"""Live C/D receipts and real browser states; never raise the shared cap."""
import base64
import json
from pathlib import Path
import time

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ["a spoon and a laptop", "a cat and a dog", "a bicycle and a car", "indoor gymnasium", "a purple clock"]
REWRITES = ["A spoon rests beside a laptop on a desk, steady camera.",
            "A cat sits beside a dog in a garden, steady camera.",
            "A bicycle stands beside a parked car, steady camera.",
            "A wide shot of an indoor gymnasium, steady camera.",
            "A purple clock hangs on a wall, steady camera."]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/preview_live.json")
    parser.add_argument("--screens", type=Path, default=ROOT / "reports/track_cd_screens")
    args = parser.parse_args()
    args.screens.mkdir(parents=True, exist_ok=True)
    receipt = {"url": args.url, "calls": [], "screenshots": [],
               "rewrite_fixtures": "Explicit scene-description fixtures; not claims of guarded risk reduction"}

    def save():
        args.report.write_text(json.dumps(receipt, indent=2) + "\n")

    def record(response, prompt, variant):
        data = response.json()
        image = data.pop("image_data_url", "")
        nbytes = len(base64.b64decode(image.split(",", 1)[1])) if image else 0
        row = {"prompt": prompt, "variant": variant, "http_status": response.status_code,
               "image_bytes": nbytes, "cache": response.headers.get("x-preview-cache"),
               "retry_after": response.headers.get("retry-after"), "error_class": response.headers.get("x-preflight-error"), "response": data}
        receipt["calls"].append(row)
        save()
        return row

    def pause(seconds):
        print(f"Waiting {seconds}s for the unchanged 5/min cap", flush=True)
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            time.sleep(min(20, end - time.monotonic()))

    pause(61)
    with httpx.Client(timeout=40) as api, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page.goto(args.url, wait_until="networkidle", timeout=60000)
        receipt["status"] = api.get(args.url + "/api/status").json()

        def shots(name, target=None):
            for width, height in [(1440, 900), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                if target:
                    page.locator(target).scroll_into_view_if_needed()
                else:
                    page.evaluate("scrollTo(0,0)")
                page.screenshot(path=str(args.screens / f"{name}_{width}x{height}.png"))
                receipt["screenshots"].append(f"{name}_{width}x{height}.png")
            page.set_viewport_size({"width": 1440, "height": 900})
            save()

        receipt["cta_bottom"] = page.locator("#check-button").evaluate("e=>e.getBoundingClientRect().bottom")
        shots("first_screen")
        page.locator("#prompt").fill(SAMPLES[0])
        with page.expect_response(lambda r: r.url.endswith("/preflight")) as pending:
            page.locator("#check-button").click()
        check = pending.value
        receipt["ui_preflight_status"] = check.status
        page.locator(".preview-button").wait_for()
        shots("after_check")
        original = page.locator(".preview-original")
        action = original if original.count() else page.locator(".preview-button")
        with page.expect_response(lambda r: r.url.endswith("/preview"), timeout=40000) as pending:
            action.click()
        browser_response = pending.value
        data = browser_response.json()
        jpeg = base64.b64decode(data["image_data_url"].split(",", 1)[1]) if browser_response.status == 200 else b""
        receipt["calls"].append({"prompt": SAMPLES[0], "variant": "original", "http_status": browser_response.status,
            "image_bytes": len(jpeg), "cache": browser_response.headers.get("x-preview-cache"),
            "response": {k: v for k, v in data.items() if k != "image_data_url"}})
        page.locator(".preview-image").wait_for(timeout=40000)
        page.locator(".preview-image").evaluate("e=>e.decode()")
        shots("preview_done", ".preview-controls")
        for prompt in SAMPLES[1:]:
            row = record(api.post(args.url + "/preview", json={"prompt": prompt, "variant": "original"}), prompt, "original")
            if row["http_status"] != 200:
                raise RuntimeError("Original fixture failed; receipt saved")
        with page.expect_response(lambda r: r.url.endswith("/preview"), timeout=40000) as pending:
            action.click()
        response = pending.value
        receipt["cap"] = {"http_status": response.status, "retry_after": response.headers.get("retry-after")}
        assert response.status == 429 and int(receipt["cap"]["retry_after"]) > 0
        page.locator('[data-state="rate-limited"]').wait_for()
        shots("rate_limited", ".preview-controls")
        pause(61)
        for prompt in REWRITES:
            row = record(api.post(args.url + "/preview", json={"prompt": prompt, "variant": "rewrite"}), prompt, "rewrite")
            if row["http_status"] != 200:
                raise RuntimeError("Rewrite fixture failed; receipt saved")
        pause(61)
        with page.expect_response(lambda r: r.url.endswith("/preview"), timeout=40000) as pending:
            action.click()
        response = pending.value
        receipt["cache"] = {"http_status": response.status, "header": response.headers.get("x-preview-cache"),
                            "model_calls": response.json().get("model_calls")}
        assert receipt["cache"] == {"http_status": 200, "header": "hit", "model_calls": 0}
        page.locator('[data-state="cached"]').wait_for()
        page.locator(".preview-image").evaluate("e=>e.decode()")
        shots("preview_cached", ".preview-controls")
        page.goto(args.url + "/architecture", wait_until="networkidle")
        shots("architecture_top")
        receipt["passed"] = (all(row["http_status"] == 200 and row["image_bytes"] > 10 * 1024
                                 for row in receipt["calls"]) and len(receipt["calls"]) == 10)
        save()
        browser.close()
        print(json.dumps({"passed": receipt["passed"], "samples": len(receipt["calls"]),
                          "screenshots": len(receipt["screenshots"]), "cta_bottom": receipt["cta_bottom"]}), flush=True)


if __name__ == "__main__":
    main()
