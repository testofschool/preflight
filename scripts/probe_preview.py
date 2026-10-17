"""G3: use the deployed Vertex project/location without printing identifiers."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
from time import monotonic

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]


async def main():
    result = subprocess.run(["gcloud", "run", "services", "describe", "preflight", "--region",
                             "asia-southeast1", "--format=json"], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("Service configuration verification failed; no image calls made")
    service = json.loads(result.stdout)
    if service["status"]["latestReadyRevisionName"] != "preflight-00009-n9b":
        print("Baseline revision differs; inspect the deployment receipt before continuing")
    settings = {entry["name"]: entry.get("value") for entry in
                service["spec"]["template"]["spec"]["containers"][0]["env"]}
    project = settings["GOOGLE_CLOUD_PROJECT"]
    location = settings.get("PREFLIGHT_GEMINI_LOCATION") or settings["GOOGLE_CLOUD_LOCATION"]
    attempts = []
    plan = [("gemini-3.1-flash-lite-image", location, "1K"),
            ("gemini-3.1-flash-lite-image", "global", "1K"),
            ("gemini-3.1-flash-image", "global", "0.5K")]
    for model, region, size in plan:
        start = monotonic()
        status, error, has_image = None, None, False
        try:
            client = genai.Client(vertexai=True, project=project, location=region,
                http_options=types.HttpOptions(timeout=30000, retry_options=types.HttpRetryOptions(attempts=1)))
            async with client.aio as api:
                response = await api.models.generate_content(model=model,
                    contents="A spoon beside a laptop on a desk, one still photograph.",
                    config=types.GenerateContentConfig(response_modalities=["IMAGE"], candidate_count=1,
                        image_config=types.ImageConfig(aspect_ratio="16:9", image_size=size)))
                has_image = any(part.inline_data and part.inline_data.data for candidate in response.candidates or []
                                for part in candidate.content.parts or [])
            status = 200
            if not has_image:
                error = "NoImageBytes"
        except Exception as exc:
            error = type(exc).__name__
            status = getattr(exc, "code", None)
            if not isinstance(status, int):
                status = None
        attempts.append({"model": model, "location": region, "size": size, "http_status": status,
                         "latency_ms": round((monotonic() - start) * 1000), "error_class": error,
                         "image_bytes_returned": bool(has_image)})
        (ROOT / "reports/preview_probe.json").write_text(json.dumps(attempts, indent=2) + "\n")
        print(json.dumps(attempts[-1]), flush=True)
        if has_image:
            break
        # Do not spend another primary call on quota/auth/billing errors.
        if status in (401, 403, 429):
            break


if __name__ == "__main__":
    asyncio.run(main())
