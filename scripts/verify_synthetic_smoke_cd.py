"""User-authorized path B: operational smoke, synthetic clip, not the frozen reference."""
import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--clip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--prompt")
    parser.add_argument("--model", default="synthetic ffmpeg testsrc operational smoke")
    args = parser.parse_args()
    source = args.clip.read_bytes()
    assert 0 < len(source) <= 30 * 1024 * 1024
    # Reuse a previously recorded prompt identity so this smoke does not add
    # a new prompt document. This test makes no scene/accuracy claim.
    prompt = args.prompt or json.loads((ROOT / "reports/postcheck_smoke_reference.json").read_text())["prompt"]
    start = monotonic()
    response = httpx.post(args.url + "/postcheck", timeout=60,
        data={"prompt": prompt, "model": args.model},
        files={"video": ("smoke.mp4", source, "video/mp4")})
    elapsed = round(monotonic() - start, 3)
    data = response.json() if "application/json" in response.headers.get("content-type", "") else {}
    schema = (isinstance(data.get("pass_bool"), bool) and isinstance(data.get("defects"), list)
              and isinstance(data.get("analysis"), dict)
              and all(isinstance(row.get("summary"), str) and row["summary"]
                      for row in data.get("analysis", {}).get("call_receipts", [])))
    passed = (response.status_code == 200 and schema and data.get("feedback_recorded") is True
              and data.get("source_sha256") == hashlib.sha256(source).hexdigest())
    receipt = {"label": "operational smoke, synthetic clip, not the frozen reference",
               "frozen_smoke": "NOT RUN — reference clip not on this machine",
               "http_status": response.status_code, "latency_seconds": elapsed,
               "error_class": response.headers.get("x-preflight-error"),
               "upstream_status": response.headers.get("x-preflight-upstream-status"),
               "source_bytes": len(source), "source_sha256": hashlib.sha256(source).hexdigest(),
               "expected_duration_seconds": 5, "inspection_api_schema_valid": bool(schema),
               "response": data, "passed": passed, "V8_accuracy_established": False}
    args.report.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ["label", "http_status", "latency_seconds", "passed"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
