"""Build and deploy the verified app with runtime-only cloud configuration."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from cloud_ops import CloudOperations, REGION, DATABASE, RUNTIME_ACCOUNT, BUILD_ACCOUNT


ROOT = Path(__file__).resolve().parents[1]


def build_digest() -> str:
    paths = [ROOT / name for name in ("Dockerfile", "requirements-cloud.lock", "app.py")]
    for folder in ("cloud", "preflight_core", "static"):
        paths.extend(path for path in (ROOT / folder).rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    paths.extend(ROOT / "artifacts" / name for name in ("engine.json", "vectorizer.joblib", "prompt_vectors.npz"))
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(ROOT)).encode() + b"\x00" + path.read_bytes())
    return digest.hexdigest()


def build(operations: CloudOperations) -> str:
    digest = build_digest()
    image = f"{REGION}-docker.pkg.dev/{operations.project}/preflight/app:{digest[:20]}"
    receipt_path = ROOT / "reports/cloud_build.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text())
        if previous.get("input_sha256") == digest:
            data = json.loads(operations.command("inspect prior build", ["gcloud", "builds", "describe", previous["build_id"],
                                                                         "--region", REGION, "--format=json"]))
        else:
            data = None
    else:
        data = None
    if data is None:
        data = json.loads(operations.command("submit container build", [
            "gcloud", "builds", "submit", str(ROOT), "--config", str(ROOT / "cloudbuild.yaml"),
            "--substitutions", "_IMAGE=" + image, "--region", REGION,
            "--service-account", f"projects/{operations.project}/serviceAccounts/{BUILD_ACCOUNT}@{operations.project}.iam.gserviceaccount.com",
            "--async", "--format=json", "--quiet",
        ]))
    last_status = None
    while True:
        receipt = {"build_id": data["id"], "input_sha256": digest, "region": REGION, "status": data["status"]}
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        if data["status"] != last_status:
            print("container_build_status=" + data["status"], flush=True)
            last_status = data["status"]
        if data["status"] == "SUCCESS":
            return image
        if data["status"] in ("FAILURE", "CANCELLED", "TIMEOUT", "EXPIRED", "INTERNAL_ERROR"):
            raise RuntimeError("Container build failed; inspect its native build ID")
        time.sleep(10)
        data = json.loads(operations.command("inspect container build", ["gcloud", "builds", "describe", data["id"],
                                                                         "--region", REGION, "--format=json"]))


def deploy(operations: CloudOperations, image: str, timeout: int) -> None:
    settings = {
        "PREFLIGHT_MODE": "cloud",
        "GOOGLE_CLOUD_PROJECT": operations.project,
        "GOOGLE_CLOUD_LOCATION": REGION,
        "PREFLIGHT_FIRESTORE_DATABASE": DATABASE,
        "PREFLIGHT_SESSION_ENGINE_ID": operations.session_engine(),
        "PREFLIGHT_GEMINI_BACKEND": "vertex",
        "PREFLIGHT_GEMINI_LOCATION": REGION,
        "PREFLIGHT_GEMINI_MODEL": os.environ.get("PREFLIGHT_GEMINI_MODEL", "gemini-3.5-flash"),
        "PREFLIGHT_TOTAL_REQUEST_LIMIT": "1000",
    }
    operations.command("deploy Cloud Run", [
        "gcloud", "run", "deploy", "preflight", "--image", image, "--region", REGION,
        "--service-account", f"{RUNTIME_ACCOUNT}@{operations.project}.iam.gserviceaccount.com",
        "--set-env-vars", ",".join(f"{name}={value}" for name, value in settings.items()),
        "--min-instances=0", "--max-instances=2", "--cpu=1", "--memory=1Gi",
        "--timeout", str(timeout), "--allow-unauthenticated", "--quiet", "--format=json",
    ])
    data = json.loads(operations.command("read Cloud Run configuration", ["gcloud", "run", "services", "describe", "preflight",
                                                                         "--region", REGION, "--format=json"]))
    spec = data["spec"]["template"]["spec"]
    annotations = data["spec"]["template"].get("metadata", {}).get("annotations", {})
    receipt = {
        "url": data["status"]["url"], "default_cloud_run_url": data["status"]["url"].endswith(".run.app"),
        "region": REGION, "min_instances": int(annotations.get("autoscaling.knative.dev/minScale", "0")),
        "timeout_seconds": spec["timeoutSeconds"], "concurrency": spec["containerConcurrency"],
        "revision": data["status"]["latestReadyRevisionName"],
        "session_service": "Agent Platform Sessions", "gemini_backend": "Vertex AI",
        "gemini_model": settings["PREFLIGHT_GEMINI_MODEL"], "veo_calls": 0,
    }
    (ROOT / "reports/cloud_run.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=60)
    arguments = parser.parse_args()
    try:
        operations = CloudOperations()
        deploy(operations, build(operations), arguments.timeout)
    except Exception as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
