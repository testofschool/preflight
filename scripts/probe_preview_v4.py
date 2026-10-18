#!/usr/bin/env python3
"""Preregistered one-attempt Vertex image probes and a shared durable call cap.

Importing this module, validate and summarize make zero provider calls. Execution
requires the explicit run --execute command. Warm/UI tooling must also reserve
every image attempt through reserve_attempt before dispatch. A reservation is
never reused after a timeout, interruption or an unknown transport outcome.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/preview_v4"
KST = ZoneInfo("Asia/Seoul")
DAILY_CAP = 85
INITIAL_CALLS = 44
DATE = "2026-10-18"
SPACING = 15.0
TIMEOUT = 30.0


def now():
    return datetime.now(KST).isoformat()


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def _atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    with temporary.open("x") as output:
        json.dump(data, output, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def _append(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as output:
        output.write(json.dumps(row, sort_keys=True) + "\n")
        output.flush()
        os.fsync(output.fileno())


def _read_rows(path):
    path = Path(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


@contextmanager
def exclusive_model(model, reports=REPORTS):
    """Every image-producing path must use this lock; P1 holds it for its arm."""
    reports = Path(reports)
    reports.mkdir(parents=True, exist_ok=True)
    with (reports / ("model_" + sha(model)[:16] + ".lock")).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another run holds this model; no provider request made") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def budget_state(reports=REPORTS):
    rows = _read_rows(Path(reports) / "call_ledger.jsonl")
    initial = [row for row in rows if row.get("event") == "baseline"]
    if len(initial) != 1:
        raise ValueError("Shared ledger requires exactly one verified baseline")
    baseline = initial[0]
    if baseline.get("budget_date_kst") != DATE or baseline.get("initial_image_calls") != INITIAL_CALLS or baseline.get("daily_cap") != DAILY_CAP:
        raise ValueError("Shared ledger date, baseline or cap differs from preregistration")
    initial_calls = INITIAL_CALLS
    scope = "all_image_attempts_today"
    amendments = [row for row in rows if row.get("event") == "budget_amendment"]
    if amendments:
        if len(amendments) != 1:
            raise ValueError("Multiple budget amendments need explicit reconciliation")
        amendment_row = amendments[0]
        amendment_path = Path(reports) / amendment_row["file"]
        raw_amendment = amendment_path.read_bytes()
        amendment = json.loads(raw_amendment)
        if sha(raw_amendment) != amendment_row["sha256"] or amendment.get("scope") != "preview_v4_only" or amendment.get("daily_cap") != DAILY_CAP or amendment.get("initial_image_calls") != 0 or amendment.get("historical_v3_attempts_excluded") != INITIAL_CALLS:
            raise ValueError("Budget amendment differs from the explicit v4-only scope")
        initial_calls = 0
        scope = "preview_v4_only"
    reservations = [row for row in rows if row.get("event") == "attempt_reserved"]
    ids = [row["attempt_id"] for row in reservations]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate attempt reservation in shared ledger")
    results = {row["attempt_id"]: row for row in rows if row.get("event") == "attempt_result"}
    refunded = [row["attempt_id"] for row in reservations if row.get("purpose") == "qa"
                and (result := results.get(row["attempt_id"], {})).get("http_status") == 200
                and result.get("cache") == "hit" and type(result.get("model_calls")) is int
                and result["model_calls"] == 0]
    measured, zeros, unknown = 0, 0, 0
    measured_by_model = {}
    for reservation in reservations:
        result = results.get(reservation["attempt_id"], {})
        calls = result.get("model_calls")
        if reservation.get("purpose") in ("qa", "warm") and not result.get("probe_arm") and result.get("http_status") != 200:
            calls = None
        if type(calls) is not int and result.get("probe_arm") and type(result.get("http_status")) is int:
            # The pre-steering direct warm has a native Vertex HTTP response,
            # recorded before the explicit model_calls field was introduced.
            calls = 1
        if type(calls) is int and calls >= 0:
            measured += calls
            zeros += calls == 0
            model = result.get("model") or reservation["model"]
            measured_by_model[model] = measured_by_model.get(model, 0) + calls
        else:
            unknown += 1
    # Only verified QA cache hits settle to zero. Failed/unknown/probe dispatches
    # retain their full reservation, including a reported zero after an error.
    used = initial_calls + len(reservations) - len(refunded)
    if used > DAILY_CAP:
        raise ValueError("Shared ledger already exceeds authorized image-call cap")
    return {"budget_date_kst": DATE, "scope": scope, "initial_image_calls": initial_calls,
            "historical_v3_attempts_excluded": INITIAL_CALLS if amendments else 0,
            "all_runs_today_conservative_attempts": INITIAL_CALLS + len(reservations) - len(refunded),
            "known_measured_model_attempts": measured, "known_zero_model_call_responses": zeros,
            "unknown_dispatch_reservations": unknown, "known_measured_attempts_by_model": measured_by_model,
            "v4_reserved_attempts": len(reservations), "verified_zero_call_qa_hits": len(refunded),
            "v4_effective_attempts": len(reservations) - len(refunded), "today_conservative_attempts": used,
            "daily_cap": DAILY_CAP, "remaining": DAILY_CAP - used}


def reserve_attempt(attempt_id, model, purpose, prompt_sha256, reports=REPORTS):
    """Durably charge one attempt before dispatch, including failed/unknown calls."""
    reports = Path(reports)
    if datetime.now(KST).date().isoformat() != DATE:
        raise ValueError("Budget is only authorized for the preregistered KST date")
    with (reports / "call_ledger.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = budget_state(reports)
        rows = _read_rows(reports / "call_ledger.jsonl")
        seals = [row for row in rows if row.get("event") == "preregistration_sealed"]
        current_preregistration = sha((reports / "preregistration.json").read_bytes())
        if seals and (len(seals) != 1 or seals[0]["sha256"] != current_preregistration):
            raise ValueError("Preregistration changed after the first reserved attempt")
        if any(row.get("attempt_id") == attempt_id for row in rows):
            raise ValueError("Attempt was already reserved; it cannot be retried")
        if state["remaining"] < 1:
            raise ValueError("Image-call cap reached; no provider request made")
        if not seals:
            _append(reports / "call_ledger.jsonl", {"event": "preregistration_sealed",
                    "sha256": current_preregistration, "sealed_at_kst": now()})
        row = {"event": "attempt_reserved", "attempt_id": attempt_id, "model": model,
               "purpose": purpose, "prompt_sha256": prompt_sha256, "reserved_at_kst": now(),
               "today_conservative_attempts": state["today_conservative_attempts"] + 1}
        _append(reports / "call_ledger.jsonl", row)
        return row


def append_result(row, reports=REPORTS):
    reports = Path(reports)
    with (reports / "call_ledger.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = _read_rows(reports / "call_ledger.jsonl")
        attempt = row["attempt_id"]
        if not any(entry.get("attempt_id") == attempt and entry.get("event") == "attempt_reserved" for entry in rows):
            raise ValueError("No durable reservation exists for this result")
        if any(entry.get("attempt_id") == attempt and entry.get("event") == "attempt_result" for entry in rows):
            raise ValueError("Result already exists for this attempt")
        _append(reports / "call_ledger.jsonl", {"event": "attempt_result", **row})


def validate(reports=REPORTS):
    reports = Path(reports)
    plan = json.loads((reports / "preregistration.json").read_text())
    if sha((reports / "official_sources.json").read_bytes()) != plan["official_sources_sha256"]:
        raise ValueError("Official evidence differs from preregistration")
    all_hashes = []
    if plan["policy"]["timeout_seconds"] > 30 or plan["policy"]["minimum_start_spacing_seconds"] < 15:
        raise ValueError("Preregistered timing violates user limits")
    if len(plan["arms"]) != 3 or {a["id"] for a in plan["arms"]} != {"P1", "P2", "P3"}:
        raise ValueError("Exactly the three requested arms are required")
    for arm in plan["arms"]:
        if len(arm["prompts"]) != 20:
            raise ValueError("Each arm requires20 preregistered prompts")
        for item in arm["prompts"]:
            path = ROOT / item["file"]
            data = path.read_bytes()
            if sha(data) != item["sha256"] or not data.strip():
                raise ValueError("Prompt differs from preregistration")
            all_hashes.append(sha(data.strip()))
    if len(set(all_hashes)) != 60:
        raise ValueError("All60 fresh prompts must be distinct")
    if not all(arm.get("price_verified") for arm in plan["arms"]):
        raise ValueError("All arms require official price verification before execution")
    return {"valid": True, "provider_calls_made_by_validation": 0, "preregistration_sha256": sha((reports / "preregistration.json").read_bytes()),
            "prompt_count": 60, "budget": budget_state(reports)}


def _usage_fields(usage):
    keys = ("promptTokenCount", "candidatesTokenCount", "thoughtsTokenCount", "totalTokenCount", "trafficType")
    result = {key: usage.get(key) for key in keys if key in usage}
    for key in ("promptTokensDetails", "candidatesTokensDetails"):
        result[key] = [{"modality": row.get("modality"), "tokenCount": row.get("tokenCount")}
                       for row in usage.get(key, []) if isinstance(row, dict)]
    return result


def _cost(arm, usage, image_count):
    rates = arm["standard_usd_per_million_tokens"]
    traffic = usage.get("trafficType")
    if arm["id"] == "P1":
        if traffic == "ON_DEMAND_PRIORITY":
            rates = arm["priority_usd_per_million_tokens"]
        elif traffic != "ON_DEMAND":
            return {"list_price_usd": None, "cost_basis": "traffic_type_unavailable", "billing_verified": False}
    input_tokens = usage.get("promptTokenCount")
    details = usage.get("candidatesTokensDetails") or []
    image_tokens = sum(row.get("tokenCount", 0) for row in details if row.get("modality") == "IMAGE")
    text_tokens = sum(row.get("tokenCount", 0) for row in details if row.get("modality") == "TEXT")
    inferred = not image_tokens and image_count > 0
    if inferred:
        image_tokens = arm["image_output_tokens"] * image_count
    if not text_tokens and isinstance(usage.get("candidatesTokenCount"), int):
        text_tokens = max(0, usage["candidatesTokenCount"] - image_tokens)
    thoughts = usage.get("thoughtsTokenCount") or 0
    if not isinstance(input_tokens, int):
        return {"list_price_usd": None, "image_component_usd": round(image_tokens * rates["image_output"] / 1e6, 9),
                "cost_basis": "input_usage_unavailable", "billing_verified": False}
    cost = (input_tokens * rates["input"] + (text_tokens + thoughts) * rates["text_output"] + image_tokens * rates["image_output"]) / 1e6
    return {"list_price_usd": round(cost, 9), "input_tokens": input_tokens, "image_output_tokens": image_tokens,
            "text_output_tokens": text_tokens, "thought_tokens": thoughts,
            "cost_basis": "usage_with_documented_image_tokens" if inferred else "usage_modality_tokens",
            "billing_verified": False, "rates_usd_per_million_tokens": rates}


async def call_once(arm, prompt, project, reports, attempt_id, previous_start_epoch=0):
    """Exactly one HTTP POST. No retries, redirects, SDK loops or fallback."""
    import certifi
    import google.auth
    from google.auth.transport.requests import Request
    import httpx
    from PIL import Image

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    image_config = {"aspectRatio": "16:9"}
    if arm.get("size_wire"):
        image_config["imageSize"] = arm["size_wire"]
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "candidateCount": 1,
                                 "imageConfig": image_config}}
    headers = {"Authorization": "Bearer " + credentials.token, "Content-Type": "application/json", **arm["headers"]}
    url = f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/{arm['location']}/publishers/google/models/{arm['model']}:generateContent"
    start = time.monotonic()
    row = {"attempt_id": attempt_id, "arm": arm["id"], "model": arm["model"], "location": arm["location"],
           "size_wire": arm.get("size_wire"), "started_at_kst": now(), "http_status": None,
           "image_bytes": 0, "image_count": 0, "traffic_type": None, "error_class": None, "model_calls": 1}
    try:
        transport = httpx.AsyncHTTPTransport(retries=0, verify=certifi.where())
        async with httpx.AsyncClient(transport=transport, timeout=TIMEOUT, follow_redirects=False, verify=certifi.where()) as client:
            # Credentials and transport setup occur before the start-spacing gate.
            # An extra100ms keeps bookkeeping jitter below the required15s gap.
            delay = previous_start_epoch + SPACING + 0.1 - time.time()
            if delay > 0:
                await asyncio.sleep(delay)
            row["started_at_kst"] = now()
            start = time.monotonic()
            async with asyncio.timeout(TIMEOUT):
                response = await client.post(url, headers=headers, json=body)
        row["http_status"] = response.status_code
        if response.status_code == 200:
            response_data = response.json()
            row["model_version"] = response_data.get("modelVersion")
            usage = _usage_fields(response_data.get("usageMetadata") or {})
            row["usage"] = usage
            row["traffic_type"] = usage.get("trafficType")
            for candidate in response_data.get("candidates", []):
                for part in (candidate.get("content") or {}).get("parts", []):
                    inline = part.get("inlineData") or {}
                    if inline.get("mimeType", "").startswith("image/") and inline.get("data"):
                        data = base64.b64decode(inline["data"], validate=True)
                        with Image.open(io.BytesIO(data)) as image:
                            dimensions = list(image.size)
                            image.verify()
                        row["image_count"] += 1
                        if len(data) > row["image_bytes"]:
                            row["image_bytes"] = len(data)
                            row["image_sha256"] = sha(data)
                            row["dimensions"] = dimensions
                            row["image_mime_type"] = inline["mimeType"]
                            ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}.get(inline["mimeType"], ".img")
                            path = (Path(reports) / "probe_images" / (attempt_id + ext)).resolve()
                            path.parent.mkdir(parents=True, exist_ok=True)
                            path.write_bytes(data)
                            row["image_file"] = str(path.relative_to(ROOT))
            row["cost"] = _cost(arm, usage, row["image_count"])
            if not row["image_count"]:
                row["error_class"] = "NoImageBytes"
        else:
            # Keep structured provider status only; arbitrary diagnostics can contain identifiers.
            try:
                row["provider_error_status"] = response.json().get("error", {}).get("status")
            except (ValueError, AttributeError):
                pass
            row["error_class"] = "ProviderHTTPError"
            row["cost"] = {"list_price_usd": 0.0, "cost_basis": "official_non_200_no_charge",
                           "billing_verified": False}
    except Exception as exc:
        row["error_class"] = type(exc).__name__
    row["latency_seconds"] = round(time.monotonic() - start, 3)
    row["finished_at_kst"] = now()
    row["pass_image"] = row["http_status"] == 200 and row["image_bytes"] > 10 * 1024
    return row


async def run_arm(args):
    validate(args.reports)
    plan = json.loads((args.reports / "preregistration.json").read_text())
    arm = next(item for item in plan["arms"] if item["id"] == args.arm)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise ValueError("GOOGLE_CLOUD_PROJECT must be set; its value is never logged")
    if not args.execute:
        raise ValueError("Execution requires explicit --execute; no provider request made")
    result_file = args.reports / f"{args.arm}.jsonl"
    with exclusive_model(arm["model"], args.reports):
        reserved = _read_rows(args.reports / "call_ledger.jsonl")
        used = {row.get("attempt_id") for row in reserved if row.get("event") == "attempt_reserved"}
        pending = [item for item in arm["prompts"] if item["id"] not in used]
        if args.limit:
            pending = pending[:args.limit]
        if budget_state(args.reports)["remaining"] < len(pending):
            raise ValueError("Arm cannot fit remaining daily budget; no provider request made")
        if not pending:
            raise ValueError("No unreserved prompts remain; dispatched calls are never retried")
        # Preserve spacing after a prior interrupted invocation as well as within this process.
        past = [row for row in reserved if row.get("event") == "attempt_reserved" and row.get("model") == arm["model"]]
        completed = {row["attempt_id"]: row for row in reserved if row.get("event") == "attempt_result"}
        previous_epoch = max((datetime.fromisoformat(completed[row["attempt_id"]]["started_at_kst"]).timestamp()
                              if row["attempt_id"] in completed and completed[row["attempt_id"]].get("started_at_kst")
                              else datetime.fromisoformat(row["reserved_at_kst"]).timestamp() + TIMEOUT
                              for row in past), default=0)
        for item in pending:
            prompt = (ROOT / item["file"]).read_text().strip()
            reserve_attempt(item["id"], arm["model"], "probe", item["sha256"], args.reports)
            row = await call_once(arm, prompt, project, args.reports, item["id"], previous_epoch)
            previous_epoch = datetime.fromisoformat(row["started_at_kst"]).timestamp()
            row["prompt_sha256"] = item["sha256"]
            append_result(row, args.reports)
            _append(result_file, row)
            print(json.dumps({key: row[key] for key in ("attempt_id", "http_status", "latency_seconds", "image_bytes", "traffic_type", "error_class")}), flush=True)
    return summarize(args.reports)


def summarize(reports=REPORTS):
    reports = Path(reports).resolve()
    plan = json.loads((reports / "preregistration.json").read_text())
    ledger = _read_rows(reports / "call_ledger.jsonl")
    registered_ids = {item["id"] for arm in plan["arms"] for item in arm["prompts"]}
    results = [dict(row) for row in ledger if row.get("event") == "attempt_result" and row.get("attempt_id") in registered_ids]
    annotations = []
    for row in results:
        if row.get("error_class") == "ValueError" and row.get("http_status") == 200 and row.get("image_sha256") and not row.get("image_file"):
            matches = [path for path in (reports / "probe_images").glob(row["attempt_id"] + ".*")
                       if sha(path.read_bytes()) == row["image_sha256"]]
            if len(matches) == 1:
                arm = next(arm for arm in plan["arms"] if arm["id"] == row["arm"])
                annotation = {"attempt_id": row["attempt_id"], "local_receipt_error_class": "ValueError",
                              "original_receipt_preserved": True, "additional_provider_calls": 0,
                              "image_file": str(matches[0].relative_to(ROOT)), "image_sha256_verified": True,
                              "cost": _cost(arm, row.get("usage", {}), row.get("image_count", 0)),
                              "basis": "Existing image file SHA matches recorded provider bytes; token usage and traffic type already recorded before local relative-path serialization failed."}
                annotations.append(annotation)
                row.update(image_file=annotation["image_file"], cost=annotation["cost"],
                           local_receipt_error_class="ValueError")
        if isinstance(row.get("http_status"), int) and row["http_status"] != 200:
            cost = {"list_price_usd": 0.0, "cost_basis": "official_non_200_no_charge", "billing_verified": False}
            if not row.get("cost"):
                annotations.append({"attempt_id": row["attempt_id"], "cost": cost,
                                    "original_receipt_preserved": True, "additional_provider_calls": 0,
                                    "basis": "Official pricing charges only HTTP200; observed4xx/5xx are zero list-price input/output."})
            row["cost"] = cost
    _atomic_json(reports / "derived_probe_annotations.json", {"updated_at_kst": now(), "rows": annotations,
                 "original_receipts_modified": False, "additional_provider_calls": 0})
    arms = []
    for arm in plan["arms"]:
        rows = [row for row in results if row["arm"] == arm["id"]]
        count = sum(row.get("pass_image") is True for row in rows)
        prices = [row.get("cost", {}).get("list_price_usd") for row in rows if row.get("pass_image")]
        price_verified = arm["price_verified"] and bool(prices) and all(isinstance(price, (float, int)) for price in prices)
        mean_price = sum(prices) / len(prices) if price_verified else None
        priced = [row.get("cost", {}).get("list_price_usd") for row in rows]
        known_total = sum(value for value in priced if isinstance(value, (int, float)))
        arms.append({"arm": arm["id"], "planned": 20, "completed": len(rows), "successful_http200_images_gt10KiB": count,
                     "reliability_passes": len(rows) == 20 and count >= 19,
                     "price_verifiable_from_responses": price_verified,
                     "passes": len(rows) == 20 and count >= 19 and price_verified,
                     "status": "complete" if len(rows) == 20 else "UNRUN" if not rows else "incomplete",
                     "mean_successful_list_price_usd": mean_price, "known_list_price_total_usd": round(known_total, 9),
                     "unpriced_rows": sum(value is None for value in priced),
                     "non200_no_charge_rows": sum(isinstance(row.get("http_status"), int) and row["http_status"] != 200 for row in rows),
                     "actual_billing_verified": False})
    passing = [arm for arm in arms if arm["passes"]]
    passing.sort(key=lambda arm: (-arm["successful_http200_images_gt10KiB"], arm["mean_successful_list_price_usd"], arm["arm"]))
    decision = {"updated_at_kst": now(), "arms": arms, "selected_arm": passing[0]["arm"] if passing else None,
                "live_generation_allowed": bool(passing), "reason": "highest success count; tie lowest measured list price" if passing else "No completed arm meets preregistered19/20 image and verified-price rule",
                "budget": budget_state(reports)}
    _atomic_json(reports / "probe_decision.json", decision)
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "run", "summarize"))
    parser.add_argument("--arm", choices=("P1", "P2", "P3"))
    parser.add_argument("--reports", type=Path, default=REPORTS)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    try:
        if args.limit is not None and not 1 <= args.limit <= 20:
            raise ValueError("Limit must be1..20; partial arms cannot pass")
        if args.command == "run":
            if not args.arm:
                raise ValueError("run requires --arm")
            result = asyncio.run(run_arm(args))
        else:
            result = validate(args.reports) if args.command == "validate" else summarize(args.reports)
        print(json.dumps(result, indent=2, sort_keys=True))
    except Exception as exc:
        # Do not print provider exception text, project IDs, credentials or token-bearing URLs.
        print(json.dumps({"error_class": type(exc).__name__, "execution_halted": True,
                          "message": str(exc) if isinstance(exc, ValueError) else "Runner halted; inspect safe structured receipts"}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
