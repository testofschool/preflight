#!/usr/bin/env python3
"""Inspect exactly three frozen owner clips once and score independent labels."""

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
CATEGORIES = {"identity_drift", "flicker", "broken_text", "physics"}


def finite_number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def validate_reference(document: dict) -> list[dict]:
    if document.get("schema_version") != 1 or not document.get("frozen_at_utc") or not document.get("label_provenance"):
        raise ValueError("An independently annotated, frozen version-one reference is required")
    if document.get("tolerance_seconds") != 2:
        raise ValueError("The frozen matching tolerance must be exactly two seconds")
    rule = document.get("pass_rule", {})
    if rule.get("minimum_matched_defects") != 2 or rule.get("required_clips") != 3 or rule.get("one_to_one") is not True:
        raise ValueError("The frozen pass rule must require three clips and two one-to-one defect matches")
    clips = document.get("clips")
    if not isinstance(clips, list) or len(clips) != 3:
        raise ValueError("Exactly three frozen owner clips are required")
    if len({clip.get("id") for clip in clips}) != 3 or len({clip.get("sha256") for clip in clips}) != 3:
        raise ValueError("The frozen clips must have distinct identities and source hashes")
    for clip in clips:
        if not isinstance(clip.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", clip["id"]):
            raise ValueError("Invalid frozen clip identifier")
        if not isinstance(clip.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", clip["sha256"]):
            raise ValueError("Each frozen source must have a SHA256")
        if not isinstance(clip.get("path"), str) or not Path(clip["path"]).is_absolute():
            raise ValueError("Frozen source paths must be absolute")
        if not finite_number(clip.get("duration_seconds")) or not 0 < clip["duration_seconds"] <= 30:
            raise ValueError("Frozen clip duration must be within the thirty-second bound")
        if not isinstance(clip.get("prompt"), str) or not 1 <= len(clip["prompt"].strip()) <= 4000:
            raise ValueError("Each frozen clip needs a neutral scene prompt")
        if not isinstance(clip.get("model"), str) or not 1 <= len(clip["model"].strip()) <= 200:
            raise ValueError("Each frozen clip needs a model provenance label")
        defects = clip.get("known_defects")
        if not isinstance(defects, list) or not defects:
            raise ValueError("Each selected clip must have at least one independently confirmed defect")
        for defect in defects:
            if defect.get("category") not in CATEGORIES or defect.get("confidence") != "confirmed":
                raise ValueError("Only independently confirmed rubric categories are evaluable")
            if not finite_number(defect.get("seconds")) or not 0 <= defect["seconds"] <= clip["duration_seconds"]:
                raise ValueError("A frozen defect timestamp is outside its clip")
    return clips


def load_source_bytes(clips: list[dict]) -> list[bytes]:
    """Validate every immutable source before the first network request."""
    sources = []
    for clip in clips:
        path = Path(clip["path"])
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 30 * 1024 * 1024:
            raise ValueError("A frozen MP4 source is absent or exceeds the upload bound")
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != clip["sha256"]:
            raise ValueError("A frozen source hash changed; no uploads were started")
        sources.append(payload)
    return sources


def match_defects(expected: list[dict], predicted: list[dict], tolerance: float = 2.0) -> dict:
    """Maximum-cardinality bipartite matching prevents double-counted detections."""
    edges = {
        index: sorted(
            [candidate for candidate, observed in enumerate(predicted) if observed["category"] == known["category"] and abs(observed["seconds"] - known["seconds"]) <= tolerance],
            key=lambda candidate: (abs(predicted[candidate]["seconds"] - known["seconds"]), candidate),
        )
        for index, known in enumerate(expected)
    }
    matched_predictions = {}

    def assign(known_index: int, visited: set[int]) -> bool:
        for predicted_index in edges[known_index]:
            if predicted_index in visited:
                continue
            visited.add(predicted_index)
            previous = matched_predictions.get(predicted_index)
            if previous is None or assign(previous, visited):
                matched_predictions[predicted_index] = known_index
                return True
        return False

    for index in range(len(expected)):
        assign(index, set())
    pairs = [
        {
            "known_index": known_index,
            "known_id": expected[known_index].get("id"),
            "predicted_index": predicted_index,
            "category": expected[known_index]["category"],
            "known_seconds": expected[known_index]["seconds"],
            "predicted_seconds": predicted[predicted_index]["seconds"],
            "absolute_error_seconds": abs(expected[known_index]["seconds"] - predicted[predicted_index]["seconds"]),
        }
        for predicted_index, known_index in sorted(matched_predictions.items(), key=lambda pair: pair[1])
    ]
    return {"matched_defects": len(pairs), "known_defects": len(expected), "predicted_defects": len(predicted), "unmatched_known_defects": len(expected) - len(pairs), "unmatched_predicted_defects": len(predicted) - len(pairs), "matches": pairs}


def request_once(endpoint: str, clip: dict, source: bytes) -> dict:
    """One multipart upload, with no automatic retry or redirect replay."""
    started = time.perf_counter()
    receipt = {"attempt": 1, "retry_count": 0}
    try:
        with httpx.Client(
            verify=ssl.create_default_context(cafile=certifi.where()),
            timeout=httpx.Timeout(90.0),
            follow_redirects=False,
        ) as client:
            response = client.post(
                endpoint,
                # Reference labels, reasons and evidence frames are never sent.
                data={"prompt": clip["prompt"], "model": clip["model"]},
                files={"video": (clip["id"] + ".mp4", source, "video/mp4")},
            )
            receipt["http_status"] = response.status_code
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


def assess_clip(clip: dict, receipt: dict) -> dict:
    result = {"verified_response": False, "matched_defects": 0, "known_defects": len(clip["known_defects"])}
    response = receipt.get("response")
    if receipt.get("http_status") != 200 or not isinstance(response, dict):
        return result
    analysis = response.get("analysis")
    defects = response.get("defects")
    if not isinstance(analysis, dict) or not isinstance(defects, list):
        return result
    invalid_defects = sum(
        not isinstance(defect, dict) or defect.get("category") not in CATEGORIES
        or not finite_number(defect.get("seconds")) or not 0 <= defect.get("seconds", -1) <= clip["duration_seconds"]
        or not isinstance(defect.get("timecode"), str) or not re.fullmatch(r"\d{2}:[0-5]\d", defect.get("timecode", ""))
        or not isinstance(defect.get("reason"), str) or not defect["reason"].strip()
        for defect in defects
    )
    model_calls = analysis.get("actual_model_calls")
    native_calls = response.get("model_calls_this_request")
    if isinstance(native_calls, bool) or not isinstance(native_calls, int) or native_calls < 0:
        native_calls = None
    reuse = response.get("reused_stored_review") is True
    result.update(
        source_sha256_matches=response.get("source_sha256") == clip["sha256"],
        reported_sampling_fps=analysis.get("sampling_fps"),
        reported_original_review_model_calls=model_calls,
        model_calls_for_this_request=native_calls,
        reused_stored_review=reuse,
        feedback_recorded=response.get("feedback_recorded") is True,
        feedback_created=response.get("feedback_created") is True,
        invalid_defect_count=invalid_defects,
        risk_before=response.get("risk_before"),
        risk_after=response.get("risk_after"),
    )
    result["verified_response"] = bool(
        result["source_sha256_matches"] and invalid_defects == 0
        and analysis.get("sampling_fps") == 2 and analysis.get("backend") == "vertex"
        and not isinstance(model_calls, bool) and isinstance(model_calls, int) and model_calls >= 2
        and native_calls is not None
        and isinstance(response.get("pass_bool"), bool)
        and result["feedback_recorded"]
    )
    if result["verified_response"]:
        result.update(match_defects(clip["known_defects"], defects))
    return result


def summarize(rows: list[dict]) -> dict:
    matched = sum(row["checks"]["matched_defects"] for row in rows)
    verified = sum(row["checks"]["verified_response"] for row in rows)
    calls = [row["checks"].get("model_calls_for_this_request") for row in rows]
    return {
        "required_clips": 3,
        "uploaded_clips": len(rows),
        "total_http_attempts": len(rows),
        "retries": 0,
        "verified_responses": verified,
        "matched_defects": matched,
        "minimum_matched_defects": 2,
        "tolerance_seconds": 2,
        "one_to_one": True,
        "V8_pass": len(rows) == 3 and verified == 3 and matched >= 2,
        "reported_model_calls_for_this_batch": sum(value for value in calls if isinstance(value, int) and not isinstance(value, bool)),
        "model_call_count_complete": len(rows) == 3 and all(isinstance(value, int) and not isinstance(value, bool) for value in calls),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "postcheck_live.json")
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "postcheck_live.txt")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        parser.error("Use an HTTPS service base URL without credentials, path, query or fragment")
    if args.report.exists() or args.log.exists():
        parser.error("Receipt files already exist; choose explicit new filenames for a separately authorized batch")
    reference_bytes = args.reference.read_bytes()
    reference = json.loads(reference_bytes)
    clips = validate_reference(reference)
    sources = load_source_bytes(clips)
    endpoint = args.url.rstrip("/") + "/postcheck"
    report = {
        "check": "V8 real owner-clip postcheck receipts",
        "endpoint": endpoint,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "reference_frozen_at_utc": reference["frozen_at_utc"],
        "label_provenance": reference["label_provenance"],
        "matching_rule": "maximum-cardinality one-to-one matching; exact category and absolute seconds within inclusive +/-2; at least2 matches across exactly3 verified clips",
        "upload_rule": "exactly one request per clip; no retries on any status or timeout; no reference defect labels, reasons or evidence sent to model",
        "rows": [],
        "complete": False,
    }
    save_report(args.report, report)
    append_log(args.log, {key: report[key] for key in ("check", "reference_sha256", "reference_frozen_at_utc", "matching_rule", "upload_rule")})
    try:
        for clip, source in zip(clips, sources):
            receipt = request_once(endpoint, clip, source)
            row = {
                "clip_id": clip["id"],
                "source_sha256": clip["sha256"],
                "source_bytes": len(source),
                "duration_seconds": clip["duration_seconds"],
                "neutral_prompt_sent": clip["prompt"],
                "model_label_sent": clip["model"],
                "known_defects": [{key: value for key, value in defect.items() if key != "evidence_frames"} for defect in clip["known_defects"]],
                "attempt": receipt,
                "checks": assess_clip(clip, receipt),
            }
            report["rows"].append(row)
            report["summary"] = summarize(report["rows"])
            save_report(args.report, report)
            append_log(args.log, row)
            print(json.dumps({"clip_id": row["clip_id"], "http_status": receipt.get("http_status"), "elapsed_seconds": receipt["elapsed_seconds"], **row["checks"]}, allow_nan=False), flush=True)
    except KeyboardInterrupt:
        report["interrupted"] = True
        report["summary"] = summarize(report["rows"])
        save_report(args.report, report)
        return 130
    report["complete"] = True
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = summarize(report["rows"])
    save_report(args.report, report)
    append_log(args.log, {"summary": report["summary"]})
    print(json.dumps(report["summary"], allow_nan=False), flush=True)
    return int(not report["summary"]["V8_pass"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as problem:
        print(json.dumps({"verification_error_type": type(problem).__name__, "complete": False}), file=sys.stderr)
        raise SystemExit(2)
