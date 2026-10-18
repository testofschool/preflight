#!/usr/bin/env python3
"""One-shot preview gates with durable receipts and a conservative 45-call ledger.

Run warm, cache and fresh separately against the no-traffic candidate. A saved
dispatch is never sent again, including after a transport failure or interruption.
No image bytes, transport cookies or arbitrary provider diagnostics are retained.
"""
from __future__ import annotations

import argparse
import ast
import base64
from datetime import datetime
import fcntl
import hashlib
import json
import math
from pathlib import Path
import ssl
import sys
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import certifi
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.verify_rewrites import save_report

PRIMARY = "gemini-3.1-flash-lite-image"
FALLBACK = "gemini-3.1-flash-image"
PRICES = {PRIMARY: 0.0336, FALLBACK: 0.045}
MAX_CALLS = 45
WORST_CALLS = 3
SPACING = 13.0
KST = ZoneInfo("Asia/Seoul")
META_KEYS = ("model", "size", "aspect_ratio", "cost_usd", "pricing_source",
             "pricing_checked_date", "latency_ms", "model_calls", "attempts",
             "fallback_used", "synthid", "caption", "cache_key", "model_attempts")


def now() -> str:
    return datetime.now(KST).isoformat()


def digest(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def samples() -> list[str]:
    tree = ast.parse((ROOT / "app.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SAMPLES" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, list) and len(value) == 5 and all(isinstance(x, str) for x in value):
                return value
    raise ValueError("Exactly five app.py SAMPLES are required")


def fresh_selection(path: Path) -> tuple[list[str], str]:
    raw = path.read_bytes()
    prompts = raw.decode("utf-8").splitlines()
    if len(prompts) != 20 or len(set(prompts)) != 20 or any(not p or p != p.strip() or len(p) > 4000 for p in prompts):
        raise ValueError("Preregistered file must contain exactly20 distinct clean prompts")
    return prompts, digest(raw)


def row_checks(row: dict) -> bool:
    return row.get("http_status") == 200 and row.get("image_bytes", 0) > 10 * 1024


def summary(report: dict) -> dict:
    rows = report["rows"]
    latencies = sorted(float(row["latency_seconds"]) for row in rows if row.get("latency_seconds") is not None)
    p95 = latencies[math.ceil(0.95 * len(latencies)) - 1] if latencies else None
    image_successes = sum(row_checks(row) for row in rows)
    cache_hits = sum(row_checks(row) and row.get("cache") == "hit" and row.get("model_calls") == 0 for row in rows)
    no504 = all(row.get("http_status") != 504 for row in rows)
    before_timeout = all(row.get("http_status") is not None and row.get("latency_seconds") is not None and row["latency_seconds"] < report["cloud_timeout_seconds"] for row in rows)
    unexpected_cache_hits = sum(row.get("cache") == "hit" for row in rows)
    expected = 20 if report["phase"] == "fresh" else 10
    finished = len(rows) == expected
    return {"scheduled": expected, "completed": len(rows), "http_200_image_gt10KiB": image_successes,
            "cache_hit_zero_model_calls": cache_hits, "p95_seconds_nearest_rank": p95,
            "http_504_count": sum(row.get("http_status") == 504 for row in rows),
            "all_returned_before_cloud_timeout": bool(finished and before_timeout),
            "reported_model_calls": sum(row["model_calls"] for row in rows if isinstance(row.get("model_calls"), int)),
            "unmeasured_model_call_rows": sum(row.get("model_calls") is None for row in rows),
            "unexpected_cache_hits": unexpected_cache_hits if report["phase"] == "fresh" else None,
            "V11b_pass": finished and cache_hits == 10 if report["phase"] == "cache" else None,
            "V11c_pass": finished and image_successes >= 19 and unexpected_cache_hits == 0 if report["phase"] == "fresh" else None,
            "V11d_pass": finished and p95 is not None and p95 <= 45 and no504 and before_timeout if report["phase"] == "fresh" else None,
            "warm_pass": finished and image_successes == 10 if report["phase"] == "warm" else None}


def refresh_budget(budget: dict) -> None:
    entries = budget["entries"]
    known = sum(row["model_calls"] for row in entries if isinstance(row.get("model_calls"), int))
    unknown = sum(row["reserved_model_calls"] for row in entries if row.get("model_calls") is None)
    outputs = sum(row.get("successful_generated_image_list_price_usd", 0) for row in entries)
    by_model = {model: 0 for model in PRICES}
    unallocated = 0
    for row in entries:
        attempts = row.get("model_attempts", [])
        if isinstance(row.get("model_calls"), int) and len(attempts) == row["model_calls"] and all(isinstance(attempt, dict) and attempt.get("model") in PRICES for attempt in attempts):
            for attempt in attempts:
                by_model[attempt["model"]] += 1
        elif isinstance(row.get("model_calls"), int):
            unallocated += row["model_calls"]
    budget.update(known_new_model_calls=known, unmeasured_reserved_model_calls=unknown,
                  total_image_calls_conservative=budget["initial_image_calls"] + known + unknown,
                  new_model_calls_by_model=by_model, known_calls_without_model_allocation=unallocated,
                  new_attempts_at_actual_model_list_prices_usd=round(sum(PRICES[model] * count for model, count in by_model.items()), 6),
                  successful_generated_image_list_price_usd=round(outputs, 6),
                  initial_attempts_list_price_bound_usd=round(budget["initial_image_calls"] * max(PRICES.values()), 6),
                  all_attempts_list_price_bound_usd=round((budget["initial_image_calls"] + known + unknown) * max(PRICES.values()), 6),
                  price_note="Successful cache misses use the returned actual-model price. The attempt bound charges every failed or unknown attempt at the largest listed per-image price; this is not observed billing.",
                  updated_at_kst=now())


def load_budget(args) -> dict:
    path = args.receipts / "image_budget.json"
    if path.exists():
        budget = json.loads(path.read_text())
        if budget["budget_date_kst"] != args.budget_date or budget["initial_image_calls"] != args.initial_image_calls:
            raise ValueError("Existing ledger date/initial attempts differ; preserve it and resolve the inputs")
    else:
        budget = {"schema_version": 1, "budget_date_kst": args.budget_date,
                  "initial_image_calls": args.initial_image_calls,
                  "initial_calls_source": args.initial_calls_source,
                  "limit": MAX_CALLS, "worst_case_calls_reserved_before_every_preview": WORST_CALLS,
                  "request_spacing_seconds": SPACING, "entries": [], "created_at_kst": now()}
    refresh_budget(budget)
    save_report(path, budget)
    return budget


def save_budget(args, budget: dict) -> None:
    refresh_budget(budget)
    save_report(args.receipts / "image_budget.json", budget)


def selection_row(prompt: str, variant: str, sample_prompt: str | None = None) -> dict:
    return {"prompt": prompt, "variant": variant, "sample_prompt": sample_prompt, "prompt_sha256": digest(prompt)}


def prepare_warm(api, args, report: dict) -> None:
    if "selection" in report:
        return
    expected = samples()
    if "selection_rewrites" not in report:
        report["selection_rewrites"] = []
    if report.get("preflight_in_progress"):
        raise ValueError("Interrupted rewrite lookup is retained; do not repeat it implicitly")
    for sample in expected[len(report["selection_rewrites"]):]:
        report["preflight_in_progress"] = sample
        save_report(args.report, report)
        start = time.monotonic()
        response = api.post(args.url + "/preflight", json={"prompt": sample})
        payload = response.json()
        rewritten = payload.get("rewritten_prompt")
        row = {"sample_prompt": sample, "http_status": response.status_code,
               "latency_seconds": round(time.monotonic() - start, 6),
               "supported": payload.get("supported"), "rewritten_prompt": rewritten,
               "rewrite_status": payload.get("rewrite_status"),
               "p_fail_before": payload.get("p_fail_before"), "p_fail_after": payload.get("p_fail_after")}
        report["selection_rewrites"].append(row)
        report.pop("preflight_in_progress", None)
        save_report(args.report, report)
        if response.status_code != 200 or not payload.get("supported") or not isinstance(rewritten, str) or not rewritten.strip():
            raise ValueError("One live sample rewrite was unavailable; no preview of a substitute is allowed")
    if len(report["selection_rewrites"]) != 5 or any(r["http_status"] != 200 or not r.get("supported") or not isinstance(r.get("rewritten_prompt"), str) or not r["rewritten_prompt"].strip() for r in report["selection_rewrites"]):
        raise ValueError("Five exact live rewrite responses are required")
    report["selection"] = [selection_row(sample, "original", sample) for sample in expected]
    report["selection"] += [selection_row(row["rewritten_prompt"], "rewrite", row["sample_prompt"]) for row in report["selection_rewrites"]]
    save_report(args.report, report)


def read_meta(response: httpx.Response) -> tuple[dict, bytes]:
    try:
        payload = response.json()
    except (ValueError, UnicodeError):
        return {}, b""
    if not isinstance(payload, dict):
        return {}, b""
    meta = {key: payload[key] for key in META_KEYS if key in payload}
    encoded = payload.get("image_data_url", "")
    image = b""
    if isinstance(encoded, str) and encoded.startswith("data:image/") and ";base64," in encoded:
        try:
            image = base64.b64decode(encoded.split(",", 1)[1], validate=True)
        except (ValueError, TypeError):
            pass
    return meta, image


def reported_count(meta: dict, response: httpx.Response, key: str) -> int | None:
    value = meta.get(key)
    if not isinstance(value, bool) and isinstance(value, int) and value >= 0:
        return value
    for header in ("x-preview-" + key.replace("_", "-"), "x-preflight-" + key.replace("_", "-")):
        value = response.headers.get(header)
        if value is not None and value.isdigit():
            return int(value)
    return None


def dispatch(api, args, report: dict, budget: dict, selected: dict, index: int) -> dict:
    if any(entry["phase"] == args.phase and entry["prompt_sha256"] == selected["prompt_sha256"] and entry.get("variant") == selected["variant"] for entry in budget["entries"]):
        raise ValueError("A dispatch for this phase/prompt already exists; do not repeat it")
    if datetime.now(KST).date().isoformat() != args.budget_date:
        raise ValueError("KST date changed; stop and audit the daily ledger")
    refresh_budget(budget)
    if budget["total_image_calls_conservative"] + WORST_CALLS > MAX_CALLS:
        raise ValueError("45-call cap: insufficient room for the worst three-call miss")
    previous = max((entry["dispatch_epoch"] for entry in budget["entries"]), default=0)
    while time.time() - previous < SPACING:
        time.sleep(min(1, SPACING - (time.time() - previous)))
    entry = {"id": len(budget["entries"]) + 1, "phase": args.phase,
             "selection_index": index, "prompt_sha256": selected["prompt_sha256"], "variant": selected["variant"],
             "endpoint": args.url + "/preview", "dispatch_epoch": time.time(), "dispatched_at_kst": now(),
             "reserved_model_calls": WORST_CALLS, "model_calls": None, "state": "dispatch_reserved"}
    budget["entries"].append(entry)
    save_budget(args, budget)
    row = {**selected, "selection_index": index, "ledger_entry_id": entry["id"],
           "dispatched_at_kst": entry["dispatched_at_kst"], "http_status": None,
           "model_calls": None, "attempts": None, "fallback_used": None, "image_bytes": 0}
    report["in_progress"] = row
    save_report(args.report, report)
    start = time.monotonic()
    try:
        response = api.post(args.url + "/preview", json={"prompt": selected["prompt"], "variant": selected["variant"]})
        meta, image = read_meta(response)
        row.update(http_status=response.status_code, cache=response.headers.get("x-preview-cache"),
                   error_class=response.headers.get("x-preflight-error"),
                   retry_after=response.headers.get("retry-after"), response=meta,
                   image_bytes=len(image), image_sha256=digest(image) if image else None,
                   model=meta.get("model"), size=meta.get("size"), cost_usd=meta.get("cost_usd"),
                   model_calls=reported_count(meta, response, "model_calls"),
                   attempts=reported_count(meta, response, "attempts"), fallback_used=meta.get("fallback_used"))
        if row["model"] and row["size"]:
            row["cache_key"] = digest(json.dumps(["preview-v1", selected["prompt"], row["model"], row["size"]], ensure_ascii=False, separators=(",", ":")))
    except (httpx.HTTPError, OSError, ValueError) as error:
        row["transport_error_type"] = type(error).__name__
    row["latency_seconds"] = round(time.monotonic() - start, 6)
    calls = row.get("model_calls")
    entry.update(model_calls=calls, model=row.get("model"), attempts=row.get("attempts"),
                 fallback_used=row.get("fallback_used"), http_status=row["http_status"],
                 state="measured" if calls is not None else "unmeasured_reserved")
    if row_checks(row) and isinstance(calls, int) and calls > 0 and row.get("model") in PRICES:
        entry["successful_generated_image_list_price_usd"] = PRICES[row["model"]]
    if isinstance(row.get("response", {}).get("model_attempts"), list):
        entry["model_attempts"] = row["response"]["model_attempts"]
    save_budget(args, budget)
    report["rows"].append(row)
    report.pop("in_progress", None)
    report["summary"] = summary(report)
    save_report(args.report, report)
    print(json.dumps({key: row.get(key) for key in ("selection_index", "variant", "http_status", "cache", "model_calls", "attempts", "fallback_used", "model", "image_bytes", "latency_seconds")}), flush=True)
    if calls is not None and calls > WORST_CALLS:
        raise ValueError("Runtime exceeded the predeclared three-attempt bound; stop")
    return row


def recover_dispatch(args, report: dict, budget: dict) -> None:
    """A crash consumes its full reservation and its prompt is never retried."""
    if "in_progress" in report:
        row = report.pop("in_progress")
        entry = next(e for e in budget["entries"] if e["id"] == row["ledger_entry_id"])
        row.update(model_calls=entry.get("model_calls"), transport_error_type="InterruptedResponseUnmeasured",
                   latency_seconds=None, request_repeated=False)
        report["rows"].append(row)
        report["summary"] = summary(report)
        save_report(args.report, report)
    # The budget reservation is saved first. Recover the narrow crash window
    # before the corresponding report in_progress row was durably written.
    completed_ids = {row["ledger_entry_id"] for row in report["rows"]}
    for entry in budget["entries"]:
        if entry["phase"] != args.phase or entry["endpoint"] != args.url + "/preview" or entry["id"] in completed_ids:
            continue
        selected = next((row for row in report.get("selection", []) if row["prompt_sha256"] == entry["prompt_sha256"] and row["variant"] == entry.get("variant")), None)
        if selected is None:
            raise ValueError("Orphan budget reservation cannot be matched to a preregistered selection")
        report["rows"].append({**selected, "selection_index": entry["selection_index"], "ledger_entry_id": entry["id"],
            "dispatched_at_kst": entry["dispatched_at_kst"], "http_status": entry.get("http_status"),
            "model_calls": entry.get("model_calls"), "attempts": entry.get("attempts"),
            "fallback_used": entry.get("fallback_used"), "model": entry.get("model"),
            "image_bytes": 0, "latency_seconds": None, "transport_error_type": "InterruptedResponseUnmeasured", "request_repeated": False})
        report["summary"] = summary(report)
        save_report(args.report, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("warm", "cache", "fresh"))
    parser.add_argument("--url")
    parser.add_argument("--receipts", type=Path, default=ROOT / "reports/preview_v3")
    parser.add_argument("--prompts", type=Path, default=ROOT / "reports/preview_v3/fresh_prompts.txt")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--initial-image-calls", type=int, help="Required live: prior provider attempts today, including failures")
    parser.add_argument("--initial-calls-source", default="Operator-supplied previous image attempts today; includes failed provider attempts")
    parser.add_argument("--budget-date", default=datetime.now(KST).date().isoformat())
    parser.add_argument("--cloud-timeout-seconds", type=float, default=60)
    parser.add_argument("--resume", action="store_true", help="Continue only not-yet-dispatched rows; never retry saved calls")
    parser.add_argument("--validate-plan", action="store_true", help="Validate preregistration and local supported vocabulary; no HTTP")
    args = parser.parse_args()
    prompts, prompt_hash = fresh_selection(args.prompts)
    if args.validate_plan:
        from preflight_core import PreflightEngine
        engine = PreflightEngine.load(ROOT / "artifacts")
        supported = sum(engine.predict(prompt).get("supported") is True for prompt in prompts)
        print(json.dumps({"fresh_prompts": len(prompts), "fresh_distinct": len(set(prompts)),
                          "locally_supported": supported, "manifest_sha256": prompt_hash, "sample_prompts": samples(), "provider_calls": 0}))
        return 0 if supported == 20 else 2
    if not args.phase or not args.url:
        parser.error("--phase and --url are required unless --validate-plan")
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        parser.error("Use an HTTPS base URL without credentials or path")
    args.url = args.url.rstrip("/")
    if args.initial_image_calls is None or not 0 <= args.initial_image_calls <= MAX_CALLS or not 0 < args.cloud_timeout_seconds <= 60:
        parser.error("Initial calls must be0..45 and Cloud Run timeout0..60s")
    args.receipts.mkdir(parents=True, exist_ok=True)
    args.report = args.report or args.receipts / (args.phase + ".json")
    budget = load_budget(args)
    if args.report.exists():
        if not args.resume:
            parser.error("Receipt exists; use --resume to skip every saved dispatch")
        report = json.loads(args.report.read_text())
        if any(report.get(k) != v for k, v in (("phase", args.phase), ("url", args.url), ("fresh_prompts_sha256", prompt_hash))):
            parser.error("Existing receipt endpoint/phase/manifest differs")
        recover_dispatch(args, report, budget)
        if report.get("complete"):
            print(json.dumps(report["summary"]))
            return 0 if report.get("passed") else 1
    else:
        report = {"schema_version": 1, "phase": args.phase, "url": args.url,
                  "created_at_kst": now(), "fresh_prompts_sha256": prompt_hash,
                  "fresh_prompts_preregistered_mtime_ns": args.prompts.stat().st_mtime_ns,
                  "request_policy": "one dispatch per row; no HTTP retries; starts spaced at least13s; unknown outcomes consume three calls",
                  "cloud_timeout_seconds": args.cloud_timeout_seconds, "rows": [], "complete": False}
        save_report(args.report, report)
    with httpx.Client(verify=ssl.create_default_context(cafile=certifi.where()), timeout=httpx.Timeout(65), follow_redirects=False) as api:
        if args.phase == "warm":
            prepare_warm(api, args, report)
        elif args.phase == "cache":
            warmed = json.loads((args.receipts / "warm.json").read_text())
            if not warmed.get("complete") or not warmed.get("passed"):
                raise ValueError("Ten successful warm rows are required before cache validation")
            report["selection"] = warmed["selection"]
        else:
            report["selection"] = [selection_row(prompt, "original") for prompt in prompts]
            already_dispatched = {entry["prompt_sha256"] for entry in budget["entries"] if entry["phase"] != "fresh"}
            if already_dispatched.intersection(row["prompt_sha256"] for row in report["selection"]):
                raise ValueError("A preregistered fresh prompt was already previewed by another phase")
        save_report(args.report, report)
        completed = {row["selection_index"] for row in report["rows"]}
        for index, selected in enumerate(report["selection"], 1):
            if index not in completed:
                dispatch(api, args, report, budget, selected, index)
    report.update(complete=True, completed_at_kst=now(), summary=summary(report))
    report["passed"] = bool(report["summary"][{"warm": "warm_pass", "cache": "V11b_pass", "fresh": "V11c_pass"}[args.phase]])
    if args.phase == "fresh":
        report["passed"] = report["passed"] and report["summary"]["V11d_pass"]
    save_report(args.report, report)
    print(json.dumps(report["summary"]), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        # Serialize all invocations without creating an extra tracked lock file.
        with Path(__file__).open("rb") as script_lock:
            fcntl.flock(script_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"gate_error_type": type(error).__name__, "message": str(error) if isinstance(error, ValueError) else "Diagnostics suppressed; receipts retain completed requests", "complete": False}), file=sys.stderr)
        raise SystemExit(2)
