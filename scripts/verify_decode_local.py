#!/usr/bin/env python3
"""Reproduce one local owner-clip preparation and validate its temporary outputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloud.postcheck import prepare_media


ROOT = Path(__file__).resolve().parents[1]


def decode_check(arguments: list[str]) -> int:
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-xerror", "-threads", "1", *arguments, "-progress", "pipe:1", "-nostats", "-f", "null", "-"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=8, check=False,
    )
    if result.returncode != 0:
        raise ValueError("Prepared media failed independent decoding")
    frame_counts = [int(line.split("=", 1)[1].strip()) for line in result.stdout.decode().splitlines() if line.startswith("frame=")]
    if not frame_counts:
        raise ValueError("The independent decoder did not report completed frames")
    return frame_counts[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=ROOT / "reports" / "postcheck_canary_reference.json")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "postcheck_decode_optimized.json")
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "postcheck_decode_optimized.txt")
    args = parser.parse_args()
    if args.report.exists() or args.log.exists():
        parser.error("Local decode receipts already exist; preserve them and use explicit new filenames")
    reference_bytes = args.reference.read_bytes()
    reference = json.loads(reference_bytes)
    source = Path(reference["cached_absolute_path"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != reference["sha256"]:
        raise ValueError("Frozen source identity changed")
    started = time.perf_counter()
    prepared = prepare_media(source)
    elapsed = time.perf_counter() - started
    if prepared.source_sha256 != reference["sha256"]:
        raise ValueError("Prepared source identity differs from the frozen source")
    if len(prepared.frames) != 10 or [frame.seconds for frame in prepared.frames] != [index / 2 for index in range(10)]:
        raise ValueError("The frozen owner clip did not produce the expected ten 2-fps frames")
    validation_started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="postcheck-decode-proof-") as directory:
        work = Path(directory)
        normalized = work / "review.mp4"
        normalized.write_bytes(prepared.video_bytes)
        for index, frame in enumerate(prepared.frames):
            if not frame.image_bytes.startswith(bytes.fromhex("ffd8")) or not frame.image_bytes.endswith(bytes.fromhex("ffd9")):
                raise ValueError("A prepared frame lacks a complete JPEG signature")
            (work / f"frame_{index:03d}.jpg").write_bytes(frame.image_bytes)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_name,width,height,avg_frame_rate,nb_frames,pix_fmt", "-of", "json", str(normalized)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=4, check=False,
        )
        if probe.returncode != 0:
            raise ValueError("Normalized MP4 metadata could not be verified")
        metadata = json.loads(probe.stdout)
        video_decoded = decode_check(["-i", str(normalized)])
        images_decoded = decode_check(["-framerate", "2", "-start_number", "0", "-i", str(work / "frame_%03d.jpg")])
        if video_decoded <= 0 or images_decoded != 10:
            raise ValueError("Not every prepared frame was independently decoded")
    validation_elapsed = time.perf_counter() - validation_started
    receipt = {
        "check": "optimized local preparation of frozen resident owner01; no model or API calls",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "reproduction_command": "../.preflight-cloud-venv/bin/python scripts/verify_decode_local.py --reference reports/postcheck_canary_reference.json",
        "working_directory": str(ROOT),
        "method": "Current prepare_media: one ffprobe, source hash, one ffmpeg decode; shared512scale and split into15fpsMP4 and2fpsJPEG outputs; decode/filter/encoderthreads1; combinedffmpeg timeout18s",
        "timing_scope": "prepare_elapsed_seconds covers prepare_media only, including its probe/hash/decode/output reads; separate validation time is excluded",
        "prepare_elapsed_seconds": round(elapsed, 6),
        "validation_elapsed_seconds": round(validation_elapsed, 6),
        "source_sha256": prepared.source_sha256,
        "source_hash_matches_frozen_reference": True,
        "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "runtime_module_sha256": hashlib.sha256((ROOT / "cloud" / "postcheck.py").read_bytes()).hexdigest(),
        "source_bytes": prepared.metadata.source_bytes,
        "source_duration_seconds": prepared.metadata.duration,
        "source_resolution": {"width": prepared.metadata.width, "height": prepared.metadata.height},
        "normalized_video_bytes": len(prepared.video_bytes),
        "normalized_video_sha256": hashlib.sha256(prepared.video_bytes).hexdigest(),
        "normalized_metadata": metadata,
        "independently_decoded_video_frames": video_decoded,
        "sampling_fps": 2,
        "frame_count": len(prepared.frames),
        "independently_decoded_jpegs": images_decoded,
        "frames": [{"index": index, "seconds": frame.seconds, "jpeg_bytes": len(frame.image_bytes), "sha256": hashlib.sha256(frame.image_bytes).hexdigest(), "jpeg_signature_valid": True} for index, frame in enumerate(prepared.frames)],
        "temporary_media_removed": True,
        "model_calls": 0,
        "api_calls": 0,
        "passed": True,
    }
    encoded = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    for path in (args.report, args.log):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded)
    print(json.dumps({key: receipt[key] for key in ("prepare_elapsed_seconds", "validation_elapsed_seconds", "source_sha256", "normalized_video_bytes", "frame_count", "independently_decoded_jpegs", "model_calls", "api_calls", "passed")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as problem:
        print(json.dumps({"verification_error_type": type(problem).__name__, "complete": False}), file=sys.stderr)
        raise SystemExit(2)
