#!/usr/bin/env python3
"""Record two honest, silent Preflight demo takes against the live service.

Requirements: Python 3.10+, playwright (and its Chromium), ffmpeg, ffprobe.
Example: python3 scripts/record_demo.py --url https://SERVICE.run.app \
    --clip reports/track_cd_synthetic_smoke.mp4 --output-dir demo

The only injected element is a visible recording cursor. Responses, scores,
availability, error messages and product text are never replaced or mocked.
Copy permission is write-only; this script never reads the clipboard.
Preview is disabled and absent from the resting first screen under decision 1.
Each action runs once. Failed actions remain in the recording and JSON log.
"""

from __future__ import annotations

import argparse
import asyncio
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


WIDTH, HEIGHT = 1920, 1080
SPOON = "a spoon and a laptop"
WRESTLING = "A person is wrestling"
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
        0 < float(info.get("format", {}).get("duration", 0)) <= MAX_SECONDS,
    ])


class Take:
    def __init__(self, page, directory: Path, number: int, started: float):
        self.page = page
        self.directory = directory
        self.started = started
        self.log = {
            "take": number, "started_at_utc": utc_now(), "steps": [], "network": [],
            "request_failures": [], "page_errors": [], "frames": [],
            "preview_decision": "disabled; no preview actions on the resting first screen",
            "response_policy": "real UI requests only; no mocks, retries or clipboard reads",
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

    async def preflight(self, prompt: str) -> dict:
        await self.scroll_to("#prompt")
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
        error = self.page.locator("#prompt-error")
        if await error.is_visible():
            raise RuntimeError(await error.inner_text())
        risk = (await self.page.locator("#risk-value").inner_text()).strip()
        if risk == "—":
            raise RuntimeError("No supported numeric risk was returned")
        return {"prompt": prompt, "risk_percent": risk,
                "band": "high" if await self.page.locator(".risk-card.high-risk").count() else "lower"}

    async def sequence(self, url: str, clip: Path, model: str) -> None:
        async def home():
            response = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is None or response.status != 200:
                raise RuntimeError("Home page did not return HTTP 200")
            await self.page.locator('.mode-pill.cloud').wait_for(state="visible", timeout=25000)
            status = await self.page.evaluate("window.preflightStatus")
            if status.get("preview") is not False:
                raise RuntimeError("Live status did not confirm preview:false")
            if await self.page.locator(".preview-button:visible, .preview-original:visible").count():
                raise RuntimeError("A preview control is visible on the resting first screen")
            await self.page.mouse.move(1540, 220, steps=12)
            await self.frame("home")
            return {key: status.get(key) for key in ("mode", "preview", "postcheck", "gemini")}
        await self.step("home_at_rest", home, 4)
        await self.step("first_prompt_check", lambda: self.preflight(SPOON))

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
        await self.at(25)
        await self.step("why_and_neighbours", why, 5)

        async def rewrite():
            await self.scroll_to(".better-card")
            await self.page.locator(".rewritten-prompt").wait_for(state="visible", timeout=3000)
            text = await self.page.locator(".rewritten-prompt").inner_text()
            await self.click(".copy-button")
            await self.page.locator('.copy-button').filter(has_text="Copied").wait_for(state="visible", timeout=3000)
            await self.frame("better_prompt_copied")
            return {"rewritten_prompt": text,
                    "comparison": await self.page.locator(".rewrite-comparison").inner_text(),
                    "copy_status": await self.page.locator(".copy-button").inner_text(),
                    "clipboard_read": False}
        await self.at(32)
        await self.step("better_prompt_and_copy", rewrite, 6)

        async def preview_hidden():
            controls = self.page.locator(".preview-button:visible, .preview-original:visible")
            count = await controls.count()
            tooltips = []
            for control in await controls.all():
                if await control.is_enabled():
                    raise RuntimeError("A preview control is enabled despite decision 1")
                tooltips.append(await control.get_attribute("title"))
            if count:
                await self.move(".preview-button:visible, .preview-original:visible")
            return {"status": "disabled", "resting_first_screen_controls": 0,
                    "result_controls": count, "tooltips": tooltips, "preview_requests": 0}
        await self.at(40)
        await self.step("preview_hidden_per_owner", preview_hidden, 3)

        first = next((step.get("observed") for step in self.log["steps"]
                      if step["name"] == "first_prompt_check" and step.get("status") == "pass"), None)

        async def second():
            observed = await self.preflight(WRESTLING)
            await self.scroll_to(".risk-card")
            await self.frame("second_prompt_risk")
            if first:
                observed["different_risk_band"] = observed["band"] != first["band"]
                if not observed["different_risk_band"]:
                    self.log.setdefault("content_gaps", []).append(
                        "The fixed prompts returned the same real risk band; scores and semantics were preserved.")
            return observed
        await self.at(50)
        await self.step("second_prompt_check", second, 8)

        async def review():
            await self.scroll_to("#clip-review", 60)
            await self.page.locator("#clip-file").set_input_files(str(clip))
            await self.click("#clip-prompt")
            await self.page.locator("#clip-prompt").press_sequentially(SPOON, delay=40)
            await self.page.locator("#clip-model").fill(model)
            await self.frame("clip_uploaded")
            await self.scroll_to("#review-button", 720)
            await self.page.locator('#review-button:not([disabled])').wait_for(state="visible", timeout=6000)
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
                    "model_label": model, "prompt": SPOON}
        await self.at(65)
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
        await self.at(85)
        await self.step("verdict_and_feedback", verdict, 6)

        async def architecture():
            response = await self.page.goto(url + "/architecture", wait_until="domcontentloaded", timeout=20000)
            if response is None or response.status != 200:
                raise RuntimeError("Architecture did not return HTTP 200")
            await self.page.locator('.mode-pill.cloud').wait_for(state="visible", timeout=15000)
            await self.scroll_to("#component-list", 280)
            await self.frame("architecture_connections")
            connections = await self.page.locator("#component-list").inner_text()
            if "Checking connections" in connections:
                raise RuntimeError("Architecture connections did not resolve")
            for _ in range(20):
                await self.page.mouse.wheel(0, 21)
                await self.pause(.5)
            return {"service_connections": connections}
        await self.at(95)
        await self.step("architecture_service_connections", architecture)

        async def return_home():
            await self.click(".site-header .brand")
            await self.page.wait_for_url(url + "/", timeout=15000)
            await self.page.locator("#prompt").wait_for(state="visible", timeout=5000)
            await self.page.mouse.move(1540, 220, steps=12)
            return {"url_path": urlsplit(self.page.url).path}
        await self.at(110)
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
    take = Take(page, directory, number, started)
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
                                 "format_and_duration_pass": video_valid(info)}
            # Decode every frame once; ffprobe metadata alone does not prove playability.
            run(["ffmpeg", "-v", "error", "-i", str(output), "-f", "null", "-"])
            take.log["video"]["full_decode_pass"] = True
        except Exception as error:
            take.log["video_error"] = f"{type(error).__name__}: {error}"
        api = [row for row in take.log["network"] if row["method"] == "POST"]
        expected = ["/preflight", "/preflight", "/postcheck"]
        take.log["expected_request_sequence_pass"] = [row["path"] for row in api] == expected
        take.log["benign_local_preview_cancellations"] = [row for row in take.log["request_failures"]
            if row.get("scheme") == "blob" and "ERR_ABORTED" in (row.get("failure") or "")]
        take.log["unexpected_request_failures"] = [row for row in take.log["request_failures"]
            if row not in take.log["benign_local_preview_cancellations"]]
        take.log["clean"] = all([
            not take.log.get("fatal_error"), not take.log.get("duration_guard"),
            not take.log.get("video_error"), len(take.log["steps"]) == 11,
            all(row["status"] == "pass" for row in take.log["steps"]),
            take.log["expected_request_sequence_pass"], all(row["status"] == 200 for row in api),
            all(row["status"] < 400 for row in take.log["network"]),
            not take.log["unexpected_request_failures"], not take.log["page_errors"],
            len(take.log["frames"]) == 8,
            take.log.get("video", {}).get("format_and_duration_pass", False),
            take.log.get("video", {}).get("full_decode_pass", False),
        ])
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
                          "max_duration_seconds": MAX_SECONDS, "preview": "disabled; absent from resting first screen"},
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
        document.update(selected_take=chosen["take"], output=str(output), frames=exported,
                        status="complete", output_ffprobe=probe(output))
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
    parser.add_argument("--takes", type=int, default=2, choices=range(1, 6))
    parser.add_argument("--model-label", default="synthetic FFmpeg loop of a Gemini still", help="Source label matching the existing synthetic review")
    parser.add_argument("--headed", action="store_true", help="Show Chromium while recording")
    parser.add_argument("--allow-http", action="store_true", help="Permit an explicitly supplied local development URL")
    try:
        sys.exit(asyncio.run(main(parser.parse_args())))
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Recording failed: {error}", file=sys.stderr)
        sys.exit(2)
