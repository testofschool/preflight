#!/usr/bin/env python3
"""Record one honest, silent Preflight demo take against the live service.

Requirements: Python 3.10+, playwright (and its Chromium), ffmpeg, ffprobe.
Example: python3 scripts/record_demo.py --url https://SERVICE.run.app \
    --clip reports/track_cd_synthetic_smoke.mp4 --output-dir demo_v3 \
    --preview-mode on --warm-receipt reports/preview_v3/warm.json

The only injected element is a visible recording cursor. Responses, scores,
availability, error messages and product text are never replaced or mocked.
Copy permission is write-only; this script never reads the clipboard.
Preview mode must match the promoted revision. Preview-on takes require a warm
receipt; exact rewrite texts absent from that receipt are skipped, never generated.
Each action runs once. Failed actions remain in the recording and JSON log.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


WIDTH, HEIGHT = 1920, 1080
SPOON = "a spoon and a laptop"
BUSY_COPY = "Preview is busy right now — try again in a minute. The risk check still works."
MAX_SECONDS = 150.0
# Cancellation leaves three seconds of the actual current screen, then closes.
SEQUENCE_LIMIT = 142.0
CURSOR_SCRIPT = r"""(() => {
  const install = () => {
    if (document.getElementById('__demo_recording_cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = '__demo_recording_cursor';
    cursor.setAttribute('aria-hidden', 'true');
    cursor.style.cssText = 'position:fixed;left:960px;top:70px;width:28px;height:36px;'
      + 'pointer-events:none;z-index:2147483647;filter:drop-shadow(0 1px 2px #0005);';
    cursor.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" '
      + 'viewBox="0 0 28 36"><path d="M3 2 L3 29 L10 22 L15 34 L20 32 '
      + 'L15 20 L25 20 Z" fill="#142b31" stroke="#fffefa" stroke-width="2" '
      + 'stroke-linejoin="round"/></svg>';
    document.documentElement.append(cursor);
    document.addEventListener('mousemove', e => {
      cursor.style.left = e.clientX + 'px'; cursor.style.top = e.clientY + 'px';
    }, {passive:true});
    document.addEventListener('mousedown', () => { cursor.style.opacity = '.55'; });
    document.addEventListener('mouseup', () => { cursor.style.opacity = '1'; });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install);
  else install();
})();"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def probe(path: Path) -> dict:
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate",
        "-of", "json", str(path),
    ]))


def video_valid(info: dict) -> bool:
    streams = [stream for stream in info.get("streams", []) if stream.get("codec_type") == "video"]
    return bool(streams) and all([
        streams[0].get("codec_name") == "h264",
        streams[0].get("width") == WIDTH,
        streams[0].get("height") == HEIGHT,
        streams[0].get("r_frame_rate") == "30/1",
        not any(stream.get("codec_type") == "audio" for stream in info.get("streams", [])),
        0 < float(info.get("format", {}).get("duration", 0)) <= MAX_SECONDS,
    ])


def warm_prompts(path: Path | None) -> set[tuple[str, str]]:
    if path is None:
        return set()
    receipt = json.loads(path.read_text(encoding="utf-8"))
    return {(row["prompt"], row["variant"]) for row in receipt.get("rows", receipt.get("rows10", []))
            if row.get("http_status") == 200 and isinstance(row.get("prompt"), str)
            and row.get("variant") in ("original", "rewrite") and row.get("cache_key")}


def beat_table(take: dict) -> list[dict]:
    groups = [
        (1, "Home", ("home_at_rest",)),
        (2, "Sample prompt → risk + why", ("sample_prompt_check", "risk_and_explanation", "why_and_neighbours")),
        (3, "Better prompt → risk drops → copy", ("better_prompt_and_copy",)),
        (4, "Cached sample still + caption", ("cached_sample_preview",)),
        (5, "Cached better-prompt still or skip", ("cached_rewrite_preview_or_skip",)),
        ("live", "Typed prompt live still", ("typed_live_preview",)),
        (6, "Clip upload → review → feedback-adjusted risk", ("clip_upload_and_review", "verdict_and_feedback")),
        (7, "Architecture image preview connection", ("architecture_service_connections",)),
    ]
    rows = []
    for number, label, names in groups:
        steps = [step for step in take["steps"] if step["name"] in names]
        if not steps:
            continue
        rows.append({"beat": number, "label": label,
                     "start_seconds": min(step["start_offset_seconds"] for step in steps),
                     "end_seconds": max(step["end_offset_seconds"] for step in steps),
                     "steps": [step["name"] for step in steps],
                     "status": "pass" if all(step["status"] == "pass" for step in steps) else "error"})
    if take["preview_decision"] == "off":
        step = next((step for step in take["steps"] if step["name"] == "preview_disabled_busy_copy"), None)
        if step:
            rows.insert(3, {"beat": "preview_off_copy", "label": "Preview busy copy; no image requests",
                            "start_seconds": step["start_offset_seconds"], "end_seconds": step["end_offset_seconds"],
                            "status": step["status"]})
    return rows


