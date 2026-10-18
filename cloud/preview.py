"""Saved sample stills and one bounded, explicitly selected Vertex image call."""

import asyncio
from dataclasses import dataclass
import hashlib
import io
import json
import os

CAPTION = "A still from an image model, not a Veo frame. Motion, flicker and timing cannot be judged from a still."
LIVE_LIMITED_MESSAGE = "Live stills are limited to the sample prompts during judging — shared Gemini image capacity. The risk check still works."
PRICING_SOURCE = "https://cloud.google.com/vertex-ai/generative-ai/pricing"
CHECKED_DATE = "2026-10-18"
PRIMARY = "gemini-3.1-flash-lite-image"
SEPARATE_CAPACITY = "gemini-2.5-flash-image"
FALLBACK = "gemini-3.1-flash-image"
PRICES = {(PRIMARY, "1K"): 0.0336, (SEPARATE_CAPACITY, "1K"): 0.0387,
          (FALLBACK, "0.5K"): 0.04482}
IMAGE_TOKENS = {PRIMARY: 1120, SEPARATE_CAPACITY: 1290, FALLBACK: 747}
# USD per million text input, text output, and image output tokens (global endpoint).
TOKEN_RATES = {PRIMARY: (0.25, 1.50, 30), SEPARATE_CAPACITY: (0.30, 2.50, 30),
               FALLBACK: (0.50, 3.00, 60)}
WIRE_IMAGE_SIZES = {"1K": "1K", "0.5K": "512", "512": "512"}
LIVE_ARMS = {"P1": (PRIMARY, "1K"), "P2": (SEPARATE_CAPACITY, "1K"),
             "P3": (FALLBACK, "0.5K")}
PRIORITY_HEADER = "X-Vertex-AI-LLM-Shared-Request-Type"


