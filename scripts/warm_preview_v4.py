#!/usr/bin/env python3
"""Persist ten exact sample actions as saved stills, without implicit retries.

`plan` is offline. Current steering uses `run-app --url URL --execute` for all ten
HTTP actions, sixty seconds apart; saved hits use zero image calls. Every dispatch
first uses the shared85/v4 durable ledger. Failed/unknown calls are never retried.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import base64
from datetime import datetime, timezone, timedelta
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import probe_preview_v4 as probe

REPORTS = probe.REPORTS
FIXTURE = ROOT / "cloud/sample_rewrites.json"
MODEL = "gemini-2.5-flash-image"
SPACING = 60.1
MAX_JPEG_BYTES = 900 * 1024
MIN_IMAGE_BYTES = 10 * 1024


def actions():
    from cloud.sample_rewrites import load_sample_rewrites

    tree = ast.parse((ROOT / "app.py").read_text())
    samples = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "SAMPLES" for target in node.targets))
    pinned = load_sample_rewrites(samples, FIXTURE)
    result = []
    for sample in samples:
        for variant in ("original", "rewrite"):
            prompt = sample if variant == "original" else pinned[sample]["rewritten_prompt"]
            result.append({"action_id": f"WARM-{len(result) + 1:02d}", "sample_prompt": sample,
                           "prompt": prompt, "variant": variant,
                           "prompt_sha256": probe.sha(prompt),
                           "risk_before": pinned[sample]["p_fail_before"],
                           "risk_after": pinned[sample]["p_fail_after"],
                           "rewrite_status": pinned[sample]["rewrite_status"]})
    if len(result) != 10 or len({row["prompt"] for row in result}) != 9:
        raise ValueError("Warm fixture must contain ten actions and nine unique exact texts")
    return result


def load_service_configuration():
    result = subprocess.run(["gcloud", "run", "services", "describe", "preflight", "--region",
                             "asia-southeast1", "--format=json"], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError("Service configuration unavailable; no image calls made")
    service = json.loads(result.stdout)
    settings = {item["name"]: item.get("value") for item in
                service["spec"]["template"]["spec"]["containers"][0].get("env", [])}
    project = settings.get("GOOGLE_CLOUD_PROJECT")
    database = settings.get("PREFLIGHT_FIRESTORE_DATABASE", "preflight-aibc")
    if not project or not database or database == "(default)":
        raise ValueError("Dedicated Firestore configuration unavailable; no image calls made")
    # These identifiers remain in memory and never appear in receipts or exceptions.
    os.environ["GOOGLE_CLOUD_PROJECT"] = project
    os.environ["PREFLIGHT_FIRESTORE_DATABASE"] = database
    return project


def jpeg_for_cache(raw):
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as source:
        image = source.convert("RGB")
    for _ in range(10):
        for quality in (90, 82, 74, 66, 58, 50):
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality)
            jpeg = output.getvalue()
            if MIN_IMAGE_BYTES < len(jpeg) <= MAX_JPEG_BYTES:
                return jpeg, list(image.size), quality
        if len(jpeg) <= MIN_IMAGE_BYTES:
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=98)
            if MIN_IMAGE_BYTES < len(output.getvalue()) <= MAX_JPEG_BYTES:
                return output.getvalue(), list(image.size), 98
            raise ValueError("Converted real image is below the gate's10KiB threshold")
        image = image.resize((max(1, int(image.width * .85)), max(1, int(image.height * .85))))
    raise ValueError("Real image cannot fit the existing900KiB cache limit")


def cached_receipt(cached):
    from PIL import Image

    raw = cached.get("bytes")
    if not isinstance(raw, bytes) or not MIN_IMAGE_BYTES < len(raw) <= MAX_JPEG_BYTES:
        raise ValueError("Existing sample cache image violates byte limits")
    with Image.open(io.BytesIO(raw)) as image:
        dimensions = list(image.size)
        image.verify()
    created = cached.get("created_at")
    if isinstance(created, str):
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
    if not isinstance(created, datetime) or created.tzinfo is None:
        raise ValueError("Existing sample cache generation date is unavailable")
    model, size = cached.get("model"), cached.get("size")
    if not isinstance(model, str) or not isinstance(size, str):
        raise ValueError("Existing sample cache model/size is unavailable")
    return {"http_status": 200, "image_bytes": len(raw), "image_sha256": probe.sha(raw),
            "dimensions": dimensions, "model": model, "size": size,
            "generated_at": created.isoformat(), "generated_date": created.astimezone(timezone.utc).date().isoformat(),
            "cache": "hit", "model_calls": 0, "cost_usd": 0.0,
            "metadata_label": f"Saved still · generated {created.astimezone(timezone.utc).date().isoformat()} · 0 model calls · $0.00"}


def persist_generated(store, action, row):
    from cloud.preview import sample_preview_cache_key
    from cloud.store import prompt_id

    if not row.get("pass_image") or not row.get("image_file"):
        return {"http_status": row.get("http_status"), "image_bytes": row.get("image_bytes", 0),
                "model_calls": 1, "cache": "miss", "cache_saved": False,
                "error_class": row.get("error_class") or "NoUsableImage"}
    raw = (ROOT / row["image_file"]).read_bytes()
    if probe.sha(raw) != row["image_sha256"]:
        raise ValueError("Provider image bytes differ from recorded digest")
    jpeg, dimensions, quality = jpeg_for_cache(raw)
    generated = datetime.fromisoformat(row["finished_at_kst"]).astimezone(timezone.utc)
    key = sample_preview_cache_key(action["prompt"])
    cost = row.get("cost", {}).get("list_price_usd")
    data = {"bytes": jpeg, "model": row["model"], "size": "1K", "created_at": generated,
            "prompt_id": prompt_id(action["prompt"]), "generation_cost_usd": cost,
            "traffic_type": row.get("traffic_type"), "cost_basis": "token-usage-list-price",
            "billing_verified": False, "warm_attempt_id": row["attempt_id"]}
    store.save_preview(key, data)
    verified = store.get_preview(key)
    if not verified or probe.sha(verified.get("bytes", b"")) != probe.sha(jpeg):
        raise ValueError("Saved sample cache readback differs from generated image")
    cache = cached_receipt(verified)
    return {**cache, "model_calls": 1, "cache": "saved", "cache_saved": True,
            "cost_usd": cost, "provider_image_bytes": row["image_bytes"],
            "provider_image_sha256": row["image_sha256"], "jpeg_quality": quality,
            "dimensions": dimensions, "latency_seconds": row["latency_seconds"],
            "provider_http_status": row["http_status"], "provider_attempt_id": row["attempt_id"]}


def report_for(rows, fixture_hash, complete=False):
    known = sum(row["model_calls"] for row in rows if type(row.get("model_calls")) is int)
    unknown = sum(row.get("model_calls") is None for row in rows)
    return {"schema_version": 1, "phase": "warm", "updated_at_kst": probe.now(),
            "fixture_sha256": fixture_hash, "model": MODEL, "location": "global",
            "minimum_new_call_start_spacing_seconds": 60, "rows": rows,
            "complete": complete, "summary": {
                "planned_ui_actions": 10, "unique_texts": 9, "completed_actions": len(rows),
                "usable_saved_stills": sum(row.get("http_status") == 200 and row.get("cache_saved") is not False
                                           and row.get("image_bytes", 0) > MIN_IMAGE_BYTES for row in rows),
                "new_image_attempts": known + unknown,
                "known_model_calls": known, "unknown_call_rows": unknown,
                "all_ten_actions_ready": complete and len(rows) == 10 and all(
                    row.get("http_status") == 200 and row.get("cache_saved") is not False
                    and row.get("image_bytes", 0) > MIN_IMAGE_BYTES for row in rows)},
            "budget": probe.budget_state()}


async def warm(args):
    from cloud.preview import sample_preview_cache_key

    probe.validate()
    if probe.budget_state().get("scope") == "preview_v4_only":
        raise ValueError("Current steering requires remaining warming through app /preview; direct warm disabled")
    fixture_hash = probe.sha(FIXTURE.read_bytes())
    work = actions()
    preregistration = json.loads((REPORTS / "preregistration.json").read_text())
    if preregistration.get("warm_plan", {}).get("fixture_sha256") != fixture_hash:
        raise ValueError("Saved rewrite fixture differs from warm preregistration")
    if not args.execute:
        raise ValueError("Warm execution requires explicit --execute; no image calls made")
    project = load_service_configuration()
    from cloud.store import FirestoreDifficultyStore
    store = FirestoreDifficultyStore.from_env()
    path = REPORTS / "warm.json"
    prior = json.loads(path.read_text()) if path.exists() else {}
    if prior and prior.get("fixture_sha256") != fixture_hash:
        raise ValueError("Warm fixture changed; preserve the prior receipts")
    rows = prior.get("rows", [])
    prior_actions = {row["action_id"]: row for row in rows}
    arm = next(arm for arm in preregistration["arms"] if arm["id"] == "P2")
    with probe.exclusive_model(MODEL):
        ledger = probe._read_rows(REPORTS / "call_ledger.jsonl")
        results = {row["attempt_id"]: row for row in ledger if row.get("event") == "attempt_result"}
        reserved = {row["attempt_id"]: row for row in ledger if row.get("event") == "attempt_reserved"}
        completed_same_model = [row for row in results.values() if row.get("model") == MODEL and row.get("started_at_kst")]
        previous_start = max((datetime.fromisoformat(row["started_at_kst"]).timestamp()
                              for row in completed_same_model), default=0)
        unknown_same_model = [row for row in reserved.values() if row.get("model") == MODEL
                              and row["attempt_id"] not in results]
        previous_start = max([previous_start] + [datetime.fromisoformat(row["reserved_at_kst"]).timestamp()
                                                  + probe.TIMEOUT for row in unknown_same_model])
        attempted_prompts = {row["prompt_sha256"]: row for row in reserved.values()
                             if row.get("purpose") == "warm"}
        pending = [action for action in work if action["action_id"] not in prior_actions]
        if args.limit:
            pending = pending[:args.limit]
        for action in pending:
            row = {**action, "cache_key": sample_preview_cache_key(action["prompt"]),
                   "model": MODEL, "size": "1K", "model_calls": 0}
            try:
                cached = store.get_preview(row["cache_key"])
                if cached:
                    row.update(cached_receipt(cached))
                elif action["prompt_sha256"] in attempted_prompts:
                    reservation = attempted_prompts[action["prompt_sha256"]]
                    provider = results.get(reservation["attempt_id"])
                    if provider and provider.get("pass_image") and provider.get("image_file"):
                        row.update(persist_generated(store, action, provider))
                        row["model_calls"] = 0
                        row["recovered_from_prior_attempt"] = provider["attempt_id"]
                    else:
                        row.update(http_status=provider.get("http_status") if provider else None,
                                   image_bytes=0, cache_saved=False, model_calls=0,
                                   error_class="PreviouslyDispatchedPromptNotRetried",
                                   prior_attempt_id=reservation["attempt_id"])
                else:
                    delay = previous_start + SPACING - time.time()
                    if delay > 0:
                        await asyncio.sleep(delay)
                    reservation = probe.reserve_attempt(action["action_id"], MODEL, "warm", action["prompt_sha256"])
                    attempted_prompts[action["prompt_sha256"]] = reservation
                    row["model_calls"] = 1
                    provider = await probe.call_once(arm, action["prompt"], project, REPORTS,
                                                     action["action_id"], previous_start)
                    provider["probe_arm"] = provider.pop("arm")
                    provider.update(purpose="warm", prompt_sha256=action["prompt_sha256"])
                    probe.append_result(provider)
                    results[provider["attempt_id"]] = provider
                    previous_start = datetime.fromisoformat(provider["started_at_kst"]).timestamp()
                    row.update(persist_generated(store, action, provider))
            except Exception as exc:
                row.update(http_status=row.get("http_status"), image_bytes=row.get("image_bytes", 0),
                           cache_saved=False, error_class=type(exc).__name__)
            rows.append(row)
            probe._atomic_json(path, report_for(rows, fixture_hash, complete=len(rows) == 10))
            print(json.dumps({key: row.get(key) for key in ("action_id", "variant", "http_status", "image_bytes", "model_calls", "cache_saved", "error_class")}), flush=True)
    result = report_for(rows, fixture_hash, complete=len(rows) == 10)
    probe._atomic_json(path, result)
    return result


def runtime_budget_before_app_warm(warm_requests, remaining_qa_admissions):
    from cloud.store import FirestoreDifficultyStore
    from zoneinfo import ZoneInfo

    load_service_configuration()
    store = FirestoreDifficultyStore.from_env()
    snapshot = store.client.collection("service_v1").document("preview-budget").get(timeout=10)
    document = snapshot.to_dict() if snapshot.exists else {}
    current = datetime.now(timezone.utc)
    count = document.get("day_count", 0) if document.get("day") == current.date().isoformat() else 0
    if type(count) is not int or count < 0:
        raise ValueError("Firestore preview day counter is invalid")
    reset = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), timezone.utc)
    row = {"recorded_at_kst": probe.now(), "day_count": count, "daily_limit": 60,
           "remaining_admissions": 60 - count, "remaining_warm_http_requests": warm_requests,
           "remaining_qa_admissions": remaining_qa_admissions,
           "total_admissions_required": warm_requests + remaining_qa_admissions,
           "fits": count + warm_requests + remaining_qa_admissions <= 60,
           "reset_at_utc": reset.isoformat(), "reset_at_kst": reset.astimezone(ZoneInfo("Asia/Seoul")).isoformat()}
    probe._atomic_json(REPORTS / "firestore_daily_budget_app_warm_admission.json", row)
    if not row["fits"]:
        raise ValueError("Remaining warm and QA admissions exceed unchanged60/day cap; STOP before warming")
    return row


def snapshot_runtime_admissions(name):
    """Read the native shared app counter without sending a preview request."""
    from cloud.store import FirestoreDifficultyStore
    from zoneinfo import ZoneInfo

    load_service_configuration()
    store = FirestoreDifficultyStore.from_env()
    snapshot = store.client.collection("service_v1").document("preview-budget").get(timeout=10)
    doc = snapshot.to_dict() if snapshot.exists else {}
    current = datetime.now(timezone.utc)
    count = doc.get("day_count", 0) if doc.get("day") == current.date().isoformat() else 0
    reset = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), timezone.utc)
    row = {"recorded_at_kst": probe.now(), "source": "Firestore service_v1/preview-budget direct read",
           "snapshot_exists": snapshot.exists, "stored_day_utc": doc.get("day"),
           "effective_day_utc": current.date().isoformat(), "day_count": count, "daily_limit": 60,
           "remaining_admissions": 60 - count, "reset_at_utc": reset.isoformat(),
           "reset_at_kst": reset.astimezone(ZoneInfo("Asia/Seoul")).isoformat(),
           "preview_requests_made_by_snapshot": 0, "provider_calls_made_by_snapshot": 0}
    probe._atomic_json(REPORTS / (name + ".json"), row)
    return row


async def warm_through_app(args):
    """All ten sample actions use /preview, including exact-text saved hits."""
    import certifi
    import httpx
    from PIL import Image
    from cloud.preview import sample_preview_cache_key

    probe.validate()
    if not args.execute or not args.url or not args.url.startswith("https://"):
        raise ValueError("App warming requires --execute and verifiedhttps --url")
    fixture_hash = probe.sha(FIXTURE.read_bytes())
    preregistration = json.loads((REPORTS / "preregistration.json").read_text())
    if preregistration.get("warm_plan", {}).get("fixture_sha256") != fixture_hash:
        raise ValueError("Saved rewrite fixture differs from preregistration")
    work = actions()
    path = REPORTS / "warm.json"
    previous = json.loads(path.read_text()) if path.exists() else {}
    if previous and previous.get("fixture_sha256") != fixture_hash:
        raise ValueError("Warm fixture differs from prior receipts")
    rows = previous.get("rows", [])
    if rows and any("http_requests" not in row for row in rows):
        archive = REPORTS / "warm_direct_before_steering.json"
        raw = path.read_bytes()
        if archive.exists() and archive.read_bytes() != raw:
            raise ValueError("Prior direct warm archive already exists with different bytes")
        archive.write_bytes(raw)
        rows = []
    completed = {row["action_id"]: row for row in rows}
    unique_done = {row["prompt"]: row for row in rows}
    pending = [action for action in work if action["action_id"] not in completed]
    if args.limit:
        pending = pending[:args.limit]
    needed = len(pending)
    runtime_budget_before_app_warm(needed, args.remaining_qa_admissions)
    with probe.exclusive_model(MODEL):
        ledger = probe._read_rows(REPORTS / "call_ledger.jsonl")
        reserved_ids = {row["attempt_id"] for row in ledger if row.get("event") == "attempt_reserved"}
        completed_calls = [row for row in ledger if row.get("event") == "attempt_result"
                           and row.get("model") == MODEL and row.get("started_at_kst")]
        # Start spacing after the prior response is conservative for server dispatch.
        last_finish = max((datetime.fromisoformat(row.get("finished_at_kst", row["started_at_kst"])).timestamp()
                           for row in completed_calls), default=0)
        transport = httpx.AsyncHTTPTransport(retries=0, verify=certifi.where())
        async with httpx.AsyncClient(transport=transport, timeout=44, follow_redirects=False) as client:
            for action in pending:
                row = {**action, "cache_key": sample_preview_cache_key(action["prompt"]),
                       "model": MODEL, "size": "1K", "model_calls": 0, "http_requests": 0}
                attempt_id = "APP-" + action["action_id"]
                row["attempt_id"] = attempt_id
                if attempt_id in reserved_ids:
                    row.update(http_status=None, image_bytes=0, cache_saved=False,
                               error_class="PreviouslyReservedActionNotRetried")
                else:
                    delay = last_finish + SPACING - time.time()
                    if delay > 0:
                        await asyncio.sleep(delay)
                    probe.reserve_attempt(attempt_id, MODEL, "warm", action["prompt_sha256"])
                    started = time.monotonic()
                    row.update(started_at_kst=probe.now(), http_requests=1, model_calls=None)
                    try:
                        async with asyncio.timeout(44):
                            response = await client.post(args.url.rstrip("/") + "/preview",
                                                         json={"prompt": action["prompt"], "variant": action["variant"]})
                        row["http_status"] = response.status_code
                        if response.status_code == 200:
                            data = response.json()
                            encoded = data.get("image_data_url", "")
                            raw = base64.b64decode(encoded.partition(",")[2], validate=True)
                            with Image.open(io.BytesIO(raw)) as image:
                                image.verify()
                            row.update(image_bytes=len(raw), image_sha256=probe.sha(raw), model=data.get("model"),
                                       size=data.get("size"), model_calls=data.get("model_calls"),
                                       cache=data.get("cache"), cache_header=response.headers.get("X-Preview-Cache"),
                                       cache_saved=data.get("cache") in ("hit", "miss") and len(raw) <= MAX_JPEG_BYTES,
                                       generated_at=data.get("generated_at"), generated_date=data.get("generated_date"),
                                       metadata_label=data.get("metadata_label"), cost_usd=data.get("cost_usd"),
                                       cost={"list_price_usd": data.get("cost_usd"), "billing_verified": False,
                                             "cost_basis": data.get("cost_basis")})
                            if not MIN_IMAGE_BYTES < len(raw) <= MAX_JPEG_BYTES or row["cache_header"] != row["cache"]:
                                row.update(cache_saved=False, error_class="CacheResponseFailedGate")
                        else:
                            row.update(image_bytes=0, cache_saved=False, error_class="PreviewHTTPError")
                    except Exception as exc:
                        row.update(http_status=row.get("http_status"), image_bytes=row.get("image_bytes", 0),
                                   cache_saved=False, error_class=type(exc).__name__)
                    row.update(finished_at_kst=probe.now(), latency_seconds=round(time.monotonic() - started, 3))
                    last_finish = time.time()
                    probe.append_result({"attempt_id": attempt_id, "purpose": "warm",
                                         **{key: value for key, value in row.items() if key not in ("prompt", "sample_prompt")}})
                rows.append(row)
                unique_done[action["prompt"]] = row
                probe._atomic_json(path, report_for(rows, fixture_hash, complete=len(rows) == 10))
                print(json.dumps({key: row.get(key) for key in ("action_id", "http_status", "image_bytes", "model_calls", "http_requests", "error_class")}), flush=True)
                if row.get("http_status") != 200 or row.get("cache_saved") is False:
                    break
    result = report_for(rows, fixture_hash, complete=len(rows) == 10)
    probe._atomic_json(path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run", "run-app"))
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--url")
    parser.add_argument("--remaining-qa-admissions", type=int, default=22,
                        help="Future required V-C10 + self-QA12; unchangedFirestore60/day")
    args = parser.parse_args()
    try:
        if args.limit is not None and not 1 <= args.limit <= 10:
            raise ValueError("Warm action limit must be1..10")
        if args.command == "plan":
            result = {"provider_calls": 0, "fixture_sha256": probe.sha(FIXTURE.read_bytes()),
                      "actions": actions(), "unique_texts": 9, "maximum_image_attempts": 9,
                      "model": MODEL, "location": "global", "budget": probe.budget_state()}
        elif args.command == "run-app":
            result = asyncio.run(warm_through_app(args))
        else:
            result = asyncio.run(warm(args))
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({"execution_halted": True, "error_class": type(exc).__name__,
                          "message": str(exc) if isinstance(exc, ValueError) else "Warm halted; inspect structured receipts"}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
