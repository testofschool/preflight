"""Runtime preview behavior uses local clients and never calls a provider."""
import asyncio
import io
from time import monotonic
from types import SimpleNamespace

from google.genai import errors
from PIL import Image
import pytest

from cloud.preview import (FALLBACK, PRIMARY, ImagePreviewService,
                           PreviewGenerationError)


@pytest.fixture(autouse=True)
def clean_image_settings(monkeypatch):
    for name in ("PREFLIGHT_IMAGE_MODEL", "PREFLIGHT_IMAGE_PRIMARY_UNSERVED",
                 "PREFLIGHT_IMAGE_MODEL_FALLBACK"):
        monkeypatch.delenv(name, raising=False)


def image_response(*, finish_reason="STOP", block_reason=None):
    output = io.BytesIO()
    Image.new("RGB", (160, 90), "green").save(output, format="PNG")
    part = SimpleNamespace(inline_data=SimpleNamespace(mime_type="image/png", data=output.getvalue()))
    candidate = SimpleNamespace(finish_reason=finish_reason, content=SimpleNamespace(parts=[part]))
    return SimpleNamespace(candidates=[candidate],
                           prompt_feedback=SimpleNamespace(block_reason=block_reason))


def unavailable(code=503, status="UNAVAILABLE"):
    return errors.ClientError(code, {"error": {"status": status, "message": "private provider detail"}})


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if callable(outcome):
            outcome = outcome()
            if hasattr(outcome, "__await__"):
                outcome = await outcome
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class Timing:
    def __init__(self):
        self.now, self.delays, self.jitter_bounds = 100.0, [], []

    def clock(self):
        return self.now

    async def sleep(self, seconds):
        self.delays.append(seconds)
        self.now += seconds

    def uniform(self, lower, upper):
        self.jitter_bounds.append((lower, upper))
        return upper


def service(outcomes, *, timing=None, **settings):
    models = FakeModels(outcomes)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    if timing is not None:
        settings.update(clock=timing.clock, sleep=timing.sleep, uniform=timing.uniform)
    else:
        settings.setdefault("uniform", lambda lower, upper: 0)
    return ImagePreviewService(client=client, **settings), models


def run(provider, **kwargs):
    return asyncio.run(provider.generate("A spoon beside a laptop on a desk.", **kwargs))


def test_503_retry_returns_jpeg_with_attempt_count():
    timing = Timing()
    provider, models = service([unavailable(), image_response()], timing=timing)
    result = run(provider)
    assert result.jpeg.startswith(b"\xff\xd8")
    assert (result.model, result.size, result.cost_usd) == (PRIMARY, "1K", 0.0336)
    assert result.attempts == result.model_calls == 2
    assert result.fallback_used is False
    assert [call["model"] for call in models.calls] == [PRIMARY, PRIMARY]
    assert timing.delays == [1]
    assert timing.jitter_bounds == [(0, 1)]
    assert [attempt["outcome"] for attempt in result.model_attempts] == ["retryable_error", "success"]
    assert result.model_attempts[0]["code"] == 503
    assert "private" not in str(result.model_attempts)


@pytest.mark.parametrize("error", [unavailable(429, "RESOURCE_EXHAUSTED"),
    errors.ServerError(503, {"error": {"status": "UNAVAILABLE"}}),
    SimpleNamespace])
def test_retry_statuses(error):
    if error is SimpleNamespace:
        error = RuntimeError("safe generic exception")
        error.status = "RESOURCE_EXHAUSTED"
    provider, models = service([error, image_response()])
    assert run(provider).attempts == 2
    assert len(models.calls) == 2


@pytest.mark.parametrize("code,status", [(400, "INVALID_ARGUMENT"), (400, "UNAVAILABLE"),
    (403, "PERMISSION_DENIED"), (500, "INTERNAL"), (503, "SAFETY")])
def test_validation_auth_internal_and_safety_errors_never_retry(code, status):
    provider, models = service([unavailable(code, status), image_response()])
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    assert len(models.calls) == caught.value.attempts == 1
    assert caught.value.fallback_used is False
    assert caught.value.model_attempts[0]["outcome"] == "terminal_error"
    assert "private" not in str(caught.value)


def test_message_text_alone_does_not_trigger_retry():
    provider, models = service([RuntimeError("503 UNAVAILABLE RESOURCE_EXHAUSTED private text")])
    with pytest.raises(PreviewGenerationError):
        run(provider)
    assert len(models.calls) == 1


def test_fallback_after_two_retryable_primary_failures_reports_actual_model():
    timing = Timing()
    provider, models = service([unavailable(), unavailable(), image_response()], timing=timing)
    result = run(provider)
    assert [call["model"] for call in models.calls] == [PRIMARY, PRIMARY, FALLBACK]
    assert [call["config"].image_config.image_size for call in models.calls] == ["1K", "1K", "0.5K"]
    assert (result.model, result.size, result.cost_usd) == (FALLBACK, "0.5K", 0.045)
    assert result.attempts == result.model_calls == 3
    assert result.fallback_used is True
    assert timing.jitter_bounds == [(0, 1), (0, 2)]
    assert timing.delays == [1, 2]
    assert provider.cache_models == [(PRIMARY, "1K"), (FALLBACK, "0.5K")]
    assert len(result.model_attempts) == 3