def preview_cache_key(prompt, model, size):
    return hashlib.sha256(json.dumps(["preview-v1", prompt, model, size],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def sample_preview_cache_key(prompt):
    """Stable across model selection; saved metadata records the real model and date."""
    return hashlib.sha256(json.dumps(["preview-sample-v1", prompt],
        ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def image_settings():
    arm = os.environ.get("PREFLIGHT_IMAGE_LIVE_ARM")
    if arm:
        if arm not in LIVE_ARMS:
            raise ValueError("Image live arm is unsupported")
        return LIVE_ARMS[arm]
    primary = os.environ.get("PREFLIGHT_IMAGE_MODEL", PRIMARY)
    fallback = os.environ.get("PREFLIGHT_IMAGE_PRIMARY_UNSERVED") == "true"
    model = os.environ.get("PREFLIGHT_IMAGE_MODEL_FALLBACK", FALLBACK) if fallback else primary
    size = "0.5K" if model == FALLBACK else "1K"
    if (model, size) not in PRICES:
        raise ValueError("Image model has no verified pricing")
    return model, size


def image_pricing(model=None, size=None, *, priority=None):
    if model is None:
        model, size = image_settings()
    if (model, size) not in PRICES:
        raise ValueError("Image model has no verified pricing")
    if priority is None:
        priority = os.environ.get("PREFLIGHT_IMAGE_LIVE_ARM") == "P1"
    multiplier = 1.8 if priority and model == PRIMARY else 1
    return {"model": model, "size": size,
            "usd_per_image": round(PRICES[model, size] * multiplier, 8),
            "source": PRICING_SOURCE, "checked_date": CHECKED_DATE,
            "cost_basis": "image-output-list-price", "billing_verified": False,
            "priority_requested": multiplier > 1}


def _enum_name(value):
    return str(getattr(value, "name", value) or "").rsplit(".", 1)[-1].upper()


def _cost(response, model, priority):
    usage = getattr(response, "usage_metadata", None)
    traffic = _enum_name(getattr(usage, "traffic_type", None)) or None
    priority_billed = priority and traffic != "ON_DEMAND"
    multiplier = 1.8 if priority_billed and model == PRIMARY else 1
    text_in, text_out, image_out = TOKEN_RATES[model]
    image_tokens = IMAGE_TOKENS[model]
    text_tokens = 0
    details = getattr(usage, "candidates_tokens_details", None) or []
    if details:
        image_tokens = sum(int(row.token_count or 0) for row in details
                           if _enum_name(row.modality) == "IMAGE")
        text_tokens = sum(int(row.token_count or 0) for row in details
                          if _enum_name(row.modality) == "TEXT")
        if not image_tokens:
            image_tokens = IMAGE_TOKENS[model]
    else:
        text_tokens = max(0, int(getattr(usage, "candidates_token_count", 0) or 0) - image_tokens)
    text_tokens += int(getattr(usage, "thoughts_token_count", 0) or 0)
    prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    cost = multiplier * (prompt_tokens * text_in + text_tokens * text_out + image_tokens * image_out) / 1e6
    return {"cost_usd": round(cost, 8), "traffic_type": traffic,
            "cost_basis": "token-usage-list-price" if usage is not None else "image-output-list-price",
            "billing_verified": False, "priority_traffic_verified": not priority or traffic in (
                "ON_DEMAND", "ON_DEMAND_PRIORITY"),
            "image_output_tokens": image_tokens, "text_output_tokens": text_tokens,
            "text_input_tokens": prompt_tokens}


@dataclass(frozen=True)
class PreviewResult:
    jpeg: bytes
    model: str
    size: str
    cost_usd: float
    traffic_type: str | None = None
    cost_basis: str = "image-output-list-price"
    billing_verified: bool = False
    priority_traffic_verified: bool = True
    image_output_tokens: int = 0
    text_output_tokens: int = 0
    text_input_tokens: int = 0
    model_calls: int = 1


class ImagePreviewService:
    def __init__(self, *, client=None):
        from google.genai import types
        self.model, self.size = image_settings()
        self.priority = os.environ.get("PREFLIGHT_IMAGE_LIVE_ARM") == "P1"
        if client is None:
            from google import genai
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = (os.environ.get("PREFLIGHT_IMAGE_LOCATION") or
                        os.environ.get("PREFLIGHT_GEMINI_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION"))
            if not project or not location:
                raise ValueError("Vertex image location is unavailable")
            client = genai.Client(vertexai=True, project=project, location=location,
                http_options=types.HttpOptions(timeout=30000,
                    headers={PRIORITY_HEADER: "priority"} if self.priority else None,
                    retry_options=types.HttpRetryOptions(attempts=1)))
        self.client = client

    async def generate(self, prompt):
        from google.genai import types
        from PIL import Image
        image_config = {"aspect_ratio": "16:9"}
        if self.model != SEPARATE_CAPACITY:
            image_config["image_size"] = WIRE_IMAGE_SIZES[self.size]
        # One provider attempt, with SDK retries disabled; no quick retry on shared capacity.
        async with asyncio.timeout(30):
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=prompt,
                config=types.GenerateContentConfig(response_modalities=["IMAGE"], candidate_count=1,
                    http_options=types.HttpOptions(timeout=30000,
                        headers={PRIORITY_HEADER: "priority"} if self.priority else None,
                        retry_options=types.HttpRetryOptions(attempts=1)),
                    image_config=types.ImageConfig(**image_config)))
        for candidate in response.candidates or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                data = getattr(part, "inline_data", None)
                if data and data.mime_type and data.mime_type.startswith("image/") and data.data:
                    with Image.open(io.BytesIO(data.data)) as source:
                        output = io.BytesIO()
                        source.convert("RGB").save(output, format="JPEG", quality=82)
                        pricing = _cost(response, self.model, self.priority)
                        if self.priority and not pricing["priority_traffic_verified"]:
                            raise ValueError("Priority image traffic price could not be verified")
                        return PreviewResult(output.getvalue(), self.model, self.size,
                                             **pricing)
        raise ValueError("Image response contained no image")
