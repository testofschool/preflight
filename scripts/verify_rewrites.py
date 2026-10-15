#!/usr/bin/env python3
"""Measure ten preselected hard prompts against the real deployed endpoint."""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import json
import math
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]


def forbidden_markers(payload: bytes) -> list[str]:
    key_name = b"_".join((b"GEMINI", b"API", b"KEY"))
    patterns = {
        "provider-key-prefix": re.compile(b"AI" + b"za"),
        "private-key-marker": re.compile(b"-" * 5 + b"BEGIN"),
        "provider-key-assignment": re.compile(rb"[\"']?" + key_name + rb"[\"']?\s*[:=]"),
    }
    return [label for label, expression in patterns.items() if expression.search(payload)]


def encoded_safe(document: dict) -> bytes:
    payload = (json.dumps(document, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if forbidden_markers(payload):
        raise ValueError("Credential markers were detected; the artifact was not written")
    return payload


def save_report(path: Path, report: dict) -> None:
    payload = encoded_safe(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def append_log(path: Path, document: dict) -> None:
    payload = encoded_safe(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as output:
        output.write(payload)


def retry_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            timestamp = parsedate_to_datetime(value)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            seconds = timestamp.timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            return None
    # A normal rolling-minute limit returns at most sixty seconds. An unusual
    # longer pause is recorded for human review instead of extending this run.
    return max(1, math.ceil(seconds)) if math.isfinite(seconds) and 0 <= seconds <= 120 else None


def perform_request(opener, endpoint: str, prompt: str, attempt_number: int) -> tuple[dict, int | None]:
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    request = Request(endpoint, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, method="POST")
    started = time.perf_counter()
    wait = None
    raw = b""
    row = {"attempt": attempt_number}
    try:
        with opener.open(request, timeout=90) as response:
            row["http_status"] = int(response.status)
            raw = response.read(2_000_001)
    except HTTPError as error:
        row["http_status"] = int(error.code)
        if error.code == 429:
            wait = retry_seconds(error.headers.get("Retry-After"))
        raw = error.read(2_000_001)
    except (URLError, TimeoutError, OSError) as error:
        row["http_status"] = None
        row["error_type"] = type(error).__name__
        row["response_unavailable"] = True
    row["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    row["response_bytes_received"] = len(raw)
    if len(raw) > 2_000_000:
        row["response_omitted"] = "response exceeded safety size limit"
    elif raw:
        markers = forbidden_markers(raw)
        if markers:
            row["response_omitted"] = "credential markers detected"
            row["credential_marker_names"] = markers
        else:
            try:
                row["response"] = json.loads(raw)
            except (ValueError, UnicodeError):
                row["response_omitted"] = "response was not valid JSON"
    return row, wait


def finite_risk(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1


def assess(prompt: str, attempt: dict) -> dict:
    response = attempt.get("response")
    if attempt.get("http_status") != 200 or not isinstance(response, dict):
        return {"verified_response": False, "strictly_improved": False, "non_higher_verified": False, "tool_workflow_verified": False}
    before, after = response.get("p_fail_before"), response.get("p_fail_after")
    valid_pair = finite_risk(before) and finite_risk(after)
    rewritten = response.get("rewritten_prompt")
    trace = response.get("tool_trace")
    completed_trace = sum(isinstance(row, dict) and row.get("completed") is True for row in trace) if isinstance(trace, list) else 0
    reported_calls = response.get("tool_call_count")
    verified_tools = (
        not isinstance(reported_calls, bool)
        and isinstance(reported_calls, int)
        and reported_calls >= 3
        and completed_trace >= 3
        and response.get("session_verified") is True
        and response.get("session_service") == "Agent Platform Sessions"
    )
    return {
        "verified_response": bool(valid_pair and isinstance(rewritten, str)),
        "strictly_improved": bool(valid_pair and after < before and isinstance(rewritten, str) and rewritten != prompt and response.get("rewrite_status") == "improved"),
        "non_higher_verified": bool(valid_pair and after <= before and isinstance(rewritten, str)),
        "higher_risk_returned": bool(valid_pair and after > before),
        "tool_workflow_verified": bool(verified_tools),
        "completed_trace_calls": completed_trace,
        "reported_tool_calls": reported_calls,
        "session_verified": response.get("session_verified") is True,
        "server_elapsed_seconds": response.get("agent_trace", {}).get("elapsed_seconds") if isinstance(response.get("agent_trace"), dict) else None,
    }


def summarize(rows: list[dict]) -> dict:
    improved = sum(row.get("checks", {}).get("strictly_improved", False) for row in rows)
    non_higher = sum(row.get("checks", {}).get("non_higher_verified", False) for row in rows)
    workflow = sum(row.get("checks", {}).get("tool_workflow_verified", False) for row in rows)
    higher = sum(row.get("checks", {}).get("higher_risk_returned", False) for row in rows)
    return {
        "selected_prompts": 10,
        "completed_prompts": len(rows),
        "total_http_attempts": sum(len(row.get("attempts", [])) for row in rows),
        "rate_limit_retries": sum(max(0, len(row.get("attempts", [])) - 1) for row in rows),
        "strictly_improved_count": improved,
        "non_higher_verified_count": non_higher,
        "higher_risk_returned_count": higher,
        "tool_workflow_verified_count": workflow,
        "V5_pass": len(rows) == 10 and improved >= 6 and non_higher == 10,
        "V6_all_ten_verified": len(rows) == 10 and workflow == 10,
        "no_increase_observed": higher == 0,
        "never_higher_verified": len(rows) == 10 and non_higher == 10,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Verified Cloud Run base URL")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "rewrites_live.json")
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "rewrites_live.txt")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        parser.error("Use an HTTPS service base URL without credentials, path, query or fragment")
    if args.report.exists() or args.log.exists():
        parser.error("Receipt files already exist; preserve them and select new explicit output paths for a separately authorized run")
    engine_path = args.artifacts / "engine.json"
    engine_bytes = engine_path.read_bytes()
    engine = json.loads(engine_bytes)
    if len(engine["prompts"]) != len(engine["difficulty"]) or len(engine["prompts"]) < 10:
        parser.error("The artifact must contain at least ten matching prompt/item records")
    ranked = sorted(range(len(engine["prompts"])), key=lambda index: (-float(engine["difficulty"][index]), index))[:10]
    selection = [{"rank": rank, "artifact_index": index, "prompt": engine["prompts"][index], "difficulty": float(engine["difficulty"][index]), "prompt_sha256": hashlib.sha256(engine["prompts"][index].encode()).hexdigest()} for rank, index in enumerate(ranked, 1)]
    if any(not isinstance(row["prompt"], str) or not 1 <= len(row["prompt"]) <= 4000 or not math.isfinite(row["difficulty"]) for row in selection):
        parser.error("Selected prompt or item difficulty is invalid")
    endpoint = args.url.rstrip("/") + "/preflight"
    report = {
        "check": "V5 and V6 real endpoint receipts",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "engine_artifact_sha256": hashlib.sha256(engine_bytes).hexdigest(),
        "selection_rule": "ten largest fitted item difficulties, descending; ties retain artifact row order; selected before any request",
        "selected_hard_prompts": selection,
        "client_isolation": "fresh in-memory cookie jar per prompt; no session_id submitted; headers and cookies are never persisted",
        "retry_rule": "at most one retry per prompt, only HTTP429 with a valid Retry-After of at most120s; never retry503, timeouts or latency failures",
        "rows": [],
        "complete": False,
    }
    save_report(args.report, report)
    append_log(args.log, {key: report[key] for key in ("check", "engine_artifact_sha256", "selection_rule", "retry_rule")})
    try:
        for selected in selection:
            opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
            row = {**selected, "attempts": []}
            for attempt_number in (1, 2):
                attempt, wait = perform_request(opener, endpoint, selected["prompt"], attempt_number)
                retry = attempt_number == 1 and attempt.get("http_status") == 429 and wait is not None
                attempt["retry_decision"] = "one rate-limit retry after required delay" if retry else "no retry"
                if retry:
                    attempt["retry_wait_seconds"] = wait
                row["attempts"].append(attempt)
                # Persist each attempt before waiting or sending another request.
                report["in_progress"] = row
                save_report(args.report, report)
                append_log(args.log, {"rank": row["rank"], "prompt_sha256": row["prompt_sha256"], "attempt": attempt})
                if not retry:
                    break
                print(f"rank={row['rank']} HTTP429; one documented retry after {wait}s", flush=True)
                remaining = wait
                while remaining:
                    duration = min(remaining, 30)
                    time.sleep(duration)
                    remaining -= duration
            row["checks"] = assess(selected["prompt"], row["attempts"][-1])
            report["rows"].append(row)
            report.pop("in_progress", None)
            report["summary"] = summarize(report["rows"])
            save_report(args.report, report)
            print(json.dumps({"rank": row["rank"], "http_status": row["attempts"][-1].get("http_status"), "elapsed_seconds": row["attempts"][-1]["elapsed_seconds"], **row["checks"]}, allow_nan=False), flush=True)
    except KeyboardInterrupt:
        report["interrupted"] = True
        report["summary"] = summarize(report["rows"])
        save_report(args.report, report)
        return 130
    report["complete"] = True
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = summarize(report["rows"])
    first_trace = next((row["attempts"][-1]["response"].get("tool_trace") for row in report["rows"] if row["checks"]["tool_workflow_verified"]), None)
    report["first_verified_tool_trace"] = first_trace
    save_report(args.report, report)
    append_log(args.log, {"summary": report["summary"], "first_verified_tool_trace": first_trace})
    print(json.dumps(report["summary"], allow_nan=False), flush=True)
    return 0 if report["summary"]["V5_pass"] and report["summary"]["V6_all_ten_verified"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as problem:
        # Network/SDK diagnostics can contain transport or resource identities.
        print(json.dumps({"verification_error_type": type(problem).__name__, "complete": False}), file=sys.stderr)
        raise SystemExit(2)
