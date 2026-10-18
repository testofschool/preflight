"""Config-only cap gate: samples-only admissions never call an image model."""
from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from app import SAMPLES, create_app
from cloud.preview import LIVE_LIMITED_MESSAGE, PRIMARY, sample_preview_cache_key
from cloud.sample_rewrites import load_sample_rewrites
from cloud.store import StoreBudgetExhausted, StoreRateLimited
from test_cloud_api import ConnectedRewrite
from test_preview import PreviewStore, Provider


# Keep every original and pinned rewrite as a case, even the unchanged gym rewrite.
SAMPLE_CASES = [(f"original-{index}", prompt) for index, prompt in enumerate(SAMPLES)] + [
    (f"pinned-rewrite-{index}", row["rewritten_prompt"])
    for index, row in enumerate(load_sample_rewrites(SAMPLES).values())]


class ModelTripwire:
    model, size = PRIMARY, "1K"

    def __init__(self):
        self.calls = 0

    async def generate(self, prompt):
        self.calls += 1
        raise AssertionError("Samples-only requests must never generate")


@pytest.fixture
def samples_only(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "false")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_WARM_ENABLED", "false")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_DAILY_LIMIT", "500")
    store, model, constructors = PreviewStore(), ModelTripwire(), []

    def factory():
        constructors.append(True)
        return model

    service = create_app(mode="cloud", store_factory=lambda: store,
                         rewrite_factory=ConnectedRewrite, preview_factory=factory)
    with TestClient(service) as client:
        assert client.get("/api/status").json()["preview_mode"] == "samples"
        assert service.state.previewer is None
        assert service.state.preview_live_enabled is False
        assert service.state.preview_warm_enabled is False
        assert constructors == []
        yield client, service, store, model
    assert constructors == []
    assert model.calls == 0


@pytest.mark.parametrize("case,prompt", SAMPLE_CASES, ids=[case for case, _ in SAMPLE_CASES])
@pytest.mark.parametrize("variant", ["original", "rewrite"])
@pytest.mark.parametrize("cached", [True, False], ids=["saved-hit", "missing-document"])
def test_every_admitted_original_and_rewrite_path_makes_zero_model_calls(
        samples_only, case, prompt, variant, cached):
    client, service, store, model = samples_only
    # Also prove the route does not use a stale provider if one is present.
    service.state.previewer = model
    if cached:
        store.save_preview(sample_preview_cache_key(prompt), {
            "bytes": Provider().jpeg, "model": PRIMARY, "size": "1K",
            "created_at": datetime(2026, 10, 18, tzinfo=timezone.utc)})
    result = client.post("/preview", json={"prompt": prompt, "variant": variant})
    assert store.client.documents["service_v1/preview-budget"]["day_count"] == 1
    assert model.calls == 0
    if cached:
        assert result.status_code == 200
        assert result.headers["x-preview-cache"] == result.json()["cache"] == "hit"
        assert result.json()["model_calls"] == result.json()["cost_usd"] == 0
    else:
        assert result.status_code == 503
        assert result.json()["detail"] == LIVE_LIMITED_MESSAGE
        assert not any(key.startswith("previews_v1/") for key in store.client.documents)


@pytest.mark.parametrize("prompt", ["a bicycle on a quiet road", SAMPLES[0] + "."])
@pytest.mark.parametrize("variant", ["original", "rewrite"])
def test_typed_prompts_never_reach_admission_even_if_cached(samples_only, prompt, variant):
    client, service, store, model = samples_only
    service.state.previewer = model
    store.save_preview(sample_preview_cache_key(prompt), {
        "bytes": Provider().jpeg, "model": PRIMARY, "size": "1K",
        "created_at": datetime.now(timezone.utc)})
    result = client.post("/preview", json={"prompt": prompt, "variant": variant})
    assert result.status_code == 503 and result.json()["detail"] == LIVE_LIMITED_MESSAGE
    assert "service_v1/preview-budget" not in store.client.documents
    assert model.calls == 0


@pytest.mark.parametrize("variant", ["original", "rewrite"])
@pytest.mark.parametrize("cached", [True, False])
def test_whitespace_normalized_sample_is_admitted_without_generation(samples_only, variant, cached):
    client, service, store, model = samples_only
    service.state.previewer = model
    if cached:
        store.save_preview(sample_preview_cache_key(SAMPLES[0]), {
            "bytes": Provider().jpeg, "model": PRIMARY, "size": "1K",
            "created_at": datetime.now(timezone.utc)})
    result = client.post("/preview", json={"prompt": " " + SAMPLES[0] + " ", "variant": variant})
    assert result.status_code == (200 if cached else 503)
    assert store.client.documents["service_v1/preview-budget"]["day_count"] == 1
    assert model.calls == 0


@pytest.mark.parametrize("created_at,expected", [
    ("2026-10-18T00:00:00Z", 200), ("not-a-date", 503),
    (datetime(2026, 10, 18), 503), (None, 503)])
def test_saved_metadata_success_and_errors_do_not_generate(samples_only, created_at, expected):
    client, service, store, model = samples_only
    service.state.previewer = model
    store.save_preview(sample_preview_cache_key(SAMPLES[0]), {
        "bytes": Provider().jpeg, "model": PRIMARY, "size": "1K", "created_at": created_at})
    result = client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"})
    assert result.status_code == expected
    assert store.client.documents["service_v1/preview-budget"]["day_count"] == 1
    assert model.calls == 0


@pytest.mark.parametrize("operation,error,expected", [
    ("admit_preview", StoreRateLimited(17), 429),
    ("admit_preview", StoreBudgetExhausted(), 429),
    ("admit_preview", RuntimeError("local admission failure"), 503),
    ("get_preview", RuntimeError("local cache failure"), 503)])
def test_admission_and_cache_failures_do_not_generate(samples_only, monkeypatch, operation, error, expected):
    client, service, store, model = samples_only
    service.state.previewer = model

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(store, operation, fail)
    result = client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"})
    assert result.status_code == expected and model.calls == 0


def test_raised_daily_limit_keeps_five_per_minute_and_ceiling(samples_only):
    client, _, store, model = samples_only
    store.save_preview(sample_preview_cache_key(SAMPLES[0]), {
        "bytes": Provider().jpeg, "model": PRIMARY, "size": "1K",
        "created_at": datetime.now(timezone.utc)})
    for _ in range(5):
        assert client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"}).status_code == 200
    sixth = client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"})
    assert sixth.status_code == 429 and 1 <= int(sixth.headers["retry-after"]) <= 60
    store.client.documents["service_v1/preview-budget"] = {
        "day": datetime.now(timezone.utc).date().isoformat(), "day_count": 499, "request_timestamps": []}
    assert client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"}).status_code == 200
    assert store.client.documents["service_v1/preview-budget"]["day_count"] == 500
    assert client.post("/preview", json={"prompt": SAMPLES[0], "variant": "original"}).status_code == 429
    assert model.calls == 0
