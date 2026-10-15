#!/usr/bin/env python3
"""One real negative-control review, one cache check, one updated-risk check."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.parse import urlsplit

import certifi
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.verify_rewrites import append_log, forbidden_markers, save_report


ROOT = Path(__file__).resolve().parents[1]
SAFE_HEADERS = ("content-security-policy", "x-content-type-options", "referrer-policy", "content-type")


def finite_number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def nonnegative_integer(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def load_frozen_source(reference_path: Path, expected_reference_sha256: str | None = None) -> tuple[dict, str, bytes]:
    reference_bytes = reference_path.read_bytes()
    reference_hash = hashlib.sha256(reference_bytes).hexdigest()
    if expected_reference_sha256 is not None and reference_hash != expected_reference_sha256:
        raise ValueError("The reference hash differs from the explicitly expected artifact")
    reference = json.loads(reference_bytes)
    if reference.get("schema_version") != 1 or not reference.get("frozen_at_utc") or reference.get("expected_confirmed_defects") != []:
        raise ValueError("A frozen negative-control reference is required")
    if "not the V8" not in reference.get("purpose", ""):
        raise ValueError("This canary must be explicitly separated from V8")
    if not isinstance(reference.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]):
        raise ValueError("The frozen source hash is missing")
    if not isinstance(reference.get("prompt"), str) or not 1 <= len(reference["prompt"].strip()) <= 4000:
        raise ValueError("A frozen neutral scene prompt is required")
    if not isinstance(reference.get("model"), str) or not 1 <= len(reference["model"].strip()) <= 200:
        raise ValueError("A frozen model provenance label is required")
    source_path = Path(reference["cached_absolute_path"])
    if not source_path.is_absolute() or source_path.is_symlink() or not source_path.is_file():
        raise ValueError("The frozen cached source must be an existing regular local file")
    size = source_path.stat().st_size
    if not 0 < size <= 30 * 1024 * 1024 or size != reference.get("source_bytes"):
        raise ValueError("The frozen source size differs or exceeds the upload bound")
    source = source_path.read_bytes()
    if hashlib.sha256(source).hexdigest() != reference["sha256"]:
        raise ValueError("The frozen source hash changed; no network requests were started")
    if hashlib.sha256(reference_path.read_bytes()).hexdigest() != reference_hash:
        raise ValueError("The reference changed during source validation")
    return reference, reference_hash, source


def request_once(client, endpoint: str, *, reference: dict, source: bytes | None = None) -> dict:
    started = time.perf_counter()
    receipt = {"attempt": 1, "retry_count": 0}
    try:
        if source is None:
            response = client.post(endpoint, json={"prompt": reference["prompt"]})
        else:
            response = client.post(
                endpoint,
                # Independent labels, expected defects and evidence are omitted.
                data={"prompt": reference["prompt"], "model": reference["model"]},
                files={"video": ("canary.mp4", source, "video/mp4")},
            )
        receipt["http_status"] = response.status_code
        receipt["safe_response_headers"] = {name: response.headers[name] for name in SAFE_HEADERS if name in response.headers}
        payload = response.content
        receipt["response_bytes_received"] = len(payload)
        markers = forbidden_markers(payload)
        if markers:
            receipt["response_omitted"] = "credential markers detected"
            receipt["credential_marker_names"] = markers
        elif len(payload) > 2_000_000:
            receipt["response_omitted"] = "response exceeded safety size limit"
        else:
            try:
                receipt["response"] = json.loads(payload)
            except (ValueError, UnicodeError):
                receipt["response_omitted"] = "response was not valid JSON"
    except (httpx.HTTPError, OSError) as problem:
        receipt["http_status"] = None
        receipt["error_type"] = type(problem).__name__
    receipt["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    return receipt


def successful_json(receipt: dict) -> dict | None:
    response = receipt.get("response")
    return response if receipt.get("http_status") == 200 and isinstance(response, dict) else None


def initial_checks(reference: dict, receipt: dict) -> dict:
    result = successful_json(receipt)
    if result is None:
        return {"passed": False, "model_calls_this_request": None}
    analysis = result.get("analysis", {})
    calls = result.get("model_calls_this_request")
    feedback = result.get("feedback", {})
    if not isinstance(analysis, dict) or not isinstance(feedback, dict):
        return {"passed": False, "model_calls_this_request": calls if nonnegative_integer(calls) else None}
    checks = {
        "source_hash_matches": result.get("source_sha256") == reference["sha256"],
        "actual_model_calls_verified": nonnegative_integer(calls) and calls >= 2,
        "sampling_2fps": analysis.get("sampling_fps") == 2,
        "vertex_backend": analysis.get("backend") == "vertex",
        "feedback_recorded": result.get("feedback_recorded") is True,
        "feedback_created": result.get("feedback_created") is True,
        "fresh_review": result.get("reused_stored_review") is False,
        "feedback_count_present": nonnegative_integer(feedback.get("count")) and feedback["count"] >= 1,
        "valid_risk_after": finite_number(result.get("risk_after")) and 0 <= result["risk_after"] <= 1,
        "typed_verdict": isinstance(result.get("pass_bool"), bool) and isinstance(result.get("defects"), list),
    }
    return {**checks, "passed": all(checks.values()), "model_calls_this_request": calls if nonnegative_integer(calls) else None}


def cache_checks(first_receipt: dict, cached_receipt: dict) -> dict:
    first, cached = successful_json(first_receipt), successful_json(cached_receipt)
    if first is None or cached is None:
        return {"passed": False, "model_calls_this_request": None}
    calls = cached.get("model_calls_this_request")
    first_feedback, next_feedback = first.get("feedback", {}), cached.get("feedback", {})
    if not isinstance(first_feedback, dict) or not isinstance(next_feedback, dict):
        return {"passed": False, "model_calls_this_request": calls if nonnegative_integer(calls) else None}
    checks = {
        "same_verdict": bool(first.get("verdict_id")) and first.get("verdict_id") == cached.get("verdict_id"),
        "cache_reused": cached.get("reused_stored_review") is True,
        "no_new_feedback": cached.get("feedback_created") is False,
        "zero_new_model_calls": nonnegative_integer(calls) and calls == 0,
        "feedback_count_unchanged": nonnegative_integer(first_feedback.get("count")) and first_feedback.get("count") == next_feedback.get("count"),
        "feedback_failures_unchanged": nonnegative_integer(first_feedback.get("failures")) and first_feedback.get("failures") == next_feedback.get("failures"),
        "identical_stored_review": all(first.get(key) == cached.get(key) for key in ("pass_bool", "defects", "reviewed_duration_seconds", "analysis", "source_sha256")),
    }
    return {**checks, "passed": all(checks.values()), "model_calls_this_request": calls if nonnegative_integer(calls) else None}


def preflight_checks(first_receipt: dict, preflight_receipt: dict) -> dict:
    first, result = successful_json(first_receipt), successful_json(preflight_receipt)
    if first is None or result is None:
        return {"passed": False, "model_calls_this_request": None}
    risk, expected = result.get("p_fail"), first.get("risk_after")
    trace = result.get("tool_trace", [])
    completed = sum(isinstance(item, dict) and item.get("completed") is True for item in trace) if isinstance(trace, list) else 0
    tool_calls = result.get("tool_call_count")
    agent = result.get("agent_trace", {})
    if not isinstance(agent, dict):
        agent = {}
    planner, rewrite = agent.get("planner_model_calls"), agent.get("rewrite_model_calls")
    model_calls = planner + rewrite if nonnegative_integer(planner) and nonnegative_integer(rewrite) else None
    checks = {
        "updated_risk_used": finite_number(risk) and finite_number(expected) and abs(risk - expected) <= 1e-12,
        "actual_tools_verified": nonnegative_integer(tool_calls) and tool_calls >= 3 and completed >= 3,
        "managed_session_verified": result.get("session_verified") is True and result.get("session_service") == "Agent Platform Sessions",
        "actual_model_calls_verified": model_calls is not None and model_calls >= 1,
    }
    return {**checks, "passed": all(checks.values()), "model_calls_this_request": model_calls, "completed_tool_calls": completed}


def summary(rows: list[dict]) -> dict:
    calls = [row["checks"].get("model_calls_this_request") for row in rows]
    return {
        "http_requests": len(rows),
        "maximum_http_requests": 3,
        "retries": 0,
        "canary_pass": len(rows) == 3 and all(row["checks"].get("passed") for row in rows),
        "known_model_calls_this_batch": sum(value for value in calls if nonnegative_integer(value)),
        "unknown_model_call_requests": sum(value is None for value in calls),
        "V8_established": False,
        "scope": "negative-control operational canary; no exhaustive clean-video certification or known-defect recall claim",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--reference", type=Path, default=ROOT / "reports" / "postcheck_canary_reference.json")
    parser.add_argument("--expected-reference-sha256")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "postcheck_canary_live.json")
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "postcheck_canary_live.txt")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        parser.error("Use an HTTPS service base URL without credentials, path, query or fragment")
    if args.report.exists() or args.log.exists():
        parser.error("Canary receipts already exist; preserve them and choose explicit new filenames for a separately authorized batch")
    reference, reference_hash, source = load_frozen_source(args.reference, args.expected_reference_sha256)
    base_url = args.url.rstrip("/")
    report = {
        "check": "negative-control postcheck/cache/feedback canary; not V8",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "service_url": base_url,
        "reference_sha256": reference_hash,
        "reference_readback_matches": True,
        "reference_frozen_at_utc": reference["frozen_at_utc"],
        "source_sha256": reference["sha256"],
        "source_bytes": len(source),
        "clip_id": reference["id"],
        "neutral_prompt_sent": reference["prompt"],
        "model_label_sent": reference["model"],
        "reference_scope": reference["reference_scope"],
        "request_policy": "one actual review, one identical cache check, one updated-risk preflight; stop on failure; no retries; maximum3 requests",
        "rows": [],
        "complete": False,
    }
    save_report(args.report, report)
    append_log(args.log, {key: report[key] for key in ("check", "reference_sha256", "source_sha256", "request_policy")})
    try:
        with httpx.Client(verify=ssl.create_default_context(cafile=certifi.where()), timeout=httpx.Timeout(90.0), follow_redirects=False) as client:
            stages = ("initial_postcheck", "identical_cached_postcheck", "updated_risk_preflight")
            for index, stage in enumerate(stages):
                endpoint = base_url + ("/preflight" if index == 2 else "/postcheck")
                receipt = request_once(client, endpoint, reference=reference, source=None if index == 2 else source)
                if index == 0:
                    checks = initial_checks(reference, receipt)
                elif index == 1:
                    checks = cache_checks(report["rows"][0]["attempt"], receipt)
                else:
                    checks = preflight_checks(report["rows"][0]["attempt"], receipt)
                row = {"stage": stage, "attempt": receipt, "checks": checks}
                report["rows"].append(row)
                report["summary"] = summary(report["rows"])
                save_report(args.report, report)
                append_log(args.log, row)
                print(json.dumps({"stage": stage, "http_status": receipt.get("http_status"), "elapsed_seconds": receipt["elapsed_seconds"], **checks}, allow_nan=False), flush=True)
                if not checks["passed"]:
                    report["stopped_after"] = stage
                    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                    save_report(args.report, report)
                    return 1
    except KeyboardInterrupt:
        report["interrupted"] = True
        report["summary"] = summary(report["rows"])
        save_report(args.report, report)
        return 130
    report["complete"] = True
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = summary(report["rows"])
    save_report(args.report, report)
    append_log(args.log, {"summary": report["summary"]})
    print(json.dumps(report["summary"], allow_nan=False), flush=True)
    return int(not report["summary"]["canary_pass"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as problem:
        print(json.dumps({"verification_error_type": type(problem).__name__, "complete": False}), file=sys.stderr)
        raise SystemExit(2)
