"""Sample identity, saved metadata, and guarded live arms; all dependencies are local."""
import asyncio
from datetime import datetime, timezone
import io
import json
from types import SimpleNamespace
from time import monotonic

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from app import SAMPLES, create_app
from cloud.preview import (FALLBACK, ImagePreviewService, LIVE_LIMITED_MESSAGE, PRIMARY,
                           PRIORITY_HEADER, SEPARATE_CAPACITY, image_pricing, image_settings,
                           preview_cache_key, sample_preview_cache_key)
from cloud.sample_rewrites import load_sample_rewrites
from test_cloud_api import ConnectedRewrite, ConnectedStore
from test_preview import PreviewStore, Provider


@pytest.fixture
def pins(tmp_path):
    path = tmp_path / "sample_rewrites.json"
    rows = [{"prompt": prompt, "rewrite": {
        "rewritten_prompt": prompt + ", clearly separated in a steady shot",
        "p_fail_before": 0.8, "p_fail_after": 0.2, "rewrite_status": "improved",
        "risk_semantics": "Saved human vote estimate; current video quality is unvalidated.",
        "session_id": "saved-session", "session_verified": True,
        "agent_trace": {"planner_model_calls": 4, "rewrite_model_calls": 1}}} for prompt in SAMPLES]
    path.write_text(json.dumps({"schema_version": 1, "source": "real-rewrite-agent",
        "generated_at": "2026-10-18T02:00:00+00:00", "samples": rows}))
    return path


def app_for(pins, store, provider=None):
    return create_app(mode="cloud", store_factory=lambda: store,
        rewrite_factory=ConnectedRewrite, preview_factory=(lambda: provider) if provider else None,
        sample_rewrites_path=pins)


def test_only_exact_samples_use_saved_rewrites_and_keep_fixed_risk(pins):
    service = app_for(pins, ConnectedStore())
    with TestClient(service) as client:
        for prompt in SAMPLES:
            result = client.post("/preflight", json={"prompt": prompt}).json()
            assert result["rewrite_source"] == "pinned-sample"
            assert result["p_fail"] == result["p_fail_before"] == 0.8
            assert result["p_fail_after"] == 0.2
            assert result["risk_semantics"].startswith("Saved human vote")
            assert result["rewrite_model_calls_this_request"] == 0
            assert result["agent_trace_saved"] is True
            assert "session_id" not in result and "session_verified" not in result
        assert not service.state.rewriter.users
        live = client.post("/preflight", json={"prompt": SAMPLES[0] + "."}).json()
        assert live["rewrite_source"] == "live"
        whitespace = client.post("/preflight", json={"prompt": " " + SAMPLES[0]}).json()
        assert whitespace["rewrite_source"] == "live"
        assert len(service.state.rewriter.users) == 2


def test_saved_sample_stills_work_without_live_client_and_use_real_saved_date(pins, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "false")
    store, provider = PreviewStore(), Provider()
    prompts = list(SAMPLES) + [row["rewritten_prompt"] for row in load_sample_rewrites(SAMPLES, pins).values()]
    for prompt in prompts:
        store.save_preview(sample_preview_cache_key(prompt), {"bytes": provider.jpeg,
            "model": FALLBACK, "size": "0.5K", "created_at": datetime(2026, 10, 17, tzinfo=timezone.utc)})
    # Keep this ten-image data test independent from the separately tested 5/min cap.
    monkeypatch.setattr(store, "admit_preview", lambda: None)
    with TestClient(app_for(pins, store)) as client:
        status = client.get("/api/status").json()
        assert status["preview"] is True and status["preview_mode"] == "samples"
        assert status["preview_mode_message"] == (
            "Image preview — Active for sample prompts (saved stills); live generation limited")
        for index, prompt in enumerate(prompts):
            response = client.post("/preview", json={"prompt": prompt,
                "variant": "original" if index < 5 else "rewrite"})
            assert response.status_code == 200
            assert response.headers["x-preview-cache"] == "hit"
            result = response.json()
            assert result["model_calls"] == result["cost_usd"] == 0
            assert result["model"] == FALLBACK and result["size"] == "0.5K"
            assert result["metadata_label"] == (
                "Saved still · generated 2026-10-17 · 0 model calls · $0.00")
            assert result["generated_date"] == "2026-10-17"
    assert provider.calls == 0