def test_fallback_failure_stops_after_three_calls_with_safe_metadata():
    provider, models = service([unavailable(), unavailable(), unavailable()])
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    error = caught.value
    assert len(models.calls) == error.attempts == error.model_calls == 3
    assert error.model == FALLBACK and error.fallback_used is True
    assert [attempt["model"] for attempt in error.model_attempts] == [PRIMARY, PRIMARY, FALLBACK]
    assert all(attempt["outcome"] == "retryable_error" for attempt in error.model_attempts)
    assert "private" not in str(error.model_attempts)


def test_terminal_second_attempt_never_reaches_fallback():
    provider, models = service([unavailable(), unavailable(400, "INVALID_ARGUMENT"), image_response()])
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    assert caught.value.attempts == len(models.calls) == 2
    assert caught.value.model == PRIMARY and caught.value.fallback_used is False


@pytest.mark.parametrize("response,reason", [
    (SimpleNamespace(candidates=[], prompt_feedback=None), "no_image"),
    (SimpleNamespace(candidates=[SimpleNamespace(content=None, finish_reason="STOP")]), "no_image"),
    (image_response(finish_reason="SAFETY"), "blocked"),
    (image_response(finish_reason="IMAGE_SAFETY"), "blocked"),
    (image_response(block_reason="PROHIBITED_CONTENT"), "blocked"),
])
def test_no_image_and_safety_response_never_retry_or_fallback(response, reason):
    provider, models = service([response, image_response()])
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    assert len(models.calls) == caught.value.attempts == 1
    assert caught.value.reason == reason
    assert caught.value.model_attempts[0]["outcome"] == "terminal_error"


def test_static_fallback_selection_is_not_duplicated(monkeypatch):
    monkeypatch.setenv("PREFLIGHT_IMAGE_PRIMARY_UNSERVED", "true")
    provider, models = service([unavailable(), unavailable(), image_response()])
    assert provider.cache_models == [(FALLBACK, "0.5K")]
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    assert [call["model"] for call in models.calls] == [FALLBACK, FALLBACK]
    assert caught.value.attempts == 2 and caught.value.fallback_used is True


def test_per_attempt_timeout_cancels_attempt_then_retries():
    cancelled = []
    async def hang():
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)
    provider, models = service([hang, image_response()], attempt_timeout=0.02, overall_timeout=0.5)
    result = run(provider)
    assert cancelled == [True]
    assert result.attempts == len(models.calls) == 2
    assert result.model_attempts[0]["outcome"] == "timeout"


def test_overall_deadline_cancels_before_first_attempt_timeout():
    async def hang():
        await asyncio.sleep(1)
    provider, models = service([hang], attempt_timeout=0.5, overall_timeout=0.025)
    started = monotonic()
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    assert monotonic() - started < 0.25
    assert len(models.calls) == caught.value.attempts == 1
    assert caught.value.reason == "timeout"
    assert caught.value.model_attempts[0]["outcome"] == "timeout"


def test_request_deadline_can_shorten_service_deadline():
    async def hang():
        await asyncio.sleep(1)
    provider, models = service([hang], overall_timeout=1)
    started = monotonic()
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider, deadline=started + 0.025)
    assert monotonic() - started < 0.25
    assert len(models.calls) == caught.value.attempts == 1
    assert models.calls[0]["config"].http_options.timeout <= 25


def test_expired_request_deadline_makes_zero_model_calls():
    provider, models = service([image_response()])
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider, deadline=monotonic() - 1)
    assert not models.calls
    assert caught.value.attempts == 0


def test_backoff_cannot_overrun_overall_deadline():
    timing = Timing()
    def slow_failure():
        timing.now += 40
        return unavailable()
    provider, models = service([slow_failure, unavailable(), image_response()], timing=timing)
    with pytest.raises(PreviewGenerationError) as caught:
        run(provider)
    assert caught.value.reason == "timeout"
    assert len(models.calls) == caught.value.attempts == 2
    assert timing.now <= 142
    assert timing.delays == [1]


def test_fallback_timeout_is_capped_by_remaining_overall_budget():
    timing = Timing()
    def slow_failure():
        timing.now += 13
        return unavailable()
    provider, models = service([slow_failure, slow_failure, image_response()], timing=timing)
    result = run(provider)
    assert result.fallback_used is True
    assert [call["config"].http_options.timeout for call in models.calls] == [13000, 13000, 13000]
    assert all(call["config"].http_options.retry_options.attempts == 1 for call in models.calls)


def test_sdk_client_retries_are_disabled(monkeypatch):
    from google import genai
    captured = {}
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("PREFLIGHT_IMAGE_LOCATION", "global")
    def client(**kwargs):
        captured.update(kwargs)
        return object()
    monkeypatch.setattr(genai, "Client", client)
    provider = ImagePreviewService()
    assert captured["http_options"].retry_options.attempts == 1
    assert captured["http_options"].timeout == 16000
    assert provider.model == PRIMARY and provider.size == "1K"


def test_external_cancellation_propagates_without_retry():
    async def scenario():
        started = asyncio.Event()
        async def hang():
            started.set()
            await asyncio.sleep(1)
        provider, models = service([hang, image_response()])
        task = asyncio.create_task(provider.generate("a desk"))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(models.calls) == 1
    asyncio.run(scenario())
