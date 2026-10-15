from fastapi.testclient import TestClient
import pytest

from app import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as connection:
        yield connection


def test_real_prediction_and_explicit_cloud_status(client):
    result = client.post("/preflight", json={"prompt": "a cat and a dog"})
    assert result.status_code == 200
    payload = result.json()
    assert 0 <= payload["p_fail"] <= 1
    assert len(payload["nearest_prompts"]) == 5
    assert len(payload["p_success_by_model"]) == 10
    assert "rewritten_prompt" not in payload
    assert 3.2 <= payload["est_cost_usd"] <= 16
    status = client.get("/api/status").json()
    assert status["mode"] == "local-g0"
    assert not any(status[name] for name in ("gemini", "adk", "firestore", "cloud_run"))
    assert status["generations"] == 0


@pytest.mark.parametrize("body", [{"prompt": "   "}, {"prompt": "x" * 4001}, {}, {"prompt": 1}])
def test_invalid_input_is_rejected(client, body):
    assert client.post("/preflight", json=body).status_code == 422


def test_out_of_vocabulary_has_no_risk_or_budget_claim(client):
    payload = client.post("/preflight", json={"prompt": "zxqvprmlk"}).json()
    assert payload["supported"] is False
    assert payload["p_fail"] is None
    assert payload["est_cost_usd"] is None


def test_twenty_checks_then_rate_limit(client):
    for _ in range(20):
        assert client.post("/preflight", json={"prompt": "bridge"}).status_code == 200
    limited = client.post("/preflight", json={"prompt": "bridge"})
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"


def test_no_generation_endpoint_and_no_external_scripts(client):
    assert client.post("/generate", json={"prompt": "bridge"}).status_code == 404
    page = client.get("/")
    assert page.status_code == 200
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    assert client.get("/architecture").status_code == 200
