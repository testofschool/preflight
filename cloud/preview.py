"""One bounded Vertex image call; no video generation and no runtime fallback."""

import io
import os

CAPTION = "A still from an image model, not a Veo frame. Motion, flicker and timing cannot be judged from a still."
PRICING_SOURCE = "https://cloud.google.com/vertex-ai/generative-ai/pricing"
CHECKED_DATE = "2026-10-17"
PRIMARY = "gemini-3.1-flash-lite-image"
FALLBACK = "gemini-3.1-flash-image"


def image_settings():
    primary = os.environ.get("PREFLIGHT_IMAGE_MODEL", PRIMARY)
    # Only a successful G3 receipt may enable the fallback selection.
    fallback = os.environ.get("PREFLIGHT_IMAGE_PRIMARY_UNSERVED") == "true"
    model = os.environ.get("PREFLIGHT_IMAGE_MODEL_FALLBACK", FALLBACK) if fallback else primary
    size = "0.5K" if model == FALLBACK else "1K"
    if model not in (PRIMARY, FALLBACK):
        raise ValueError("Image model has no verified pricing")
    return model, size


def image_pricing():
    model, size = image_settings()
    # Vertex lists $30/M image tokens × 1120 = $0.0336 (rounded $0.034).
    # The fallback's 747 tokens × $60/M = $0.04482 (listed $0.045).
    return {"model": model, "size": size,
            "usd_per_image": 0.045 if size == "0.5K" else 0.0336,
            "source": PRICING_SOURCE, "checked_date": CHECKED_DATE}


class ImagePreviewService:
    def __init__(self):
        from google import genai
        from google.genai import types
        self.model, self.size = image_settings()
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = (os.environ.get("PREFLIGHT_IMAGE_LOCATION") or
                    os.environ.get("PREFLIGHT_GEMINI_LOCATION") or os.environ.get("GOOGLE_CLOUD_LOCATION"))
        if not project or not location:
            raise ValueError("Vertex image location is unavailable")
        self.client = genai.Client(vertexai=True, project=project, location=location,
                                   http_options=types.HttpOptions(timeout=30000,
                                       retry_options=types.HttpRetryOptions(attempts=1)))

    async def generate(self, prompt):
        from google.genai import types
        from PIL import Image
        response = await self.client.aio.models.generate_content(
            model=self.model, contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE"], candidate_count=1,
                image_config=types.ImageConfig(aspect_ratio="16:9", image_size=self.size)))
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                data = part.inline_data
                if data and data.mime_type and data.mime_type.startswith("image/") and data.data:
                    with Image.open(io.BytesIO(data.data)) as source:
                        output = io.BytesIO()
                        source.convert("RGB").save(output, format="JPEG", quality=82)
                        return output.getvalue()
        raise ValueError("Image response contained no image")