class Take:
    def __init__(self, page, directory: Path, number: int, started: float, args):
        self.page = page
        self.directory = directory
        self.started = started
        self.args = args
        self.preflight_result: dict = {}
        self.expected_requests = ["/preflight"]
        self.log = {
            "take": number, "started_at_utc": utc_now(), "steps": [], "network": [],
            "request_failures": [], "page_errors": [], "frames": [],
            "preview_decision": args.preview_mode,
            "warm_receipt": str(args.warm_receipt) if args.warm_receipt else None,
            "response_policy": "real UI requests only; no mocks, client retries or clipboard reads",
        }
        self.network_tasks: set[asyncio.Task] = set()
        self.request_starts: dict[int, float] = {}
        page.on("request", lambda request: self.request_starts.__setitem__(id(request), time.monotonic()))
        page.on("response", self.response)
        page.on("requestfailed", lambda request: self.log["request_failures"].append({
            "offset_seconds": self.offset(), "method": request.method,
            "path": urlsplit(request.url).path, "scheme": urlsplit(request.url).scheme,
            "failure": request.failure,
        }))
        page.on("pageerror", lambda error: self.log["page_errors"].append(str(error)))

    def offset(self) -> float:
        return round(time.monotonic() - self.started, 3)

    def response(self, response) -> None:
        task = asyncio.create_task(self.capture_response(response))
        self.network_tasks.add(task)
        task.add_done_callback(self.network_tasks.discard)

    async def capture_response(self, response) -> None:
        path = urlsplit(response.url).path
        if not path or response.url.startswith(("data:", "blob:")):
            return
        row = {"offset_seconds": self.offset(), "method": response.request.method,
               "path": path, "status": response.status,
               "preview_cache": response.headers.get("x-preview-cache") if path == "/preview" else None,
               "response_headers_after_seconds": round(time.monotonic() - self.request_starts.get(
                   id(response.request), time.monotonic()), 3)}
        self.log["network"].append(row)
        if path not in ("/api/status", "/preflight", "/postcheck", "/preview"):
            return
        try:
            data = await response.json()
            # No tokens/session identifiers, binary data or request headers are logged.
            keys = (
                "mode", "cloud_run", "firestore", "gemini", "adk", "postcheck", "preview",
                "agent_platform_session", "p_fail", "historical_p_fail", "risk_semantics",
                "rewrite_status", "rewritten_prompt", "p_fail_before", "p_fail_after",
                "supported", "coverage_supported", "pass_bool", "risk_before", "risk_after",
                "feedback_recorded", "feedback_created", "reused_stored_review", "detail",
                "model", "size", "cost_usd", "attempts", "fallback_used", "model_calls", "caption",
                "metadata_label", "generated_date", "rewrite_source", "preview_mode",
            )
            row["observed_response"] = {key: data[key] for key in keys if key in data}
        except Exception as error:
            row["response_read_error"] = str(error)[:400]

    async def pause(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def at(self, offset: float) -> None:
        await self.pause(max(0, offset - self.offset()))

    async def move(self, selector: str) -> None:
        locator = self.page.locator(selector).first
        box = await locator.bounding_box()
        if not box:
            raise RuntimeError(f"Element is not visible: {selector}")
        await self.page.mouse.move(box["x"] + box["width"] / 2,
                                   box["y"] + box["height"] / 2, steps=16)

    async def click(self, selector: str) -> None:
        await self.move(selector)
        await self.page.locator(selector).first.click(timeout=5000)

    async def scroll_to(self, selector: str, top: int = 110) -> None:
        locator = self.page.locator(selector).first
        await locator.wait_for(state="visible", timeout=5000)
        delta = await locator.evaluate("(element) => element.getBoundingClientRect().top") - top
        for _ in range(12):
            await self.page.mouse.wheel(0, delta / 12)
            await self.pause(.055)
        await self.pause(.25)

    async def frame(self, name: str) -> None:
        path = self.directory / "screens" / f"{len(self.log['frames']) + 1:02d}_{name}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        offset = self.offset()
        await self.page.screenshot(path=str(path), full_page=False)
        self.log["frames"].append({"name": name, "offset_seconds": offset, "screenshot": str(path)})

    async def step(self, name: str, action, hold: float = 0) -> bool:
        row = {"name": name, "started_at_utc": utc_now(), "start_offset_seconds": self.offset()}
        self.log["steps"].append(row)
        print(json.dumps({"take": self.log["take"], "step": name, "offset": self.offset()}), flush=True)
        try:
            detail = await action()
            row["status"] = "pass"
            if detail is not None:
                row["observed"] = detail
            await self.pause(hold)
            return True
        except asyncio.CancelledError:
            row["status"] = "interrupted_by_duration_guard"
            raise
        except Exception as error:
            row["status"] = "error"
            row["error"] = f"{type(error).__name__}: {error}"[:1200]
            # Leave the real error or current pending UI visible. Never insert a fake error.
            try:
                row["visible_ui_errors"] = await self.page.locator(
                    "#prompt-error:visible, #postcheck-error:visible, .preview-controls .form-error:visible"
                ).all_text_contents()
            except Exception:
                pass
            await self.pause(3)
            return False
        finally:
            row["end_offset_seconds"] = self.offset()
            row["wall_seconds"] = round(row["end_offset_seconds"] - row["start_offset_seconds"], 3)
            self.save()

    def save(self) -> None:
        write_json(self.directory / "record_log.json", self.log)

    async def preflight(self, prompt: str, sample: bool = False) -> dict:
        await self.scroll_to("#prompt")
        if sample:
            chip = self.page.locator(".sample").filter(has_text=prompt)
            if await chip.count() != 1 or await chip.get_attribute("data-prompt") != prompt:
                raise RuntimeError("The required sample chip is unavailable or ambiguous")
            await self.move(f'.sample[data-prompt={json.dumps(prompt)}]')
            await chip.click()
            if await self.page.locator("#prompt").input_value() != prompt:
                raise RuntimeError("Sample chip did not fill the expected prompt")
        else:
            await self.click("#prompt")
            await self.page.locator("#prompt").fill("")
            await self.page.locator("#prompt").press_sequentially(prompt, delay=40)
        async with self.page.expect_response(
            lambda response: urlsplit(response.url).path == "/preflight"
            and response.request.method == "POST", timeout=35000,
        ) as pending:
            await self.click("#check-button")
        response = await pending.value
        await self.page.locator('.results-panel[aria-busy="false"]').wait_for(state="visible", timeout=5000)
        if response.status != 200:
            raise RuntimeError(f"/preflight returned HTTP {response.status}")
        self.preflight_result = await response.json()
        error = self.page.locator("#prompt-error")
        if await error.is_visible():
            raise RuntimeError(await error.inner_text())
        risk = (await self.page.locator("#risk-value").inner_text()).strip()
        if risk == "—":
            raise RuntimeError("No supported numeric risk was returned")
        return {"prompt": prompt, "risk_percent": risk,
                "band": "high" if await self.page.locator(".risk-card.high-risk").count() else "lower"}

    async def cached_preview(self, prompt: str, variant: str, export_frame: bool) -> dict:
        if (prompt, variant) not in self.args.warmed_prompts:
            raise RuntimeError(f"No successful warm receipt for {variant} prompt")
        selector = ".preview-original" if variant == "original" and await self.page.locator(".preview-original").count() else ".preview-button"
        await self.scroll_to(selector, 180)
        await self.page.locator(selector).wait_for(state="visible", timeout=3000)
        if not await self.page.locator(selector).is_enabled():
            raise RuntimeError("Preview control is disabled on the promoted preview-on revision")
        self.expected_requests.append("/preview")
        async with self.page.expect_response(
            lambda response: urlsplit(response.url).path == "/preview"
            and response.request.method == "POST", timeout=10000,
        ) as pending:
            await self.click(selector)
        response = await pending.value
        payload = response.request.post_data_json
        data = await response.json()
        cache = response.headers.get("x-preview-cache")
        if payload.get("prompt") != prompt or payload.get("variant") != variant:
            raise RuntimeError("The UI preview request differs from the warmed prompt")
        if response.status != 200 or cache != "hit" or data.get("model_calls") != 0:
            raise RuntimeError(f"Expected cached preview; HTTP {response.status}, cache={cache}, model_calls={data.get('model_calls')}")
        image = self.page.locator(".preview-image")
        await image.wait_for(state="visible", timeout=5000)
        await image.evaluate("image => image.decode()")
        caption = self.page.locator(".preview-controls [data-state] > .subtle-copy")
        await caption.wait_for(state="visible", timeout=3000)
        text = (await caption.inner_text()).strip()
        if not text or text != data.get("caption"):
            raise RuntimeError("Preview caption is missing or does not match the real response")
        metadata = self.page.locator(".preview-metadata")
        metadata_text = (await metadata.inner_text()).strip()
        expected_metadata = f"Saved still · generated {data.get('generated_date')} · 0 model calls · $0.00"
        if metadata_text != expected_metadata:
            raise RuntimeError("Saved-still label differs from the exact required metadata")
        await self.scroll_to(".preview-image", 160)
        visibility = await image.evaluate("image => { const r=image.getBoundingClientRect(); return {top:r.top,bottom:r.bottom,width:image.naturalWidth,height:image.naturalHeight}; }")
        caption_box = await caption.bounding_box()
        metadata_box = await metadata.bounding_box()
        if not caption_box or not metadata_box or caption_box["y"] < 0 or metadata_box["y"] + metadata_box["height"] > HEIGHT or visibility["top"] < 0 or visibility["bottom"] > HEIGHT or not visibility["width"]:
            raise RuntimeError("Real preview image, caption and saved-still label do not fit in the recording viewport")
        visible_start = self.offset()
        await self.pause(3.25)
        if export_frame:
            await self.frame("cached_original_preview")
        return {"prompt": prompt, "variant": variant, "cache": cache, "model_calls": 0,
                "caption": text, "metadata_label": metadata_text, "model": data.get("model"), "size": data.get("size"),
                "image_visible_start_seconds": visible_start,
                "image_visible_end_seconds": self.offset(), "visible_hold_seconds": round(self.offset() - visible_start, 3)}

    async def sequence(self, url: str, clip: Path, model: str) -> None:
        async def home():
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is None or response.status != 200:
                raise RuntimeError("Home page did not return HTTP 200")
            await self.page.locator('.mode-pill.cloud').wait_for(state="visible", timeout=25000)
            status = await self.page.evaluate("() => window.preflightStatus")
            if status.get("preview") is not (self.args.preview_mode == "on"):
                raise RuntimeError(f"Live status did not confirm preview mode {self.args.preview_mode}")
            if await self.page.locator(".preview-button:visible, .preview-original:visible").count():
                raise RuntimeError("A preview control is visible on the resting first screen")
            await self.page.mouse.move(1540, 220, steps=12)
            await self.frame("home")
            return {key: status.get(key) for key in ("mode", "preview", "postcheck", "gemini")}
        await self.step("home_at_rest", home, 4)
        await self.step("sample_prompt_check", lambda: self.preflight(self.args.sample_prompt, sample=True))

        async def risk():
            await self.scroll_to(".risk-card")
            await self.move("#risk-symbol")
            await self.pause(1)
            await self.click(".risk-card details > summary")
            if not await self.page.locator(".risk-card details[open]").count():
                raise RuntimeError("Score details did not open")
            await self.pause(2)
            await self.frame("risk_and_score_details")
            await self.pause(3)
            await self.click(".risk-card details > summary")
        await self.at(15)
        await self.step("risk_and_explanation", risk)

        async def why():
            await self.scroll_to(".why-card")
            if not await self.page.locator("#neighbors").is_visible():
                raise RuntimeError("Historical neighbours are not visible")
            await self.frame("historical_neighbours")
            return {"neighbours": await self.page.locator("#neighbors .neighbor").all_text_contents()}
        await self.at(24)
        await self.step("why_and_neighbours", why, 3)

        async def rewrite():
            await self.scroll_to(".better-card")
            await self.page.locator(".rewritten-prompt").wait_for(state="visible", timeout=3000)
            text = await self.page.locator(".rewritten-prompt").inner_text()
            before, after = self.preflight_result.get("p_fail_before"), self.preflight_result.get("p_fail_after")
            if (self.preflight_result.get("rewrite_status") != "improved" or text != self.preflight_result.get("rewritten_prompt")
                    or not isinstance(before, (int, float)) or not isinstance(after, (int, float)) or not 0 <= after < before <= 1):
                raise RuntimeError("The real rewrite response does not prove a risk reduction")
            await self.click(".copy-button")
            await self.page.locator('.copy-button').filter(has_text="Copied").wait_for(state="visible", timeout=3000)
            await self.frame("better_prompt_copied")
            return {"rewritten_prompt": text, "risk_before": before, "risk_after": after,
                    "comparison": await self.page.locator(".rewrite-comparison").inner_text(),
                    "copy_status": await self.page.locator(".copy-button").inner_text(),
                    "clipboard_read": False}
        await self.at(29)
        await self.step("better_prompt_and_copy", rewrite, 4)

        async def preview_disabled():
            await self.scroll_to(".preview-controls", 200)
            controls = self.page.locator(".preview-button:visible, .preview-original:visible")
            count = await controls.count()
            tooltips = []
            for control in await controls.all():
                if await control.is_enabled():
                    raise RuntimeError("A preview control is enabled on the promoted preview-off revision")
                tooltips.append(await control.get_attribute("title"))
            if count:
                await self.move(".preview-button:visible, .preview-original:visible")
            message = self.page.locator(".preview-controls p.subtle-copy").filter(has_text=BUSY_COPY)
            if (BUSY_COPY not in tooltips or await message.count() != 1 or not await message.is_visible()
                    or (await message.inner_text()).strip() != BUSY_COPY):
                raise RuntimeError("The required visible preview busy paragraph and tooltip are unavailable")
            await self.pause(2)
            await self.frame("preview_busy_copy")
            return {"status": "disabled", "resting_first_screen_controls": 0,
                    "result_controls": count, "tooltips": tooltips, "visible_busy_copy": await message.inner_text(),
                    "preview_requests": 0}
        await self.at(36)
        if self.args.preview_mode == "on":
            await self.step("cached_sample_preview", lambda: self.cached_preview(self.args.sample_prompt, "original", True))

            async def optional_rewrite_preview():
                prompt = self.preflight_result.get("rewritten_prompt")
                if (prompt, "rewrite") not in self.args.warmed_prompts:
                    return {"status": "skipped", "reason": "Exact current rewrite absent from the successful warm receipt", "model_calls": 0}
                return await self.cached_preview(prompt, "rewrite", False)
            await self.at(44)
            await self.step("cached_rewrite_preview_or_skip", optional_rewrite_preview)
        else:
            await self.step("preview_disabled_busy_copy", preview_disabled, 3)

        if self.args.live_prompt:
            async def typed_live():
                self.expected_requests.append("/preflight")
                await self.preflight(self.args.live_prompt)
                # Allow the existing per-minute preview request window to advance.
                previous = [r["offset_seconds"] for r in self.log["network"] if r.get("path") == "/preview"]
                if previous:
                    await self.at(previous[-1] + 13.1)
                from scripts.probe_preview_v4 import reserve_attempt, append_result
                status = await self.page.evaluate("() => window.preflightStatus")
                prompt = self.preflight_result.get("rewritten_prompt") if self.preflight_result.get("rewrite_status") == "improved" else self.args.live_prompt
                attempt_id = "demo-typed-live-preview"
                reserve_attempt(attempt_id, status["pricing_image"]["model"], "qa",
                                hashlib.sha256(prompt.encode()).hexdigest())
                self.expected_requests.append("/preview")
                async with self.page.expect_response(lambda r: urlsplit(r.url).path == "/preview" and r.request.method == "POST", timeout=45000) as pending:
                    await self.click(".preview-button")
                response = await pending.value
                data = await response.json()
                append_result({"attempt_id": attempt_id, "http_status": response.status,
                               "model_calls": data.get("model_calls"), "image_bytes": len(base64.b64decode(data.get("image_data_url", ",").split(",",1)[1]))})
                if response.status != 200 or response.headers.get("x-preview-cache") == "hit" or data.get("model_calls") != 1:
                    raise RuntimeError("Typed demo prompt did not produce a fresh live still")
                await self.page.locator(".preview-image").evaluate("i => i.decode()")
                await self.scroll_to(".preview-image", 160)
                await self.pause(3.25)
                return {"prompt": prompt, "model": data.get("model"), "metadata_label": data.get("metadata_label"), "model_calls": 1}
            await self.step("typed_live_preview", typed_live)

        async def review():
            await self.scroll_to("#clip-review", 60)
            await self.page.locator("#clip-file").set_input_files(str(clip))
            await self.click("#clip-prompt")
            await self.page.locator("#clip-prompt").press_sequentially(self.args.sample_prompt, delay=40)
            await self.page.locator("#clip-model").fill(model)
            await self.frame("clip_uploaded")
            await self.scroll_to("#review-button", 720)
            await self.page.locator('#review-button:not([disabled])').wait_for(state="visible", timeout=6000)
            self.expected_requests.append("/postcheck")
            async with self.page.expect_response(
                lambda response: urlsplit(response.url).path == "/postcheck"
                and response.request.method == "POST", timeout=35000,
            ) as pending:
                await self.click("#review-button")
            response = await pending.value
            await self.page.locator('#postcheck-results[aria-busy="false"]').wait_for(state="visible", timeout=5000)
            if response.status != 200:
                raise RuntimeError(f"/postcheck returned HTTP {response.status}")
            if await self.page.locator("#postcheck-error").is_visible():
                raise RuntimeError(await self.page.locator("#postcheck-error").inner_text())
            return {"verdict": await self.page.locator("#verdict-value").inner_text(),
                    "model_label": model, "prompt": self.args.sample_prompt}
        await self.at(56)
        await self.step("clip_upload_and_review", review)

        async def verdict():
            await self.scroll_to("#verdict-card", 110)
            value = await self.page.locator("#verdict-value").inner_text()
            if value not in ("Pass", "Flagged", "Inconclusive"):
                raise RuntimeError(f"No completed verdict is displayed: {value}")
            before = await self.page.locator("#feedback-before").inner_text()
            after = await self.page.locator("#feedback-after").inner_text()
            if "—" in (before, after):
                raise RuntimeError("Feedback before/after risk is unavailable")
            await self.frame("clip_verdict_and_feedback")
            return {"verdict": value, "feedback_before": before, "feedback_after": after,
                    "receipt": await self.page.locator("#feedback-receipt").inner_text()}
        await self.at(78)
        await self.step("verdict_and_feedback", verdict, 6)

        async def architecture():
            response = await self.page.goto(url + "/architecture", wait_until="domcontentloaded", timeout=20000)
            if response is None or response.status != 200:
                raise RuntimeError("Architecture did not return HTTP 200")
            await self.page.locator('.mode-pill.cloud').wait_for(state="visible", timeout=15000)
            await self.scroll_to("#component-list", 280)
            connections = await self.page.locator("#component-list").inner_text()
            if "Checking connections" in connections:
                raise RuntimeError("Architecture connections did not resolve")
            preview = self.page.locator("#component-list li").filter(has_text="Image preview")
            badge = (await preview.locator(".preview-mode-message").inner_text()).strip() if self.args.preview_mode == "on" else (await preview.locator(".connection-status").inner_text()).strip()
            expected = "Image preview — Active for sample prompts (saved stills); live generation " + ("on" if self.args.live_prompt else "limited") if self.args.preview_mode == "on" else "Not active"
            if badge != expected:
                raise RuntimeError(f"Architecture image preview state {badge!r} differs from {expected!r}")
            await self.frame("architecture_connections")
            return {"service_connections": connections, "image_preview": badge}
        await self.at(90)
        await self.step("architecture_service_connections", architecture, 7)

        async def return_home():
            await self.click(".site-header .brand")
            await self.page.wait_for_url(url + "/", timeout=15000)
            await self.page.locator("#prompt").wait_for(state="visible", timeout=5000)
            await self.page.mouse.move(1540, 220, steps=12)
            return {"url_path": urlsplit(self.page.url).path}
        await self.at(104)
        await self.step("home_final_rest", return_home, 4)


async def record_take(browser, args, number: int) -> dict:
    directory = args.output_dir / "takes" / f"take_{number}"
    directory.mkdir(parents=True, exist_ok=False)
    context = await browser.new_context(
        viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1,
        record_video_dir=str(directory / "browser"),
        record_video_size={"width": WIDTH, "height": HEIGHT},
        permissions=["clipboard-write"], locale="en-US", timezone_id="Asia/Seoul",
    )
    await context.add_init_script(CURSOR_SCRIPT)
    started = time.monotonic()
    page = await context.new_page()
    page.set_default_timeout(6000)
    video = page.video
    take = Take(page, directory, number, started, args)
    try:
        await asyncio.wait_for(take.sequence(args.url, args.clip, args.model_label), timeout=SEQUENCE_LIMIT)
    except asyncio.TimeoutError:
        take.log["duration_guard"] = {"status": "sequence_incomplete", "offset_seconds": take.offset()}
        await asyncio.sleep(3)
    except Exception as error:
        take.log["fatal_error"] = f"{type(error).__name__}: {error}"
        await asyncio.sleep(3)
    finally:
        take.log["wall_seconds"] = take.offset()
        if take.network_tasks:
            pending = list(take.network_tasks)
            try:
                await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=1)
            except asyncio.TimeoutError:
                take.log["network_log_warning"] = "Response-body logging exceeded one second at recording close"
        await context.close()
        source = Path(await video.path())
        output = args.output_dir / f"preflight_demo_take_{number}.mp4"
        try:
            # Preserve the entire take: no trimming, time compression, or omitted errors.
            run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-an", "-vf", "fps=30",
                 "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                 "-movflags", "+faststart", str(output)])
            info = probe(output)
            take.log["video"] = {"path": str(output), "source": str(source), "ffprobe": info,
                                 "duration_seconds": float(info["format"]["duration"]),
                                 "bytes": output.stat().st_size, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                                 "format_and_duration_pass": video_valid(info)}
            # Decode every frame once; ffprobe metadata alone does not prove playability.
            run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"])
            take.log["video"]["full_decode_pass"] = True
        except Exception as error:
            take.log["video_error"] = f"{type(error).__name__}: {error}"
        api = [row for row in take.log["network"] if row["method"] == "POST"]
        take.log["expected_request_sequence"] = take.expected_requests
        take.log["expected_request_sequence_pass"] = [row["path"] for row in api] == take.expected_requests
        take.log["benign_local_preview_cancellations"] = [row for row in take.log["request_failures"]
            if row.get("scheme") == "blob" and "ERR_ABORTED" in (row.get("failure") or "")]
        take.log["unexpected_request_failures"] = [row for row in take.log["request_failures"]
            if row not in take.log["benign_local_preview_cancellations"]]
        take.log["clean"] = all([
            not take.log.get("fatal_error"), not take.log.get("duration_guard"),
            not take.log.get("video_error"), len(take.log["steps"]) == ((12 if args.live_prompt else 11) if args.preview_mode == "on" else 10),
            all(row["status"] == "pass" for row in take.log["steps"]),
            take.log["expected_request_sequence_pass"], all(row["status"] == 200 for row in api),
            all(row["status"] < 400 for row in take.log["network"]),
            not take.log["unexpected_request_failures"], not take.log["page_errors"],
            len(take.log["frames"]) == 8,
            take.log.get("video", {}).get("format_and_duration_pass", False),
            take.log.get("video", {}).get("full_decode_pass", False),
        ])
        take.log["beats"] = beat_table(take.log)
        take.log["ended_at_utc"] = utc_now()
        take.save()
    return take.log