def test_samples_only_misses_and_arbitrary_cached_prompts_fail_closed(pins, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "false")
    store, provider = PreviewStore(), Provider()
    typed = "a cat and a dog outside"
    store.save_preview(sample_preview_cache_key(typed), {"bytes": provider.jpeg,
        "model": PRIMARY, "size": "1K", "created_at": datetime.now(timezone.utc)})
    with TestClient(app_for(pins, store, provider)) as client:
        for prompt in (SAMPLES[0], typed):
            response = client.post("/preview", json={"prompt": prompt, "variant": "original"})
            assert response.status_code == 503 and response.json()["detail"] == LIVE_LIMITED_MESSAGE
    assert provider.calls == 0


def test_live_mode_single_call_then_hit_reports_zero_cost(pins, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "true")
    store, provider = PreviewStore(), Provider()
    with TestClient(app_for(pins, store, provider)) as client:
        assert client.get("/api/status").json()["preview_mode"] == "samples+live"
        request = {"prompt": "a bicycle beside a red car outside", "variant": "original"}
        first = client.post("/preview", json=request).json()
        assert first["model_calls"] == 1 and first["cost_usd"] == 0.0336
        assert first["metadata_label"].startswith("Model gemini-3.1-flash-lite-image · 1K · $0.0336 · ")
        hit = client.post("/preview", json=request).json()
        assert hit["model_calls"] == hit["cost_usd"] == 0
        assert provider.calls == 1
        assert any(preview_cache_key(request["prompt"], PRIMARY, "1K") in key
                   for key in store.client.documents)


def test_warm_mode_generates_only_sample_misses_through_admitted_route(pins, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "false")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_WARM_ENABLED", "true")
    store, provider = PreviewStore(), Provider()
    with TestClient(app_for(pins, store, provider)) as client:
        status = client.get("/api/status").json()
        assert status["preview"] is True and status["preview_mode"] == "samples"
        assert status["preview_mode_message"].endswith("live generation limited")
        typed = client.post("/preview", json={"prompt": "a bicycle on a quiet road", "variant": "original"})
        assert typed.status_code == 503 and typed.json()["detail"] == LIVE_LIMITED_MESSAGE
        assert provider.calls == 0
        assert "service_v1/preview-budget" not in store.client.documents
        request = {"prompt": SAMPLES[0], "variant": "original"}
        first = client.post("/preview", json=request)
        assert first.status_code == 200 and first.json()["model_calls"] == 1
        assert first.headers["x-preview-cache"] == "miss"
        assert store.client.documents["service_v1/preview-budget"]["day_count"] == 1
        second = client.post("/preview", json=request)
        assert second.status_code == 200 and second.json()["model_calls"] == 0
        assert second.headers["x-preview-cache"] == "hit"
        assert provider.calls == 1
        assert store.client.documents["service_v1/preview-budget"]["day_count"] == 2
    # A fresh revision with warming switched off still reads the saved image.
    monkeypatch.setenv("PREFLIGHT_PREVIEW_WARM_ENABLED", "false")
    with TestClient(app_for(pins, store, provider)) as client:
        cached = client.post("/preview", json=request)
        assert cached.status_code == 200 and cached.json()["model_calls"] == 0
        miss = client.post("/preview", json={"prompt": SAMPLES[1], "variant": "original"})
        assert miss.status_code == 503 and provider.calls == 1


def test_sample_miss_requires_warm_flag_even_when_live_is_enabled(pins, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "true")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_WARM_ENABLED", "false")
    store, provider = PreviewStore(), Provider()
    with TestClient(app_for(pins, store, provider)) as client:
        result = client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"})
        assert result.status_code == 503 and result.json()["detail"] == LIVE_LIMITED_MESSAGE
        assert provider.calls == 0


def test_preview_route_deadline_is_below_cloud_run_timeout_and_cancels(pins, monkeypatch):
    import app

    assert app.PREVIEW_HTTP_TIMEOUT_SECONDS == 38
    monkeypatch.setattr(app, "PREVIEW_HTTP_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "true")
    store, provider, cancelled = PreviewStore(), Provider(), []

    async def hang(prompt):
        provider.calls += 1
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)

    provider.generate = hang
    with TestClient(app_for(pins, store, provider)) as client:
        started = monotonic()
        result = client.post("/preview", json={"prompt": "a spoon beside a laptop on a desk", "variant": "original"})
        assert monotonic() - started < 0.5
        assert result.status_code == 503 and result.json()["detail"] == LIVE_LIMITED_MESSAGE
        assert result.headers["x-preflight-error"] == "TimeoutError"
    assert provider.calls == 1 and cancelled == [True]


