#!/usr/bin/env python3
"""Six no-retry typed-prompt requests against a no-traffic v4 candidate."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import ssl
import sys
from time import monotonic
from urllib.parse import urlsplit

import certifi
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_rewrites import assess, forbidden_markers, save_report

REPEATED_PROMPT = "a spoon and a laptop on a quiet desk with an ivory notebook"
PROMPTS = [REPEATED_PROMPT, REPEATED_PROMPT,
           "a cat and a dog resting beside separate cushions in a quiet room",
           "a bicycle and a car parked side by side on a quiet road",
           "a purple clock on a plain wall above a wooden table",
           "an indoor gymnasium with a basketball resting on the floor"]
PRIVATE_FIELDS = {"session_id", "cookie", "cookies", "set-cookie", "authorization",
                  "access_token", "refresh_token", "api_key"}


def safe_response(value):
    if isinstance(value, dict):
        return {key: safe_response(item) for key, item in value.items()
                if str(key).lower() not in PRIVATE_FIELDS}
    if isinstance(value, list):
        return [safe_response(item) for item in value]
    return value


def checks(prompt, row):
    result = assess(prompt, row)
    response = row.get("response", {})
    completed = Counter(item.get("tool") for item in response.get("tool_trace", [])
                        if isinstance(item, dict) and item.get("completed") is True)
    result["required_tools_completed"] = completed["nearest_prompts"] >= 1 and (
        completed["rewrite"] >= 1 and completed["difficulty"] >= 2)
    result["tool_workflow_verified"] = result["tool_workflow_verified"] and result["required_tools_completed"]
    result["live_rewrite_verified"] = response.get("rewrite_source") == "live"
    result["under_45_seconds"] = row.get("elapsed_seconds", 45) < 45
    return result


def summarize(rows):
    before = rows[0].get("response", {}).get("rewritten_prompt") if rows else None
    after = rows[1].get("response", {}).get("rewritten_prompt") if len(rows) > 1 else None
    pair_differs = isinstance(before, str) and isinstance(after, str) and before != after
    summary = {"expected_requests": 6, "completed_requests": len(rows),
        "http_200_count": sum(row.get("http_status") == 200 for row in rows),
        "live_rewrite_count": sum(row.get("checks", {}).get("live_rewrite_verified", False) for row in rows),
        "tool_workflow_verified_count": sum(row.get("checks", {}).get("tool_workflow_verified", False) for row in rows),
        "verified_response_count": sum(row.get("checks", {}).get("verified_response", False) for row in rows),
        "under_45_seconds_count": sum(row.get("checks", {}).get("under_45_seconds", False) for row in rows),
        "repeated_prompt_rewrites_differ": pair_differs, "http_retries": 0,
        "image_model_calls": 0, "veo_calls": 0}
    summary["pass"] = len(rows) == 6 and all(summary[key] == 6 for key in (
        "http_200_count", "live_rewrite_count", "tool_workflow_verified_count",
        "verified_response_count", "under_45_seconds_count")) and pair_differs
    return summary


async def perform_request(url, prompt):
    row = {"http_status": None}
    started = monotonic()
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        async with asyncio.timeout(45):
            async with httpx.AsyncClient(verify=context, timeout=httpx.Timeout(40, connect=10),
                                        follow_redirects=False, trust_env=False) as client:
                response = await client.post(url + "/preflight", json={"prompt": prompt})
                row["http_status"] = response.status_code
                row["response_bytes_received"] = len(response.content)
                if len(response.content) > 2_000_000:
                    row["response_omitted"] = "response exceeded safety size limit"
                elif forbidden_markers(response.content):
                    row["response_omitted"] = "credential markers detected"
                else:
                    try:
                        value = response.json()
                        if isinstance(value, dict):
                            row["response"] = safe_response(value)
                        else:
                            row["response_omitted"] = "response was not a JSON object"
                    except ValueError:
                        row["response_omitted"] = "response was not valid JSON"
    except (httpx.HTTPError, TimeoutError, OSError) as error:
        row["error_type"] = type(error).__name__
    row["elapsed_seconds"] = round(monotonic() - started, 6)
    return row


async def verify(args):
    report = {"check": "V-E six typed prompts and live rewrite variation",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": args.url.rstrip("/") + "/preflight", "complete": False,
        "selection": PROMPTS, "retry_policy": "exactly one HTTP attempt per row; no retry",
        "isolation": "fresh client and cookie jar per request; no session_id submitted; cookies and session IDs omitted",
        "timeout_seconds": {"http": 40, "total_per_request": 45}, "rows": []}
    save_report(args.report, report)
    for number, prompt in enumerate(PROMPTS, 1):
        # A durable dispatch prevents an interrupted run from silently repeating a request.
        report["dispatch"] = {"number": number, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                              "dispatched_at_utc": datetime.now(timezone.utc).isoformat()}
        save_report(args.report, report)
        row = {"number": number, "prompt": prompt, **await perform_request(args.url.rstrip("/"), prompt)}
        row["checks"] = checks(prompt, row)
        report["rows"].append(row)
        report.pop("dispatch", None)
        report["summary"] = summarize(report["rows"])
        save_report(args.report, report)
        print(json.dumps({"number": number, "http_status": row["http_status"],
                          "elapsed_seconds": row["elapsed_seconds"], **row["checks"]}), flush=True)
    report["complete"] = True
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = summarize(report["rows"])
    if len(report["rows"]) >= 2:
        report["same_prompt_rewrite_proof"] = {"prompt": REPEATED_PROMPT,
            "rewrites": [row.get("response", {}).get("rewritten_prompt") for row in report["rows"][:2]],
            "differ": report["summary"]["repeated_prompt_rewrites_differ"]}
    save_report(args.report, report)
    print(json.dumps(report["summary"]), flush=True)
    return 0 if report["summary"]["pass"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/preview_v4/preflight_candidate.json")
    args = parser.parse_args()
    url = urlsplit(args.url)
    if (url.scheme != "https" or not url.hostname or url.username or url.password or url.query
            or url.fragment or url.path not in ("", "/")):
        parser.error("Use an HTTPS service base URL without credentials, path, query or fragment")
    if args.report.exists():
        parser.error("Preserve the existing receipt; choose a new explicit report for a separate authorized run")
    try:
        return asyncio.run(verify(args))
    except Exception as error:
        print(json.dumps({"complete": False, "error_type": type(error).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
