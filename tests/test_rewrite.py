"""Execute the real ADK tool loop against synthetic model and predictor fixtures."""
from __future__ import annotations

import asyncio

import pytest
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.sessions import InMemorySessionService
from google.genai import types

from cloud.rewrite_agent import RewriteService, RewriteUnavailable, select_rewrite


class PlanningModel(BaseLlm):
    model: str = "gemini-synthetic-test"
    calls: int = 0

    async def generate_content_async(self, llm_request, stream=False):
        self.calls += 1
        prompt = next(
            part.text for content in llm_request.contents if content.role == "user"
            for part in content.parts if part.text
        )
        allowed = llm_request.config.tool_config.function_calling_config.allowed_function_names
        if "rewrite" in allowed:
            calls = [("rewrite", {"prompt": prompt, "reasons": ["Compare the retrieved historical neighbours"]})]
        elif "nearest_prompts" in allowed:
            calls = [("nearest_prompts", {"prompt": prompt}), ("difficulty", {"prompt": prompt})]
        else:
            proposals = next(
                part.function_response.response["candidates"]
                for content in reversed(llm_request.contents) for part in content.parts
                if part.function_response and part.function_response.name == "rewrite"
            )
            calls = [("difficulty", {"prompt": candidate}) for candidate in proposals]
        yield LlmResponse(content=types.Content(role="model", parts=[
            types.Part(function_call=types.FunctionCall(name=name, id=f"synthetic-{self.calls}-{index}", args=arguments))
            for index, (name, arguments) in enumerate(calls)
        ]))


class DirectAnswerModel(PlanningModel):
    async def generate_content_async(self, llm_request, stream=False):
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="A rewrite without the tool is not valid")]))


class SyntheticEngine:
    def __init__(self, rates):
        self.rates = rates
        self.requested = []

    def predict(self, prompt):
        self.requested.append(prompt)
        return {
            "supported": self.rates[prompt] is not None,
            "p_fail": self.rates[prompt],
            "difficulty": 0.8,
            "nearest_prompts": [
                {"prompt": "a steady cat scene", "both_bad_rate": 0.2, "similarity": 0.7},
                {"prompt": "a dog beside a cat", "both_bad_rate": 0.5, "similarity": 0.4},
            ],
        }


class SessionFixture(InMemorySessionService):
    """In-memory session fixture accepting the managed service's TTL option."""
    async def create_session(self, *, ttl=None, **kwargs):
        self.last_ttl = ttl
        return await super().create_session(**kwargs)


def configured_service(engine, model=None, candidates=None):
    sessions = SessionFixture()
    actual_model = model or PlanningModel()

    async def generate(prompt, reasons, evidence):
        assert prompt == "original cat and dog"
        assert reasons and evidence
        return candidates or ["clear cat beside dog", "busy cat and dog"]

    service = RewriteService(
        engine,
        session_service=sessions,
        app_name="preflight_synthetic_tests",
        model_name="gemini-synthetic-test",
        model=actual_model,
        candidate_generator=generate,
    )
    return service, sessions, actual_model


def test_real_adk_tools_measure_candidates_and_persist_session():
    async def run():
        engine = SyntheticEngine({"original cat and dog": 0.6, "clear cat beside dog": 0.2, "busy cat and dog": 0.8})
        service, sessions, model = configured_service(engine)
        result = await service.preflight("original cat and dog", user_id="synthetic_user")
        assert result["rewrite_status"] == "improved"
        assert result["rewritten_prompt"] == "clear cat beside dog"
        assert result["p_fail_before"] == 0.6
        assert result["p_fail_after"] == 0.2
        assert model.calls == 3
        assert result["tool_call_count"] == 5
        assert [row["tool"] for row in result["tool_trace"]] == ["nearest_prompts", "difficulty", "rewrite", "difficulty", "difficulty"]
        assert result["session_verified"]
        saved = await sessions.get_session(app_name=service.app_name, user_id="synthetic_user", session_id=result["session_id"])
        assert sum(len(event.get_function_calls()) for event in saved.events) == 5
        assert engine.requested.count("original cat and dog") == 1
        assert "a steady cat scene" in result["reasons"][0]
        assert len(result["reasons"]) <= 2
        assert result["agent_trace"]["planner_model_calls"] == 3
        assert result["agent_trace"]["rewrite_model_calls"] == 1
    asyncio.run(run())


def test_equal_or_worse_candidates_always_return_original():
    async def run():
        engine = SyntheticEngine({"original cat and dog": 0.4, "clear cat beside dog": 0.4, "busy cat and dog": 0.9})
        service, _, _ = configured_service(engine)
        result = await service.preflight("original cat and dog")
        assert result["rewrite_status"] == "no_safe_rewrite"
        assert result["rewritten_prompt"] == "original cat and dog"
        assert result["p_fail_after"] == result["p_fail_before"] == 0.4
        assert result["rewrite_message"] == "no safe rewrite found"
    asyncio.run(run())


def test_a_direct_model_answer_cannot_fake_a_completed_rewrite():
    async def run():
        engine = SyntheticEngine({"original cat and dog": 0.5})
        service, _, _ = configured_service(engine, model=DirectAnswerModel())
        with pytest.raises(RewriteUnavailable, match="Required ADK tool executions"):
            await service.preflight("original cat and dog")
    asyncio.run(run())


def test_live_predictor_overrides_engine_rates_and_session_can_continue():
    async def run():
        engine = SyntheticEngine({"original cat and dog": 0.7, "clear cat beside dog": 0.3, "busy cat and dog": 0.9})
        service, _, _ = configured_service(engine)
        seen = []

        async def live_prediction(prompt):
            seen.append(prompt)
            result = engine.predict(prompt)
            if prompt == "clear cat beside dog":
                result["p_fail"] = 0.8
            return result

        service.predictor = live_prediction
        first = await service.preflight("original cat and dog", user_id="same_user")
        assert first["rewrite_status"] == "no_safe_rewrite"
        second = await service.preflight("original cat and dog", user_id="same_user", session_id=first["session_id"])
        assert second["session_id"] == first["session_id"]
        assert second["session_event_count"] > first["session_event_count"]
        assert seen.count("original cat and dog") == 2
    asyncio.run(run())


def test_generator_failure_has_no_success_fallback_or_sensitive_error_text():
    async def run():
        engine = SyntheticEngine({"original cat and dog": 0.7})
        service, _, _ = configured_service(engine)

        async def failed_generator(prompt, reasons, evidence):
            raise RuntimeError("synthetic private upstream diagnostic")

        service.candidate_generator = failed_generator
        with pytest.raises(RewriteUnavailable) as failure:
            await service.preflight("original cat and dog")
        assert "private upstream" not in str(failure.value)
    asyncio.run(run())


def test_guard_rejects_unmeasured_and_unchanged_candidates():
    result = select_rewrite("original", 0.4, [("unmeasured", None), ("original", 0.1), ("equal", 0.4)])
    assert result["rewritten_prompt"] == "original"
    assert result["rewrite_status"] == "no_safe_rewrite"
    improved = select_rewrite("original", 0.4, [("lower", 0.399)])
    assert improved["rewritten_prompt"] == "lower"
    assert improved["p_fail_after"] < improved["p_fail_before"]


def test_session_readiness_checks_persisted_state_without_model_call():
    async def run():
        service, sessions, model = configured_service(SyntheticEngine({}))
        assert not service.session_active
        assert await service.healthcheck()
        assert service.session_active
        assert sessions.last_ttl == "86400s"
        assert model.calls == 0
    asyncio.run(run())