def test_invalid_pin_score_snapshot_is_rejected(pins):
    fixture = json.loads(pins.read_text())
    fixture["samples"][0]["rewrite"]["p_fail_after"] = 0.9
    pins.write_text(json.dumps(fixture))
    with pytest.raises(ValueError, match="strict improvement"):
        load_sample_rewrites(SAMPLES, pins)


def test_real_committed_fixture_preserves_the_unchanged_guard_result():
    pinned = load_sample_rewrites(SAMPLES)
    assert len(pinned) == 5
    assert sum(row["rewrite_status"] == "improved" for row in pinned.values()) == 4
    gym = pinned["indoor gymnasium"]
    assert gym["rewrite_status"] == "no_safe_rewrite"
    assert gym["rewritten_prompt"] == "indoor gymnasium"
    assert gym["p_fail_before"] == gym["p_fail_after"] == 0.065
    assert all("session_id" not in row and "session_verified" not in row for row in pinned.values())


class Models:
    def __init__(self, traffic="ON_DEMAND", error=None):
        self.calls, self.traffic, self.error = [], traffic, error

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        buffer = io.BytesIO()
        Image.new("RGB", (160, 90), "green").save(buffer, "PNG")
        data = SimpleNamespace(mime_type="image/png", data=buffer.getvalue())
        candidate = SimpleNamespace(content=SimpleNamespace(parts=[SimpleNamespace(inline_data=data)]))
        return SimpleNamespace(candidates=[candidate], usage_metadata=SimpleNamespace(
            traffic_type=self.traffic, prompt_token_count=100, candidates_tokens_details=None))


@pytest.mark.parametrize("arm,model,size,wire,cost", [
    ("P1", PRIMARY, "1K", "1K", 0.06048),
    ("P2", SEPARATE_CAPACITY, "1K", None, 0.0387),
    ("P3", FALLBACK, "0.5K", "512", 0.04482),
])
def test_live_arm_selection_wire_size_and_no_retries(monkeypatch, arm, model, size, wire, cost):
    monkeypatch.setenv("PREFLIGHT_IMAGE_LIVE_ARM", arm)
    models = Models("ON_DEMAND_PRIORITY" if arm == "P1" else "ON_DEMAND")
    provider = ImagePreviewService(client=SimpleNamespace(aio=SimpleNamespace(models=models)))
    assert image_settings() == (model, size)
    assert image_pricing()["usd_per_image"] == cost
    result = asyncio.run(provider.generate("a spoon beside a laptop"))
    assert len(models.calls) == result.model_calls == 1
    assert models.calls[0]["config"].image_config.image_size == wire
    options = models.calls[0]["config"].http_options
    assert options.retry_options.attempts == 1
    assert (options.headers or {}).get(PRIORITY_HEADER) == ("priority" if arm == "P1" else None)


def test_priority_downgrade_uses_standard_price_and_actual_prompt_tokens(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_IMAGE_LIVE_ARM", "P1")
    models = Models("ON_DEMAND")
    result = asyncio.run(ImagePreviewService(client=SimpleNamespace(
        aio=SimpleNamespace(models=models))).generate("a spoon beside a laptop"))
    assert result.cost_usd == 0.033625  # 1,120 image tokens + 100 text input tokens.
    assert result.traffic_type == "ON_DEMAND" and result.priority_traffic_verified
    assert result.billing_verified is False and result.cost_basis == "token-usage-list-price"


@pytest.mark.parametrize("traffic", [None, "UNKNOWN_TRAFFIC"])
def test_priority_unknown_traffic_fails_closed_after_one_attempt(monkeypatch, traffic):
    monkeypatch.setenv("PREFLIGHT_IMAGE_LIVE_ARM", "P1")
    models = Models(traffic)
    provider = ImagePreviewService(client=SimpleNamespace(aio=SimpleNamespace(models=models)))
    with pytest.raises(ValueError, match="traffic price could not be verified"):
        asyncio.run(provider.generate("a spoon beside a laptop"))
    assert len(models.calls) == 1


def test_shared_capacity_failure_is_one_attempt(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_IMAGE_LIVE_ARM", "P3")
    models = Models(error=RuntimeError("private RESOURCE_EXHAUSTED"))
    with pytest.raises(RuntimeError):
        asyncio.run(ImagePreviewService(client=SimpleNamespace(
            aio=SimpleNamespace(models=models))).generate("a spoon beside a laptop"))
    assert len(models.calls) == 1
