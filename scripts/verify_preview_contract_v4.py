#!/usr/bin/env python3
"""Mocked Chromium UI contracts only: no model calls and no release-gate claim."""
from __future__ import annotations

import argparse
import base64
import io
import json
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image
from playwright.sync_api import expect, sync_playwright

from verify_preview_ui_v3 import JS_COUNT

ROOT = Path(__file__).resolve().parents[1]
LIMITED = "Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works."
SAVED = "Saved still · generated 2026-10-18 · 0 model calls · $0.00"
LIVE = "Model gemini-2.5-flash-image · 1K · $0.039 · 2.4 s"


def mode_message(mode):
    return "Image preview — Active for sample prompts (saved stills); live generation " + ("on" if mode == "samples+live" else "limited")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="reports/preview_v4/ui_contract.json")
    args = parser.parse_args()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    fixture = io.BytesIO()
    Image.new("RGB", (160, 90), "green").save(fixture, "JPEG")
    image_url = "data:image/jpeg;base64," + base64.b64encode(fixture.getvalue()).decode()
    state = {"mode": "samples", "reply": "cache", "pinned": True, "no_safe": False, "requests": []}
    receipt = {"scope": "Mocked browser UI contracts only; 0 provider calls; real-candidate gates remain separate", "checks": [], "passed": False}

    def check(name, passed):
        receipt["checks"].append({"name": name, "passed": bool(passed)})
        assert passed, name

    def respond(route, body, status=200, headers=None):
        route.fulfill(status=status, content_type="application/json", headers=headers or {}, body=json.dumps(body))

    def handle(route):
        path = urlsplit(route.request.url).path
        if path == "/api/status":
            respond(route, {"mode": "cloud", "cloud_run": True, "gemini": True, "adk": True, "firestore": True,
                            "agent_platform_session": True, "postcheck": False, "preview": True,
                            "preview_mode": state["mode"], "preview_mode_message": mode_message(state["mode"])})
        elif path == "/preflight":
            prompt = route.request.post_data_json["prompt"]
            respond(route, {"p_fail": 0.5, "p_fail_before": 0.5, "p_fail_after": 0.5 if state["no_safe"] else 0.2,
                            "est_cost_usd": 6.4, "rewrite_status": "no_safe_rewrite" if state["no_safe"] else "improved",
                            "rewritten_prompt": prompt if state["no_safe"] else "A cat rests beside a dog in a quiet room.",
                            "rewrite_source": "pinned-sample" if state["pinned"] else "live", "supported": True,
                            "reasons": ["Historical evidence provides this estimate."], "nearest_prompts": []})
        elif path == "/preview":
            state["requests"].append(route.request.post_data_json)
            if state["reply"] in ("limited", "error"):
                respond(route, {"detail": LIMITED if state["reply"] == "limited" else "private provider stack trace"}, 503)
            else:
                cached = state["reply"] == "cache"
                respond(route, {"image_data_url": image_url, "caption": "Fixture only; no generation.",
                                "cache": "hit" if cached else "miss", "model_calls": 0 if cached else 1,
                                "generated_date": "2026-10-18", "model": "gemini-2.5-flash-image", "size": "1K",
                                "cost_usd": 0 if cached else 0.039, "latency_ms": 2400,
                                "metadata_label": SAVED if cached else LIVE}, headers={"X-Preview-Cache": "hit" if cached else "miss"})
        else:
            target = ROOT / "static" / ("index.html" if path == "/" else "architecture.html") if path in ("/", "/architecture") else ROOT / path.lstrip("/")
            if target.is_file() and (path.startswith("/static/") or path in ("/", "/architecture")):
                route.fulfill(path=str(target))
            else:
                route.fulfill(status=404, body="")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            context.route("**/*", handle)
            page = context.new_page()

            def home():
                page.goto("http://preflight.test/", wait_until="networkidle")

            def submit(prompt):
                page.locator("#prompt").fill(prompt)
                page.locator("#check-button").click()
                expect(page.locator("#check-button")).to_be_enabled()
                page.locator(".preview-button").wait_for()

            def preview(original=False):
                page.locator(".preview-original" if original else ".preview-button").click()
                expect(page.locator(".preview-button")).to_be_enabled()

            def architecture(expected):
                page.goto("http://preflight.test/architecture", wait_until="networkidle")
                check("architecture message " + expected, page.locator(".preview-mode-message").inner_text() == mode_message(expected))

            home()
            measured = page.evaluate(JS_COUNT)
            receipt["first_viewport"] = measured
            receipt["objects"] = len(measured["elements"])
            receipt["colors"] = len(measured["colors"])
            receipt["cta_bottom_px"] = page.locator("#check-button").evaluate("e => e.getBoundingClientRect().bottom")
            check("first viewport objects <=18", receipt["objects"] <= 18)
            check("first viewport colors <=12", receipt["colors"] <= 12)
            check("CTA inside 900px", receipt["cta_bottom_px"] <= 900)
            page.locator(".sample").first.click()
            submit(page.locator("#prompt").input_value())
            check("saved rewrite label exact and visible", page.locator(".sample-rewrite-label").inner_text() == "Sample rewrite (saved)" and page.locator(".sample-rewrite-label").is_visible())
            check("samples-only message exact", page.locator(".preview-mode-message").inner_text() == mode_message("samples"))
            check("samples-only preview enabled", page.locator(".preview-button").is_enabled())
            preview()
            check("cache metadata exact", page.locator(".preview-metadata").inner_text() == SAVED)
            check("cache still visible", page.locator(".preview-image").evaluate("i => i.complete && i.naturalWidth > 0"))
            check("main preview uses rewrite variant", state["requests"][-1]["variant"] == "rewrite")
            preview(original=True)
            check("original variant keeps sample text", state["requests"][-1]["variant"] == "original" and state["requests"][-1]["prompt"] == "a cat and a dog")
            state["no_safe"] = True
            submit("indoor gymnasium")
            check("no-safe sample decision label exact", page.locator(".sample-rewrite-label").inner_text() == "Sample rewrite (saved)")
            check("no-safe unchanged explanation visible", page.locator(".saved-sample-unchanged").is_visible())
            check("no-safe has no accepted rewrite/copy", page.locator(".rewritten-prompt, .copy-button").count() == 0)
            check("no-safe main button discloses unchanged", page.locator(".preview-button").inner_text() == "Preview saved sample (unchanged)")
            preview()
            check("no-safe saved variant uses original honestly", state["requests"][-1]["variant"] == "rewrite" and state["requests"][-1]["prompt"] == "indoor gymnasium")
            preview(original=True)
            check("no-safe original action remains separate", state["requests"][-1]["variant"] == "original" and state["requests"][-1]["prompt"] == "indoor gymnasium")
            state.update(pinned=False, no_safe=False, reply="limited")
            submit("A new typed prompt with a cat and a bicycle")
            check("typed rewrite has no saved label", page.locator(".sample-rewrite-label").count() == 0)
            preview()
            check("typed miss exact limited copy", page.locator(".preview-controls .form-error").inner_text() == LIMITED)
            check("no busy retry copy", "busy right now" not in page.inner_text("body") and "try again in a minute" not in page.inner_text("body"))
            architecture("samples")
            state.update(mode="samples+live", reply="live")
            home()
            submit("A new typed prompt with a bicycle in a park")
            check("live-on message exact", page.locator(".preview-mode-message").inner_text() == mode_message("samples+live"))
            preview()
            check("live metadata preserves selected actual price", page.locator(".preview-metadata").inner_text() == LIVE)
            state["reply"] = "error"
            preview()
            check("live error exact limited copy", page.locator(".preview-controls .form-error").inner_text() == LIMITED)
            check("provider details redacted", "private provider" not in page.inner_text("body"))
            architecture("samples+live")
            page.set_viewport_size({"width": 390, "height": 844})
            check("mobile architecture no horizontal overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            state.update(mode="samples", reply="cache", pinned=True)
            home()
            submit("a cat and a dog")
            preview()
            check("mobile cache metadata exact", page.locator(".preview-metadata").inner_text() == SAVED)
            check("mobile result no horizontal overflow", page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            context.close()
            browser.close()
        receipt["passed"] = True
    except Exception as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        receipt["check_count"] = len(receipt["checks"])
        output.write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps({"output": str(output), "passed": receipt["passed"], "checks": receipt["check_count"]}))


if __name__ == "__main__":
    main()
