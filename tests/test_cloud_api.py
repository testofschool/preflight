from fastapi.testclient import TestClient

from app import create_app
from cloud.store import StoreRateLimited, StoreBudgetExhausted


class ConnectedStore:
    def attach(self, engine):
        self.engine = engine
        return self

    def admit_request(self):
        return {"remaining": 19}

    def difficulty(self, prompt):
        result = self.engine.predict(prompt)
        result["evidence_store"] = "firestore"
        return result


class ConnectedRewrite:
    def __init__(self, engine, predictor):
        self.predictor = predictor
        self.session_active = False
        self.users = []

    async def healthcheck(self):
        self.session_active = True

    async def preflight(self, prompt, *, user_id, session_id=None):
        self.users.append(user_id)
        before = self.predictor(prompt)["p_fail"]
        return {"p_fail_before": before, "p_fail_after": before,
                "rewrite_status": "no_safe_rewrite", "rewritten_prompt": prompt,
                "session_id": session_id or "session-one", "session_verified": True}


def test_connected_cookie_and_session_continuity(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "preflight")
    service = create_app(mode="cloud", store_factory=ConnectedStore, rewrite_factory=ConnectedRewrite)
    with TestClient(service, base_url="https://preview.test") as client:
        first = client.post("/preflight", json={"prompt": "a cat and a dog"})
        assert first.status_code == 200
        assert first.json()["mode"] == "cloud"
        assert first.json()["evidence_store"] == "firestore"
        assert "Secure" in first.headers["set-cookie"]
        assert "HttpOnly" in first.headers["set-cookie"]
        second = client.post("/preflight", json={"prompt": "bridge", "session_id": first.json()["session_id"]})
        assert second.json()["session_id"] == "session-one"
        assert len(set(service.state.rewriter.users)) == 1
        status = client.get("/api/status").json()
        assert all(status[name] for name in ("cloud_run", "gemini", "adk", "firestore", "agent_platform_session"))
        assert status["rate_limit"]["scope"] == "shared Firestore transaction"


def test_cloud_failure_does_not_become_statistical_success():
    class FailedStore(ConnectedStore):
        def difficulty(self, prompt):
            raise RuntimeError("Private configuration must not enter the response")
    service = create_app(mode="cloud", store_factory=FailedStore, rewrite_factory=ConnectedRewrite)
    with TestClient(service) as client:
        result = client.post("/preflight", json={"prompt": "bridge"})
        assert result.status_code == 503
        assert "Private configuration" not in result.text
        assert "p_fail" not in result.json()


def test_cloud_shared_budget_is_propagated():
    class LimitedStore(ConnectedStore):
        def admit_request(self):
            raise StoreRateLimited(17)
    with TestClient(create_app(mode="cloud", store_factory=LimitedStore, rewrite_factory=ConnectedRewrite)) as client:
        result = client.post("/preflight", json={"prompt": "bridge"})
        assert result.status_code == 429
        assert result.headers["retry-after"] == "17"


def test_cloud_cumulative_budget_does_not_offer_a_false_retry_time():
    class ExhaustedStore(ConnectedStore):
        def admit_request(self):
            raise StoreBudgetExhausted()
    with TestClient(create_app(mode="cloud", store_factory=ExhaustedStore, rewrite_factory=ConnectedRewrite)) as client:
        result = client.post("/preflight", json={"prompt": "bridge"})
        assert result.status_code == 429
        assert "retry-after" not in result.headers


def test_cloud_unsupported_query_abstains_without_rewrite():
    service = create_app(mode="cloud", store_factory=ConnectedStore, rewrite_factory=ConnectedRewrite)
    with TestClient(service) as client:
        result = client.post("/preflight", json={"prompt": "zxqvprmlk"})
        assert result.status_code == 200
        assert result.json()["p_fail"] is None
        assert result.json()["rewrite_status"] == "unavailable"
        assert not service.state.rewriter.users
