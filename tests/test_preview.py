"""Image preview regressions: all storage/provider calls use local fakes."""
import io
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import create_app
from cloud.preview import CAPTION, LIVE_LIMITED_MESSAGE, PRIMARY
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

    def __init__(self):
        self.calls = 0
        buffer = io.BytesIO()
        Image.new("RGB", (160, 90), "green").save(buffer, "JPEG", quality=82)
        self.jpeg = buffer.getvalue()

    async def generate(self, prompt):
        self.calls += 1
        return self.jpeg


@pytest.fixture
def connected(monkeypatch, tmp_path):
    monkeypatch.setenv("PREFLIGHT_PREVIEW_DAILY_LIMIT", "60")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_LIVE_ENABLED", "true")
    monkeypatch.setenv("PREFLIGHT_PREVIEW_WARM_ENABLED", "true")
    store, provider = PreviewStore(), Provider()
    service = create_app(mode="cloud", store_factory=lambda: store,
                         rewrite_factory=ConnectedRewrite, preview_factory=lambda: provider,
                         sample_rewrites_path=tmp_path / "absent.json")
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
    async def fail(prompt):
        raise RuntimeError("private provider message")
    provider.generate = fail
    result = call(client)
    assert result.status_code == 503
    assert result.headers["x-preflight-error"] == "RuntimeError"
    assert "private provider message" not in result.text
    assert result.json()["detail"] == LIVE_LIMITED_MESSAGE


def test_unknown_field_forbidden(connected):
    assert call(connected[0], unknown=True).status_code == 422


def test_caption_exact(connected):
    assert call(connected[0]).json()["caption"] == CAPTION == (
        "A still from an image model, not a Veo frame. Motion, flicker and timing cannot be judged from a still.")


def test_local_preview_unavailable():
    with TestClient(create_app(mode="local-g0")) as client:
        status = client.get("/api/status").json()
        assert status["preview"] is False
        assert status["preview_mode_message"] == "Image preview — Not active; live generation limited"
        assert call(client).json()["detail"] == LIVE_LIMITED_MESSAGE


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
