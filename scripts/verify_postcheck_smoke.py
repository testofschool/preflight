#!/usr/bin/env python3
"""One fresh upload on the current image; operational evidence, not V8."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import ssl
import sys
from urllib.parse import urlsplit

import certifi
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_postcheck_canary import load_frozen_source, request_once, initial_checks
from scripts.verify_rewrites import save_report, append_log


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        parser.error("Use an HTTPS base URL without credentials or a path")
    if args.report.exists() or args.log.exists():
        parser.error("Receipt already exists; the completed request must not be repeated")
    reference, digest, source = load_frozen_source(args.reference)
    report = {
        "check": "one fresh current-image operational upload; not V8",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": args.url.rstrip("/") + "/postcheck",
        "reference_sha256": digest,
        "source_sha256": reference["sha256"],
        "reference_frozen_at_utc": reference["frozen_at_utc"],
        "source_bytes": len(source),
        "revision": reference["validation_revision"],
        "request_policy": "exactly one upload; no retry, cache replay or preflight call",
        "V8_established": False,
        "complete": False,
    }
    save_report(args.report, report)
    with httpx.Client(verify=ssl.create_default_context(cafile=certifi.where()), timeout=httpx.Timeout(90), follow_redirects=False) as client:
        attempt = request_once(client, report["endpoint"], reference=reference, source=source)
    checks = initial_checks(reference, attempt)
    report.update(attempt=attempt, checks=checks, complete=True, finished_at_utc=datetime.now(timezone.utc).isoformat())
    save_report(args.report, report)
    append_log(args.log, f"one_upload HTTP={attempt.get('http_status')} seconds={attempt['elapsed_seconds']:.6f} verified={checks['passed']} model_calls={checks['model_calls_this_request']} V8_established=false")
    print(args.log.read_text(), end="")
    return 0 if checks["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
