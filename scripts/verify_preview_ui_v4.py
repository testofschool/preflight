#!/usr/bin/env python3
"""Real Chromium sample-cache gates and a separate production judge pass."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_preview_ui_v3 import JS_COUNT

LIMITED = "Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works."
SAMPLES = ["a cat and a dog", "a spoon and a laptop", "a bicycle and a car", "indoor gymnasium", "a purple clock"]
TYPED = ["A spoon and a laptop beside a green ceramic mug on an October judging desk.",
         "A bicycle and a car parked beside an orange garden bench on a quiet street."]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--phase", choices=("candidate", "self-qa"), required=True)
    parser.add_argument("--live-qa", action="store_true")
    parser.add_argument("--typed-from-receipt", type=Path, help="Use two successful V-C original prompts for zero-call server-cache self-QA")
    args = parser.parse_args()
    args.url = args.url.rstrip("/")
    args.report_dir.mkdir(parents=True, exist_ok=False)
    receipt = {"phase": args.phase, "url": args.url, "started_at_utc": datetime.now(timezone.utc).isoformat(),
               "fresh_browser": True, "http_cache_disabled": True, "service_workers": "blocked",
               "steps": [], "preview_rows": [], "page_errors": [], "network": [], "passed": False}
    path = args.report_dir / "summary.json"
    last_preview = 0.0
    current_prompt = None
    current_result = {}

    def save():
        path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="en-US",
                                      timezone_id="Asia/Seoul", service_workers="block")
        page = context.new_page()
        context.new_cdp_session(page).send("Network.setCacheDisabled", {"cacheDisabled": True})
        page.set_default_timeout(10000)
        page.on("pageerror", lambda error: receipt["page_errors"].append(str(error)))
        page.on("response", lambda response: receipt["network"].append({"path": urlsplit(response.url).path,
                     "method": response.request.method, "http_status": response.status}))

        def shot(name, action, observed, expected, passed=True, target=None):
            if target:
                page.locator(target).scroll_into_view_if_needed()
            page.wait_for_timeout(180)
            filename = f"{len(receipt['steps']) + 1:02d}_{name}.png"
            page.screenshot(path=str(args.report_dir / filename))
            row = {"step": name, "action": action, "observed": observed, "expected": expected,
                   "passed": bool(passed), "screenshot": filename}
            receipt["steps"].append(row)
            save()

        def load_home():
            response = page.goto(args.url, wait_until="domcontentloaded", timeout=40000)
            assert response and response.status == 200
            page.wait_for_function("() => window.preflightStatus !== undefined", timeout=30000)
            page.evaluate("() => document.fonts.ready")
            page.wait_for_timeout(2500)

        def check(prompt, name, sample=False):
            nonlocal current_prompt, current_result
            page.evaluate("() => scrollTo(0,0)")
            if sample:
                page.locator(".sample").filter(has_text=prompt).click()
                shot(name + "_sample", "Click sample " + prompt, page.locator("#prompt").input_value(), prompt,
                     page.locator("#prompt").input_value() == prompt)
            else:
                page.locator("#prompt").fill(prompt)
            started = time.monotonic()
            with page.expect_response(lambda r: urlsplit(r.url).path == "/preflight" and r.request.method == "POST", timeout=45000) as pending:
                page.locator("#check-button").click()
            response = pending.value
            data = response.json()
            current_prompt, current_result = prompt, data
            page.locator('.results-panel[aria-busy="false"]').wait_for(state="visible", timeout=45000)
            valid = response.status == 200 and (not sample or data.get("rewrite_source") == "pinned-sample")
            label = page.locator(".sample-rewrite-label")
            if sample:
                valid = valid and label.count() == 1 and label.is_visible() and label.inner_text() == "Sample rewrite (saved)"
            mode_text = "Image preview — Active for sample prompts (saved stills); live generation " + ("on" if receipt["status"].get("preview_mode") == "samples+live" else "limited")
            actual_mode = page.locator(".preview-controls .preview-mode-message").inner_text()
            valid = valid and actual_mode == mode_text
            shot(name + "_check", "Click Check", {"http_status": response.status, "rewrite_source": data.get("rewrite_source"),
                 "p_fail_before": data.get("p_fail_before"), "p_fail_after": data.get("p_fail_after"),
                 "rewrite_status": data.get("rewrite_status"), "preview_mode_message": actual_mode, "latency_seconds": round(time.monotonic()-started, 4)},
                 "200; saved sample rewrite" if sample else "200; live rewrite", valid, ".better-card")
            assert valid, "Check failed or sample rewrite label missing"
            return data

        def preview(name, variant, sample=True, ordinal=0):
            nonlocal last_preview
            # Preserve the deployed five-per-minute request limiter, including hits.
            wait = 13.1 - (time.monotonic() - last_preview)
            if wait > 0:
                page.wait_for_timeout(int(wait * 1000) + 1)
            dispatch_id = None
            if not sample and receipt["status"].get("preview_mode") == "samples+live":
                from scripts.probe_preview_v4 import reserve_attempt
                dispatch_id = f"{args.phase}-{name}"
                reserve_attempt(dispatch_id, receipt["status"]["pricing_image"]["model"], "qa",
                    hashlib.sha256(page.locator("#prompt").input_value().encode()).hexdigest())
            selector = ".preview-original" if variant == "original" and page.locator(".preview-original").count() else ".preview-button"
            page.locator(selector).scroll_into_view_if_needed()
            started = time.monotonic()
            with page.expect_response(lambda r: urlsplit(r.url).path == "/preview" and r.request.method == "POST", timeout=45000) as pending:
                page.locator(selector).click()
            last_preview = started
            response = pending.value
            data = response.json()
            elapsed = time.monotonic() - started
            row = {"step": name, "variant": variant, "submitted": response.request.post_data_json,
                   "http_status": response.status, "latency_seconds": round(elapsed, 4),
                   "cache": response.headers.get("x-preview-cache"), "model_calls": data.get("model_calls"),
                   "model": data.get("model"), "size": data.get("size"), "generated_date": data.get("generated_date"),
                   "cost_usd": data.get("cost_usd"), "image_bytes": 0, "image_visible": False}
            if data.get("image_data_url"):
                image = page.locator(".preview-image")
                image.wait_for(state="visible")
                image.evaluate("i => i.decode()")
                row["image_visible"] = image.evaluate("i => i.complete && i.naturalWidth > 0")
                row["image_bytes"] = len(base64.b64decode(data["image_data_url"].split(",", 1)[1]))
                row["label"] = page.locator(".preview-metadata").inner_text()
            else:
                page.locator(".preview-controls .form-error").wait_for(state="visible")
                row["label"] = page.locator(".preview-controls .form-error").inner_text()
            row["expected_label"] = f"Saved still · generated {data.get('generated_date')} · 0 model calls · $0.00" if sample else None
            valid = elapsed < 45 and response.status != 504
            if sample:
                expected_prompt = current_prompt if variant == "original" else current_result["rewritten_prompt"]
                valid = valid and row["submitted"].get("variant") == variant and row["submitted"].get("prompt") == expected_prompt and response.status == 200 and row["cache"] == "hit" and row["model_calls"] == 0 and row["image_visible"] and row["label"] == row["expected_label"] and row["image_bytes"] > 10240
            elif receipt["status"].get("preview_mode") == "samples":
                valid = valid and row["label"] == LIMITED and not row["image_visible"]
            else:
                valid = valid and ((response.status == 200 and row["image_visible"]) or row["label"] == LIMITED)
            row["passed"] = bool(valid)
            receipt["preview_rows"].append(row)
            shot(name, "Click Preview " + variant, {k:v for k,v in row.items() if k != "submitted"},
                 "Saved image, hit, 0 calls and exact label" if sample else "Live image or exact limited message", valid, ".preview-controls")
            if dispatch_id:
                from scripts.probe_preview_v4 import append_result
                append_result({"attempt_id": dispatch_id, "http_status": response.status, "cache": row["cache"],
                    "model_calls": data.get("model_calls"), "image_bytes": row["image_bytes"], "latency_seconds": elapsed})
            return valid

        try:
            load_home()
            receipt["status"] = page.evaluate("() => window.preflightStatus")
            assert receipt["status"].get("preview") is True
            measurement = page.evaluate(JS_COUNT)
            receipt["viewport"] = {"objects": len(measurement["elements"]), "colors": len(measurement["colors"]),
                 "cta_bottom_px": page.locator("#check-button").evaluate("e=>e.getBoundingClientRect().bottom"),
                 "elements": measurement["elements"]}
            v = receipt["viewport"]
            shot("first_viewport", "Open fresh browser", v, "objects <=18; colors <=12; CTA <=900px",
                 v["objects"] <= 18 and v["colors"] <= 12 and v["cta_bottom_px"] <= 900)
            for i,prompt in enumerate(SAMPLES, 1):
                check(prompt, f"sample_{i}", sample=True)
                preview(f"sample_{i}_original", "original")
                preview(f"sample_{i}_rewrite", "rewrite")
            if args.phase == "self-qa" or args.live_qa:
                typed = TYPED if args.phase == "self-qa" else [f"A spoon and a laptop beside a numbered coral card {i}, in a fresh v4 UI judging still." for i in range(1,11)]
                if args.phase == "self-qa" and args.typed_from_receipt:
                    prior = json.loads(args.typed_from_receipt.read_text())
                    typed = [r["submitted"]["prompt"] for r in prior["preview_rows"] if r["step"].startswith("typed_") and r["http_status"] == 200 and r["cache"] != "hit" and r["model_calls"] == 1][:2]
                    assert len(typed) == 2, "Two successful V-C typed prompts required for cache-reuse self-QA"
                    receipt["self_qa_typed_cache_source"] = str(args.typed_from_receipt)
                for i,prompt in enumerate(typed,1):
                    check(prompt, f"typed_{i}")
                    preview(f"typed_{i}_preview", "original", sample=False, ordinal=i)
            response = page.goto(args.url + "/architecture", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_function("() => window.preflightStatus !== undefined", timeout=30000)
            page.wait_for_timeout(1200)
            actual = page.locator("#component-list").inner_text()
            expected = "Image preview — Active for sample prompts (saved stills); live generation " + ("on" if receipt["status"].get("preview_mode") == "samples+live" else "limited")
            shot("architecture", "Open architecture page", actual, expected, expected in actual, "#component-list")
            receipt["expected_surface_message"] = expected
            if args.phase == "self-qa":
                page.goto("https://github.com/testofschool/preflight", wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(2000)
                readme = page.locator("article").first
                text = readme.inner_text()
                readme.evaluate("e => e.scrollIntoView({block:'start'})")
                shot("readme_top", "Read public README top section", text[:3500], expected, expected in text)
                clause = readme.get_by_text(expected, exact=True)
                clause.scroll_into_view_if_needed()
                shot("readme_preview_clause", "Read README preview clause", clause.inner_text(), expected,
                     clause.inner_text() == expected)
            sample_rows = [r for r in receipt["preview_rows"] if r["step"].startswith("sample_")]
            typed_rows = [r for r in receipt["preview_rows"] if r["step"].startswith("typed_")]
            receipt["V_B"] = len(sample_rows) == 10 and all(r["passed"] for r in sample_rows)
            receipt["V_C"] = (len(typed_rows) == 10 and sum(r["image_visible"] and r["http_status"] == 200 and r["cache"] != "hit" and r["model_calls"] == 1 and r["image_bytes"] > 10240 for r in typed_rows) >= 9) if args.live_qa else None
            receipt["V_D"] = all(r["latency_seconds"] < 45 and r["http_status"] != 504 for r in receipt["preview_rows"])
            receipt["passed"] = all(s["passed"] for s in receipt["steps"]) and receipt["V_B"] and receipt["V_D"] and not receipt["page_errors"] and (not args.live_qa or receipt["V_C"])
        except Exception as error:
            receipt["error"] = {"type": type(error).__name__, "message": str(error)[:500]}
            save()
        finally:
            context.close()
            browser.close()
            receipt["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
            save()
    print(json.dumps({k:receipt.get(k) for k in ("phase", "passed", "V_B", "V_C", "V_D", "viewport", "error")}))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
