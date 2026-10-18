"""Image preview regressions: all storage/provider calls use local fakes."""
import io
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import create_app
from cloud.preview import CAPTION, PRIMARY, FALLBACK, PreviewResult
from cloud.store import FirestoreDifficultyStore
from test_cloud_api import ConnectedRewrite
from test_store import MemoryClient


def transactional(fn):
    def run(tx):
        result = fn(tx)
        tx.commit()
        return result
    return run


class PreviewStore(FirestoreDifficultyStore):
    def __init__(self):
        super().__init__(MemoryClient(), transactional)


class Provider:
    model, size = PRIMARY, "1K"
    cache_models = [(PRIMARY, "1K"), (FALLBACK, "0.5K")]

    def __init__(self):
        self.calls = 0
        buffer = io.BytesIO()
        Image.new("RGB", (160, 90), "green").save(buffer, "JPEG", quality=82)
        self.jpeg = buffer.getvalue()

    async def generate(self, prompt, **kwargs):
        self.calls += 1
        return PreviewResult(self.jpeg, self.model, self.size, .0336, 1, False)


@pytest.fixture
def connected(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_DAILY_LIMIT", "60")
    store, provider = PreviewStore(), Provider()
    service = create_app(mode="cloud", store_factory=lambda: store,
                         rewrite_factory=ConnectedRewrite, preview_factory=lambda: provider)
    with TestClient(service) as client:
        yield client, store, provider


def call(client, **changes):
    return client.post("/preview", json={"prompt": "a cat and a dog", "variant": "original", **changes})


def test_cache_hit_no_provider_call(connected):
    client, store, provider = connected
    assert call(client).json()["model_calls"] == 1
    result = call(client, variant="rewrite")
    assert result.status_code == 200
    assert result.headers["x-preview-cache"] == "hit"
    assert result.json()["model_calls"] == 0
    assert provider.calls == 1
    assert len([key for key in store.client.documents if key.startswith("previews_v1/")]) == 1


def test_sixth_call_is_rate_limited(connected):
    client, _, _ = connected
    for _ in range(5):
        assert call(client).status_code == 200
    result = call(client)
    assert result.status_code == 429
    assert 1 <= int(result.headers["retry-after"]) <= 60


def test_daily_cap(connected, monkeypatch):
    client, _, provider = connected
    monkeypatch.setenv("PREFLIGHT_PREVIEW_DAILY_LIMIT", "1")
    assert call(client).status_code == 200
    assert call(client).status_code == 429
    assert provider.calls == 1


def test_oversized_image_not_cached(connected):
    client, store, provider = connected
    provider.jpeg = b"x" * (900 * 1024 + 1)
    result = call(client)
    assert result.status_code == 200
    assert result.headers["x-preview-cache"] == "skip-size"
    assert not any(key.startswith("previews_v1/") for key in store.client.documents)


def test_provider_exception_is_redacted(connected):
    client, _, provider = connected
    async def fail(prompt, **kwargs):
        raise RuntimeError("private provider message")
    provider.generate = fail
    result = call(client)
    assert result.status_code == 503
    assert result.headers["x-preflight-error"] == "RuntimeError"
    assert "private provider message" not in result.text
    assert result.json()["detail"] == "Preview is busy right now — try again in a minute. The risk check still works."


def test_unknown_field_forbidden(connected):
    assert call(connected[0], unknown=True).status_code == 422


def test_caption_exact(connected):
    assert call(connected[0]).json()["caption"] == CAPTION == (
        "A still from an image model, not a Veo frame. Motion, flicker and timing cannot be judged from a still.")


def test_local_preview_unavailable():
    with TestClient(create_app(mode="local-g0")) as client:
        assert client.get("/api/status").json()["preview"] is False
        assert call(client).json()["detail"] == "Preview is busy right now — try again in a minute. The risk check still works."


def test_ceiling_and_utc_reset(connected, monkeypatch):
    _, store, _ = connected
    monkeypatch.setenv("PREFLIGHT_PREVIEW_DAILY_LIMIT", "9999")
    store.client.documents["service_v1/preview-budget"] = {
        "day": datetime.now(timezone.utc).date().isoformat(), "day_count": 500}
    from cloud.store import StoreBudgetExhausted
    with pytest.raises(StoreBudgetExhausted):
        store.admit_preview()
    store.client.documents["service_v1/preview-budget"]["day"] = "2000-01-01"
    store.admit_preview()
    assert store.client.documents["service_v1/preview-budget"]["day_count"] == 1


def test_fallback_is_cached_under_actual_model_and_reported(connected):
    import hashlib
    import json
    client, store, provider = connected
    async def fallback(prompt, **kwargs):
        provider.calls += 3
        return PreviewResult(provider.jpeg, FALLBACK, "0.5K", .045, 3, True)
    provider.generate = fallback
    first = call(client)
    assert first.status_code == 200
    data = first.json()
    assert (data["model"], data["size"], data["cost_usd"], data["attempts"], data["fallback_used"], data["model_calls"]) == (
        FALLBACK, "0.5K", .045, 3, True, 3)
    key = hashlib.sha256(json.dumps(["preview-v1", "a cat and a dog", FALLBACK, "0.5K"],
        separators=(",", ":")).encode()).hexdigest()
    assert "previews_v1/" + key in store.client.documents
    second = call(client)
    assert second.headers["x-preview-cache"] == "hit"
    assert (second.json()["model"], second.json()["attempts"], second.json()["model_calls"], second.json()["fallback_used"]) == (
        FALLBACK, 0, 0, True)
    assert provider.calls == 3


def test_primary_cache_is_preferred_over_fallback(connected):
    import hashlib
    import json
    client, store, provider = connected
    for model, size in provider.cache_models:
        key = hashlib.sha256(json.dumps(["preview-v1", "a cat and a dog", model, size], separators=(",", ":")).encode()).hexdigest()
        store.save_preview(key, {"bytes": provider.jpeg, "model": model, "size": size})
    response = call(client)
    assert response.headers["x-preview-cache"] == "hit"
    assert response.json()["model"] == PRIMARY
    assert response.json()["fallback_used"] is False
    assert provider.calls == 0


def test_failure_keeps_attempt_receipt_without_provider_detail(connected):
    from cloud.preview import PreviewGenerationError
    client, _, provider = connected
    trail = [{"model": PRIMARY, "size": "1K", "attempt": 1, "outcome": "retryable_error", "code": 503},
             {"model": PRIMARY, "size": "1K", "attempt": 2, "outcome": "retryable_error", "code": 503},
             {"model": FALLBACK, "size": "0.5K", "attempt": 3, "outcome": "timeout"}]
    async def fail(prompt, **kwargs):
        raise PreviewGenerationError(attempts=3, model=FALLBACK, fallback_used=True, model_attempts=trail)
    provider.generate = fail
    response = call(client)
    assert response.status_code == 503
    assert response.json()["attempts"] == response.json()["model_calls"] == 3
    assert response.json()["fallback_used"] is True
    assert response.json()["model"] == FALLBACK
    assert response.json()["model_attempts"] == trail