async def main(args) -> int:
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            raise RuntimeError(f"Required tool is unavailable: {binary}")
    args.url = args.url.rstrip("/")
    if urlsplit(args.url).scheme != "https" and not args.allow_http:
        raise RuntimeError("Use the live HTTPS URL; --allow-http is only for explicit local development")
    args.clip = args.clip.resolve(strict=True)
    args.warm_receipt = args.warm_receipt.resolve(strict=True) if args.warm_receipt else None
    args.warmed_prompts = warm_prompts(args.warm_receipt)
    if args.preview_mode == "on" and (args.sample_prompt, "original") not in args.warmed_prompts:
        raise RuntimeError("Preview-on recording requires a successful exact sample original in --warm-receipt")
    args.output_dir = args.output_dir.resolve()
    info = probe(args.clip)
    duration = float(info.get("format", {}).get("duration", 0))
    if not 0 < duration <= 30 or args.clip.stat().st_size > 30 * 1024 * 1024:
        raise RuntimeError("Clip must be a decodable MP4, <=30 seconds and <=30 MiB")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if (args.output_dir / "takes").exists() or (args.output_dir / "preflight_demo_raw.mp4").exists():
        raise RuntimeError("Output already contains a recording; choose a new directory to preserve receipts")
    document = {
        "started_at_utc": utc_now(), "url": args.url, "takes_requested": args.takes,
        "clip": {"path": str(args.clip), "bytes": args.clip.stat().st_size,
                 "sha256": hashlib.sha256(args.clip.read_bytes()).hexdigest(), "ffprobe": info,
                 "model_label": args.model_label, "accuracy_validation_claim": False},
        "configuration": {"width": WIDTH, "height": HEIGHT, "fps": 30, "typing_delay_ms": 40,
                          "max_duration_seconds": MAX_SECONDS, "preview": args.preview_mode,
                          "sample_prompt": args.sample_prompt, "warm_receipt": str(args.warm_receipt) if args.warm_receipt else None},
        "takes": [], "selected_take": None,
    }
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not args.headed)
        try:
            for number in range(1, args.takes + 1):
                document["takes"].append(await record_take(browser, args, number))
                write_json(args.output_dir / "record_log.json", document)
        finally:
            await browser.close()
    clean = [take for take in document["takes"] if take["clean"]]
    if clean:
        chosen = min(clean, key=lambda take: take["video"]["duration_seconds"])
        output = args.output_dir / "preflight_demo_raw.mp4"
        shutil.copy2(chosen["video"]["path"], output)
        frames = args.output_dir / "frames"
        frames.mkdir(exist_ok=True)
        exported = []
        for number, frame in enumerate(chosen["frames"], 1):
            path = frames / f"{number:02d}_{frame['name']}.png"
            offset = min(frame["offset_seconds"], chosen["video"]["duration_seconds"] - .1)
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(offset), "-i", str(output),
                 "-frames:v", "1", str(path)])
            exported.append({"path": str(path), "offset_seconds": offset, "name": frame["name"]})
        sample_response = next((r.get("observed_response", {}) for r in chosen["network"] if r.get("path") == "/preflight"), {})
        document.update(sample_risk_numbers={key:sample_response.get(key) for key in ("p_fail", "p_fail_before", "p_fail_after", "historical_p_fail", "rewrite_source")},
                        selected_take=chosen["take"], output=str(output), frames=exported,
                        status="complete", output_ffprobe=probe(output), beats=chosen["beats"],
                        output_bytes=output.stat().st_size, output_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    else:
        document.update(status="no_clean_take", reason="No take passed every required interaction and video check")
    document["ended_at_utc"] = utc_now()
    write_json(args.output_dir / "record_log.json", document)
    print(json.dumps({"status": document["status"], "selected_take": document["selected_take"],
                      "durations_seconds": [take.get("video", {}).get("duration_seconds") for take in document["takes"]],
                      "clean": [take["clean"] for take in document["takes"]],
                      "log": str(args.output_dir / "record_log.json")}), flush=True)
    return 0 if clean else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="Live Preflight HTTPS base URL")
    parser.add_argument("--clip", type=Path, required=True, help="Existing permitted synthetic smoke MP4")
    parser.add_argument("--output-dir", type=Path, default=Path("demo"))
    parser.add_argument("--takes", type=int, default=1, choices=(1,), help="One untrimmed take, as required for Track H v3")
    parser.add_argument("--preview-mode", required=True, choices=("on", "off"), help="The accepted promoted revision's preview state")
    parser.add_argument("--warm-receipt", type=Path, help="V11 warm.json containing successful rows; required for preview-on")
    parser.add_argument("--sample-prompt", default=SPOON, help="Exact visible sample chip text")
    parser.add_argument("--live-prompt", help="One fresh typed prompt, only after the live arm and V-C pass")
    parser.add_argument("--model-label", default="synthetic FFmpeg loop of a Gemini still", help="Source label matching the existing synthetic review")
    parser.add_argument("--headed", action="store_true", help="Show Chromium while recording")
    parser.add_argument("--allow-http", action="store_true", help="Permit an explicitly supplied local development URL")
    try:
        sys.exit(asyncio.run(main(parser.parse_args())))
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Recording failed: {error}", file=sys.stderr)
        sys.exit(2)
