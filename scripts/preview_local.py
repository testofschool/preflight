"""Start this build locally and record curl timings; this is not Cloud Run QA."""

from datetime import datetime
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
from zoneinfo import ZoneInfo


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    (root / "logs").mkdir(exist_ok=True)
    (root / "reports").mkdir(exist_ok=True)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8080)) == 0:
            raise SystemExit("Port 8080 is in use; no existing process was changed.")
    server_command = [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1",
                      "--port", "8080", "--no-access-log"]
    log_file = (root / "logs/server.log").open("w")
    started = time.monotonic()
    process = subprocess.Popen(server_command, cwd=root, stdout=log_file, stderr=subprocess.STDOUT,
                               start_new_session=True)
    outputs = []

    def invoke(prompt: str, label: str) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            response_path = Path(temporary) / "response.json"
            command = ["curl", "--silent", "--show-error", "--max-time", "60", "--output",
                       str(response_path), "--write-out", "%{http_code} %{time_total}",
                       "--json", json.dumps({"prompt": prompt}), "http://127.0.0.1:8080/preflight"]
            receipt = subprocess.run(command, capture_output=True, text=True, check=True)
            code, duration = receipt.stdout.split()
            payload = json.loads(response_path.read_text())
            if code != "200" or not isinstance(payload.get("p_fail"), (int, float)):
                raise RuntimeError("Local prediction did not return a supported HTTP 200 result")
            row = {"sample": prompt, "label": label, "http_status": int(code),
                   "request_seconds": float(duration), "p_fail": payload["p_fail"],
                   "neighbours": len(payload["nearest_prompts"]),
                   "rewrite_present": "rewritten_prompt" in payload}
            line = f"{label} | {prompt} | HTTP {code} | {duration}s | p_fail={payload['p_fail']:.6f}"
            outputs.append(line)
            print(line, flush=True)
            return row

    try:
        while True:
            if process.poll() is not None:
                raise RuntimeError("Local server exited during startup; inspect server.log")
            try:
                with urlopen("http://127.0.0.1:8080/healthz", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            if time.monotonic() - started > 60:
                raise TimeoutError("Local startup exceeded 60 seconds")
            time.sleep(0.05)
        ready_seconds = time.monotonic() - started
        from app import SAMPLES
        first = invoke(SAMPLES[0], "first local request")
        cold_total_seconds = time.monotonic() - started
        warm = [invoke(prompt, "warm local request") for prompt in SAMPLES]
        with urlopen("http://127.0.0.1:8080/api/status", timeout=1) as response:
            status = json.load(response)
        report = {
            "scope": "LOCAL ONLY; V3 Cloud Run warm/cold remains NOT RUN",
            "created_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "pid": process.pid,
            "server_command": server_command,
            "startup_ready_seconds": ready_seconds,
            "startup_through_first_prediction_seconds": cold_total_seconds,
            "first_prediction": first,
            "warm_samples": warm,
            "all_local_warm_under_10_seconds": all(row["request_seconds"] < 10 for row in warm),
            "status": status,
        }
        (root / "reports/local_latency.json").write_text(json.dumps(report, indent=2) + "\n")
        outputs.append(f"local_startup_through_first_prediction={cold_total_seconds:.6f}s")
        (root / "logs/local_latency.txt").write_text("\n".join(outputs) + "\n")
        print(f"local_server_pid={process.pid}; local_url=http://127.0.0.1:8080", flush=True)
    except BaseException:
        process.terminate()
        process.wait(timeout=10)
        raise
    finally:
        log_file.close()


if __name__ == "__main__":
    main()
