"""Historical prompt checks and bounded, upload-only cloud video inspection."""

from collections import deque
from contextlib import asynccontextmanager
import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from threading import Lock
from time import monotonic
from uuid import uuid4
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.formparsers import MultiPartException

from preflight_core import PreflightEngine
from cloud.preview import CAPTION, image_pricing


ROOT = Path(__file__).resolve().parent
PRICING = {
    "model": "Veo 3.1 Standard · 720p/1080p + audio",
    "usd_per_second": 0.40,
    "duration_seconds": 8,
    "single_attempt_usd": 3.20,
    "source": "https://ai.google.dev/gemini-api/docs/pricing#veo-3.1",
    "checked_date": "2026-10-16",
    "assumption": "Illustrative budget only; historical both-bad rate is not calibrated to Veo.",
}
SAMPLES = [
    "a cat and a dog",
    "a spoon and a laptop",
    "a bicycle and a car",
    "indoor gymnasium",
    "a purple clock",
]
PRICING_IMAGE = image_pricing()


class PromptInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("prompt")
    @classmethod
    def clean_prompt(cls, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Enter a video prompt.")
        return cleaned


class PreviewInput(PromptInput):
    variant: Literal["original", "rewrite"]


class RequestBudget:
    """One process, one global 20-request rolling minute; no client identifiers."""

    def __init__(self, count: int = 20):
        self.count = count
        self.recent: deque[float] = deque()
        self.lock = Lock()

    def admit(self) -> None:
        with self.lock:
            now = monotonic()
            while self.recent and self.recent[0] <= now - 60:
                self.recent.popleft()
            if len(self.recent) >= self.count:
                raise HTTPException(
                    status_code=429,
                    detail="This local demo allows 20 checks per minute. Try again shortly.",
                    headers={"Retry-After": "60"},
                )
            self.recent.append(now)


def create_app(artifact_dir: Path | None = None, *, mode: str | None = None,
               store_factory=None, rewrite_factory=None, postcheck_factory=None, preview_factory=None) -> FastAPI:
    selected_mode = mode or os.environ.get("PREFLIGHT_MODE", "local-g0")
    if selected_mode not in ("local-g0", "cloud"):
        raise ValueError("Unsupported runtime mode")
    connected = selected_mode == "cloud"

    @asynccontextmanager
    async def lifespan(service: FastAPI):
        service.state.engine = PreflightEngine.load(artifact_dir or ROOT / "artifacts")
        service.state.budget = RequestBudget()
        service.state.connected = connected
        service.state.postchecker = None
        service.state.previewer = None
        service.state.postcheck_slot = asyncio.Semaphore(1)
        if connected:
            from cloud.store import FirestoreDifficultyStore
            from cloud.rewrite_agent import RewriteService
            try:
                service.state.store = (store_factory or FirestoreDifficultyStore.from_env)().attach(service.state.engine)
                service.state.rewriter = (rewrite_factory or RewriteService)(
                    service.state.engine, predictor=service.state.store.difficulty)
                await service.state.rewriter.healthcheck()
            except Exception as error:
                # Configuration/transport exceptions can contain resource identifiers.
                raise RuntimeError(f"Cloud startup verification failed ({type(error).__name__})") from None
            # A video dependency failure must not prevent Track A from starting.
            try:
                from cloud.postcheck import PostcheckService
                if postcheck_factory is None and not all(shutil.which(name) for name in ("ffmpeg", "ffprobe")):
                    raise RuntimeError("Video decoding tools are unavailable")
                service.state.postchecker = (postcheck_factory or PostcheckService.from_env)()
            except Exception:
                service.state.postchecker = None
            if preview_factory is not None or os.environ.get("PREFLIGHT_PREVIEW_ENABLED") == "true":
                try:
                    from cloud.preview import ImagePreviewService
                    service.state.previewer = (preview_factory or ImagePreviewService)()
                except Exception:
                    service.state.previewer = None
        yield

    service = FastAPI(title="Preflight", lifespan=lifespan)

    @service.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; media-src 'self' blob:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @service.get("/healthz")
    def health():
        return {"status": "ready", "mode": selected_mode}

    @service.get("/api/status")
    def status():
        return {
            "mode": selected_mode,
            "label": "Connected research preview" if connected else "Local statistical preview",
            "cloud_run": connected and bool(os.environ.get("K_SERVICE")),
            "gemini": connected,
            "adk": connected,
            "agent_platform_session": connected and service.state.rewriter.session_active,
            "firestore": connected,
            "postcheck": connected and service.state.postchecker is not None,
            "preview": connected and service.state.previewer is not None,
            "pricing_image": image_pricing(),
            "generations": 0,
            "sample_prompts": SAMPLES,
            "pricing": PRICING,
            "rate_limit": {"checks": 20, "seconds": 60,
                           "scope": "shared Firestore transaction" if connected else "single local process"},
        }

    @service.post("/preflight")
    async def preflight(body: PromptInput, request: Request, response: Response):
        if connected:
            from cloud.store import StoreRateLimited, StoreBudgetExhausted
            try:
                await asyncio.to_thread(service.state.store.admit_request)
                prediction = await asyncio.to_thread(service.state.store.difficulty, body.prompt)
                if prediction.get("supported"):
                    user_id = request.cookies.get("pf_user", "")
                    if not re.fullmatch(r"anon-[0-9a-f]{32}", user_id):
                        user_id = "anon-" + uuid4().hex
                    rewrite = await service.state.rewriter.preflight(body.prompt, user_id=user_id,
                                                                      session_id=body.session_id)
                    prediction.update(rewrite)
                    # Use the agent's original score snapshot consistently with its rewrite guard.
                    prediction["p_fail"] = rewrite["p_fail_before"]
                    response.set_cookie("pf_user", user_id, httponly=True, secure=bool(os.environ.get("K_SERVICE")),
                                        samesite="lax", max_age=86400)
                else:
                    prediction["rewrite_status"] = "unavailable"
            except StoreRateLimited as error:
                raise HTTPException(429, detail="This preview allows 20 checks per minute. Try again shortly.",
                                    headers={"Retry-After": str(error.retry_after)}) from None
            except StoreBudgetExhausted:
                raise HTTPException(429, detail="This preview's cumulative request budget is exhausted.") from None
            except Exception as error:
                raise HTTPException(503, detail="The connected evidence or rewrite service is unavailable.",
                                    headers={"X-Preflight-Error": type(error).__name__}) from None
        else:
            service.state.budget.admit()
            prediction = service.state.engine.predict(body.prompt)
        risk = prediction.get("p_fail")
        attempts = min(1 / max(1 - risk, 1e-12), 5) if risk is not None else None
        prediction.update(
            mode=selected_mode,
            pricing=PRICING,
            est_cost_usd=round(PRICING["single_attempt_usd"] * attempts, 2)
            if attempts is not None else None,
            expected_attempts_capped=attempts,
        )
        prediction.setdefault("risk_semantics", "Mean both-bad human vote rate of five similar historical prompts.")
        if not connected:
            prediction["rewrite_status"] = "unavailable-g0"
            prediction.pop("rewritten_prompt", None)
        return prediction

    @service.post("/preview")
    async def preview(body: PreviewInput, response: Response):
        if not connected:
            raise HTTPException(503, detail="Preview needs the connected service.")
        if service.state.previewer is None:
            raise HTTPException(503, detail="Preview is unavailable right now. The risk check still works.")
        from cloud.store import StoreRateLimited, StoreBudgetExhausted, prompt_id
        started = monotonic()
        try:
            await asyncio.to_thread(service.state.store.admit_preview)
            provider = service.state.previewer
            pricing = image_pricing()
            key = hashlib.sha256(json.dumps(["preview-v1", body.prompt, provider.model, provider.size],
                                           ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            cached = await asyncio.to_thread(service.state.store.get_preview, key)
            if cached:
                jpeg = cached["bytes"]
                calls, cache = 0, "hit"
            else:
                async with asyncio.timeout(30):
                    jpeg = await provider.generate(body.prompt)
                calls, cache = 1, "miss"
                if len(jpeg) <= 900 * 1024:
                    await asyncio.to_thread(service.state.store.save_preview, key,
                        {"bytes": jpeg, "model": provider.model, "size": provider.size,
                         "created_at": datetime.now(timezone.utc), "prompt_id": prompt_id(body.prompt)})
                else:
                    cache = "skip-size"
            response.headers["X-Preview-Cache"] = cache
            return {"image_data_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode(),
                    "model": provider.model, "size": provider.size, "aspect_ratio": "16:9",
                    "cost_usd": pricing["usd_per_image"], "pricing_source": pricing["source"],
                    "pricing_checked_date": pricing["checked_date"],
                    "latency_ms": round((monotonic() - started) * 1000), "model_calls": calls,
                    "synthid": True, "caption": CAPTION}
        except StoreRateLimited as error:
            raise HTTPException(429, detail=f"Try again in {error.retry_after} s",
                                headers={"Retry-After": str(error.retry_after)}) from None
        except StoreBudgetExhausted:
            now = datetime.now(timezone.utc)
            retry = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
            raise HTTPException(429, detail="The daily preview allowance has been reached.",
                                headers={"Retry-After": str(retry)}) from None
        except Exception as error:
            raise HTTPException(503, detail="Preview is unavailable right now. The risk check still works.",
                                headers={"X-Preflight-Error": type(error).__name__}) from None

    @service.post("/postcheck")
    async def postcheck(request: Request):
        if not connected or service.state.postchecker is None:
            raise HTTPException(503, detail="Connected video inspection is unavailable.")
        from cloud.postcheck import InvalidClip, MAX_UPLOAD_BYTES, PostcheckUnavailable
        from cloud.store import StoreRateLimited, StoreBudgetExhausted, StoreDataUnavailable

        content_type = request.headers.get("content-type", "").lower()
        if not content_type.startswith("multipart/form-data;"):
            raise HTTPException(415, detail="Upload an MP4 using multipart form data.")
        raw_length = request.headers.get("content-length")
        try:
            if raw_length is not None and int(raw_length) > MAX_UPLOAD_BYTES + 16384:
                raise HTTPException(413, detail="Upload an MP4 no larger than 30 MiB.")
        except ValueError:
            raise HTTPException(400, detail="Invalid upload size header.") from None
        if service.state.postcheck_slot.locked():
            raise HTTPException(429, detail="A clip is being inspected. Try again shortly.", headers={"Retry-After": "10"})
        async with service.state.postcheck_slot:
            try:
                async with request.form(max_files=1, max_fields=2, max_part_size=8192) as form:
                    if set(form) - {"video", "prompt", "model"} or len(form.getlist("video")) != 1:
                        raise HTTPException(422, detail="Supply one video, its prompt and an optional model label.")
                    video = form.get("video")
                    if not isinstance(video, UploadFile):
                        raise HTTPException(422, detail="Select an MP4 file.")
                    if (not str(video.filename or "").lower().endswith(".mp4")
                            or video.content_type not in ("video/mp4", "application/octet-stream")):
                        raise HTTPException(415, detail="This preview accepts MP4 video files.")
                    raw_prompt, raw_model = form.get("prompt"), form.get("model", "owner-upload")
                    if not isinstance(raw_prompt, str) or not 1 <= len(raw_prompt.strip()) <= 4000:
                        raise HTTPException(422, detail="Enter a scene prompt between 1 and 4,000 characters.")
                    if not isinstance(raw_model, str) or not 1 <= len(raw_model.strip()) <= 200:
                        raise HTTPException(422, detail="Enter a model label between 1 and 200 characters.")
                    prompt, model = raw_prompt.strip(), raw_model.strip()
                    await asyncio.to_thread(service.state.store.admit_request)
                    with tempfile.TemporaryDirectory(prefix="preflight-upload-") as directory:
                        path = Path(directory) / "clip.mp4"
                        digest = hashlib.sha256()
                        total_bytes = 0
                        with path.open("wb") as destination:
                            while chunk := await video.read(1024 * 1024):
                                total_bytes += len(chunk)
                                if total_bytes > MAX_UPLOAD_BYTES:
                                    raise HTTPException(413, detail="Upload an MP4 no larger than 30 MiB.")
                                digest.update(chunk)
                                destination.write(chunk)
                        if not total_bytes:
                            raise HTTPException(422, detail="The uploaded video is empty.")
                        source_sha256 = digest.hexdigest()
                        checker = service.state.postchecker
                        identifier = hashlib.sha256(json.dumps(
                            ["postcheck-v1", source_sha256, prompt, model, checker.model_name],
                            ensure_ascii=False, separators=(",", ":"),
                        ).encode()).hexdigest()
                        before = await asyncio.to_thread(service.state.store.difficulty, prompt)
                        existing = await asyncio.to_thread(service.state.store.get_verdict, identifier)
                        model_calls_this_request = 0
                        concurrent_review_discarded = False
                        if existing is not None:
                            review = existing.get("review")
                            if (not review or review.get("source_sha256") != source_sha256
                                    or existing.get("prompt") != prompt or existing.get("model") != model):
                                raise StoreDataUnavailable("Stored review identity differs")
                            created = False
                        else:
                            review = await checker.review(path, prompt, model)
                            model_calls_this_request = int(review.get("analysis", {}).get("actual_model_calls", 0))
                            if review.get("source_sha256") != source_sha256 or not isinstance(review.get("pass_bool"), bool):
                                raise PostcheckUnavailable("The inspected video identity could not be verified")
                            try:
                                recorded = await asyncio.to_thread(
                                    service.state.store.record_verdict, prompt, model,
                                    review["pass_bool"], review["defects"], verdict_id=identifier, review=review,
                                )
                                created = recorded["created"]
                            except ValueError:
                                # Another instance can commit a valid review while this
                                # request is inspecting the same immutable clip identity.
                                existing = await asyncio.to_thread(service.state.store.get_verdict, identifier)
                                canonical = existing.get("review") if existing else None
                                if (not canonical or canonical.get("source_sha256") != source_sha256
                                        or existing.get("prompt") != prompt or existing.get("model") != model):
                                    raise StoreDataUnavailable("Stored review identity differs") from None
                                review, created = canonical, False
                                concurrent_review_discarded = True
                        after = await asyncio.to_thread(service.state.store.difficulty, prompt)
                        return {
                            **review, "verdict_id": identifier, "mode": selected_mode,
                            "risk_before": before.get("p_fail"), "risk_after": after.get("p_fail"),
                            "historical_p_fail": after.get("historical_p_fail", before.get("p_fail")),
                            "risk_semantics": after.get("risk_semantics"),
                            "feedback": after.get("postcheck_feedback", {}),
                            "feedback_recorded": True, "feedback_created": created,
                            "reused_stored_review": existing is not None,
                            "model_calls_this_request": model_calls_this_request,
                            "concurrent_review_discarded": concurrent_review_discarded,
                        }
            except HTTPException:
                raise
            except StarletteHTTPException:
                raise HTTPException(422, detail="Supply one MP4, its prompt and an optional model label.") from None
            except (ValueError, MultiPartException, InvalidClip):
                raise HTTPException(422, detail="The MP4 could not be inspected within the 30 MiB, 30-second video limits.") from None
            except StoreRateLimited as error:
                raise HTTPException(429, detail="This preview allows 20 checks per minute. Try again shortly.",
                                    headers={"Retry-After": str(error.retry_after)}) from None
            except StoreBudgetExhausted:
                raise HTTPException(429, detail="This preview's cumulative request budget is exhausted.") from None
            except Exception as error:
                headers = {"X-Preflight-Error": type(error).__name__}
                upstream_status = getattr(error, "upstream_status", None)
                if isinstance(upstream_status, int) and 100 <= upstream_status <= 599:
                    headers["X-Preflight-Upstream-Status"] = str(upstream_status)
                raise HTTPException(503, detail="Connected video inspection or verdict storage is unavailable.",
                                    headers=headers) from None

    @service.get("/")
    def home():
        return FileResponse(ROOT / "static" / "index.html")

    @service.get("/architecture")
    def architecture():
        return FileResponse(ROOT / "static" / "architecture.html")

    service.mount("/static", StaticFiles(directory=ROOT / "static", check_dir=False), name="static")
    return service


app = create_app()
