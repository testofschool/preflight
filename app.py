"""Local G0 service. All predictions use bundled public historical votes."""

from collections import deque
from contextlib import asynccontextmanager
import asyncio
import os
from pathlib import Path
import re
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from preflight_core import PreflightEngine


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
               store_factory=None, rewrite_factory=None) -> FastAPI:
    selected_mode = mode or os.environ.get("PREFLIGHT_MODE", "local-g0")
    if selected_mode not in ("local-g0", "cloud"):
        raise ValueError("Unsupported runtime mode")
    connected = selected_mode == "cloud"

    @asynccontextmanager
    async def lifespan(service: FastAPI):
        service.state.engine = PreflightEngine.load(artifact_dir or ROOT / "artifacts")
        service.state.budget = RequestBudget()
        service.state.connected = connected
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
        yield

    service = FastAPI(title="Preflight", lifespan=lifespan)

    @service.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
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
            "postcheck": False,
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

    @service.get("/")
    def home():
        return FileResponse(ROOT / "static" / "index.html")

    @service.get("/architecture")
    def architecture():
        return FileResponse(ROOT / "static" / "architecture.html")

    service.mount("/static", StaticFiles(directory=ROOT / "static", check_dir=False), name="static")
    return service


app = create_app()
