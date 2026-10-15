"""Calibrate timeout and measure genuine Cloud Run cold/warm requests with curl."""

import argparse
from datetime import datetime
from http.cookies import SimpleCookie
import json
import math
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4
from zoneinfo import ZoneInfo

from cloud_ops import CloudOperations, REGION


ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ["a cat and a dog", "a spoon and a laptop", "a bicycle and a car", "indoor gymnasium", "a purple clock"]


def cold_revision(operations: CloudOperations, *, timeout: int | None = None) -> str:
    arguments = ["gcloud", "run", "services", "update", "preflight", "--region", REGION,
                 "--update-env-vars", "PREFLIGHT_COLD_CHECK=" + uuid4().hex,
                 "--no-deploy-health-check", "--quiet", "--format=json"]
    if timeout is not None:
        arguments.extend(["--timeout", str(timeout)])
    data = json.loads(operations.command("prepare a cold revision", arguments))
    return data["status"]["latestReadyRevisionName"]


def curl_sample(url: str, prompt: str, phase: str, cookie: str | None, session_id: str | None) -> tuple[dict, str | None, str | None]:
    body = {"prompt": prompt}
    if session_id:
        body["session_id"] = session_id
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "response.json"
        headers = Path(directory) / "headers.txt"
        arguments = ["curl", "--silent", "--show-error", "--max-time", "60", "--output", str(output),
                     "--dump-header", str(headers), "--write-out", "%{http_code} %{time_total}",
                     "--json", json.dumps(body), url.rstrip("/") + "/preflight"]
        if cookie:
            arguments.extend(["--cookie", cookie])
        result = subprocess.run(arguments, capture_output=True, text=True)
        status, elapsed = result.stdout.split() if len(result.stdout.split()) == 2 else ("000", "60")
        payload = json.loads(output.read_text()) if output.exists() else {}
        # Fixed public test prompts are used. Never store transport headers/cookies.
        encoded = json.dumps(payload)
        if "AI" + "za" in encoded or "-" * 5 + "BEGIN" in encoded:
            raise RuntimeError("STOP: forbidden credential marker in API response")
        cookies = SimpleCookie()
        for line in headers.read_text().splitlines() if headers.exists() else []:
            if line.lower().startswith("set-cookie:"):
                cookies.load(line.split(":", 1)[1].strip())
        if "pf_user" in cookies:
            cookie = "pf_user=" + cookies["pf_user"].value
        row = {"phase": phase, "prompt": prompt, "http_status": int(status), "seconds": float(elapsed),
               "curl_exit_code": result.returncode, "response": payload}
        row["valid_connected_response"] = bool(status == "200" and payload.get("mode") == "cloud"
                                                and payload.get("session_verified") and payload.get("tool_call_count", 0) >= 3)
        print(f"{phase} | {prompt} | HTTP {status} | {elapsed}s | tools={payload.get('tool_call_count', 0)}", flush=True)
        return row, cookie, payload.get("session_id") or session_id


def batch(url: str, label: str) -> list[dict]:
    rows = []
    cookie = session_id = None
    for phase, prompt in [("cold", SAMPLES[0])] + [("warm", sample) for sample in SAMPLES]:
        row, cookie, session_id = curl_sample(url, prompt, label + "_" + phase, cookie, session_id)
        rows.append(row)
        if not row["valid_connected_response"]:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--validation-only", action="store_true", help="retain the already measured timeout and test one new cold revision")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/cloud_latency.json")
    parser.add_argument("--log", type=Path, default=ROOT / "logs/cloud_latency.txt")
    arguments = parser.parse_args()
    operations = CloudOperations()
    report = {"created_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
              "url": arguments.url, "method": "new revision, min instances zero, deploy health check disabled; first invocation triggers startup"}
    try:
        if arguments.validation_only:
            current = json.loads(operations.command("read existing measured timeout", ["gcloud", "run", "services", "describe", "preflight",
                                                                                       "--region", REGION, "--format=json"]))
            report["timeout_seconds"] = current["spec"]["template"]["spec"]["timeoutSeconds"]
            report["calibration_note"] = "Retains the timeout derived from recorded sample requests; see postcheck_timeout_calibration.json"
        else:
            report["calibration_revision"] = cold_revision(operations)
            report["calibration"] = batch(arguments.url, "calibration")
            if len(report["calibration"]) != 6 or not all(row["valid_connected_response"] for row in report["calibration"]):
                raise RuntimeError("Calibration did not return six connected responses")
            report["timeout_seconds"] = math.ceil(2 * max(row["seconds"] for row in report["calibration"]))
        report["validation_revision"] = cold_revision(operations, timeout=report["timeout_seconds"])
        report["validation"] = batch(arguments.url, "validation")
        rows = report["validation"]
        report["V3_pass"] = bool(len(rows) == 6 and all(row["valid_connected_response"] for row in rows)
                                 and rows[0]["seconds"] < 60 and all(row["seconds"] < 10 for row in rows[1:]))
        data = json.loads(operations.command("read measured service configuration", ["gcloud", "run", "services", "describe", "preflight",
                                                                                      "--region", REGION, "--format=json"]))
        spec = data["spec"]["template"]["spec"]
        annotations = data["spec"]["template"].get("metadata", {}).get("annotations", {})
        report["V10_config"] = {"region": data["metadata"].get("labels", {}).get("cloud.googleapis.com/location", REGION),
                                "min_instances": int(annotations.get("autoscaling.knative.dev/minScale", "0")),
                                "timeout_seconds": spec["timeoutSeconds"], "concurrency": spec["containerConcurrency"],
                                "revision": data["status"]["latestReadyRevisionName"]}
        print(json.dumps({"V3_pass": report["V3_pass"], "V10": report["V10_config"]}), flush=True)
    finally:
        arguments.report.write_text(json.dumps(report, indent=2) + "\n")
        lines = [f"{row['phase']} | {row['prompt']} | HTTP {row['http_status']} | {row['seconds']:.6f}s"
                 for key in ("calibration", "validation") for row in report.get(key, [])]
        arguments.log.write_text("\n".join(lines) + "\n")
    if not report.get("V3_pass"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
