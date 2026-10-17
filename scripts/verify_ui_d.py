"""Final disabled-preview UI, real preflight, geometry and screenshots."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    root = Path("reports/track_cd_screens")
    root.mkdir(parents=True, exist_ok=True)
    result = {"url": args.url, "screenshots": [], "overflow_checks": [], "console_errors": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page.on("pageerror", lambda error: result["console_errors"].append(type(error).__name__))
        page.goto(args.url, wait_until="networkidle", timeout=60000)
        result["cta_bottom"] = page.locator("#check-button").evaluate("e=>e.getBoundingClientRect().bottom")
        result["textarea_rows"] = page.locator("#prompt").get_attribute("rows")
        result["mode_in_footer"] = page.locator("#mode-label").evaluate("e=>Boolean(e.closest('footer'))")
        result["session_row_hidden"] = page.locator("#session-row").count() == 1 and not page.locator("#session-row").is_visible()
        result["session_row_in_footer"] = page.locator("#session-row").evaluate("e=>Boolean(e.closest('footer'))")
        result["score_collapsed"] = page.locator(".risk-card details").evaluate("e=>!e.open")

        def shots(state):
            for width, height in [(1440, 900), (390, 844)]:
                page.set_viewport_size({"width": width, "height": height})
                page.evaluate("scrollTo(0,0)")
                name = f"{args.prefix}_{state}_{width}x{height}.png"
                page.screenshot(path=str(root / name))
                result["screenshots"].append(name)
                result["overflow_checks"].append(page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            page.set_viewport_size({"width": 1440, "height": 900})

        shots("first_screen")
        page.locator("#prompt").fill("a spoon and a laptop")
        with page.expect_response(lambda r: r.url.endswith("/preflight"), timeout=60000) as pending:
            page.locator("#check-button").click()
        result["preflight_status"] = pending.value.status
        page.locator(".preview-button").wait_for()
        result["preview_disabled"] = page.locator(".preview-button").is_disabled()
        result["preview_tooltip"] = page.locator(".preview-button").get_attribute("title")
        shots("after_check")
        page.goto(args.url + "/architecture", wait_until="networkidle")
        result["architecture_image_row"] = page.get_by_text("Image preview (Gemini image model)", exact=True).count() == 1
        shots("architecture_top")
        result["passed"] = (result["cta_bottom"] <= 900 and result["textarea_rows"] == "6"
                            and result["mode_in_footer"] and result["session_row_hidden"] and result["session_row_in_footer"]
                            and result["score_collapsed"] and result["preflight_status"] == 200
                            and result["preview_disabled"] and result["preview_tooltip"] == "Preview unavailable in this region"
                            and result["architecture_image_row"] and all(result["overflow_checks"])
                            and not result["console_errors"])
        Path(f"reports/{args.prefix}_ui.json").write_text(json.dumps(result, indent=2) + "\n")
        browser.close()
        print(json.dumps({key: result[key] for key in ["passed", "cta_bottom", "preview_disabled", "preflight_status"]}))
        return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
