#!/usr/bin/env python3
"""Build a no-traffic v4 revision; promote only after saved numerical gates pass."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cloud_ops import CloudOperations, REGION
from release_cloud import build

REPORTS = ROOT / "reports/preview_v4"
TAG = "preview-v4-candidate"


def save(name, data):
    (REPORTS / name).write_text(json.dumps(data, indent=2) + "\n")


def native(ops):
    return json.loads(ops.command("read service", ["gcloud", "run", "services", "describe", "preflight", "--region", REGION, "--format=json"]))


def safe_service(data):
    spec = data["spec"]["template"]["spec"]
    env = {entry["name"]:entry.get("value") for entry in spec["containers"][0].get("env", [])}
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "url": data["status"]["url"],
            "revision": data["status"]["latestReadyRevisionName"], "traffic": data["status"]["traffic"],
            "timeout_seconds": spec["timeoutSeconds"], "concurrency": spec["containerConcurrency"],
            "resources": spec["containers"][0]["resources"],
            "allowed_env": {key:value for key,value in env.items() if key.startswith("PREFLIGHT_") and "SESSION" not in key}}


def validate_promotion_records(gate, candidate, provenance, revision):
    if not all(gate.get(key) is True for key in ("V_A", "V_B", "V_D", "V_E", "V_F")):
        raise RuntimeError("Required candidate gates are not all passing; production unchanged")
    if candidate.get("live_arm") and gate.get("V_C") is not True:
        raise RuntimeError("Live UI gate did not pass; samples-only candidate required")
    env = {entry["name"]:entry.get("value") for entry in revision["spec"]["containers"][0].get("env", [])}
    if candidate["allowed_env"].get("PREFLIGHT_PREVIEW_WARM_ENABLED") != "false" or env.get("PREFLIGHT_PREVIEW_WARM_ENABLED") != "false":
        raise RuntimeError("Warming must be disabled in saved and native candidate configuration")
    if env.get("PREFLIGHT_PREVIEW_ENABLED") != "true" or (env.get("PREFLIGHT_PREVIEW_LIVE_ENABLED") == "true") != bool(candidate.get("live_arm")):
        raise RuntimeError("Native preview mode differs from the gated candidate")
    if not provenance.get("pass") or provenance.get("commit") != gate.get("production_commit"):
        raise RuntimeError("Gate source commit lacks passing native provenance")
    for key, gate_key in (("revision", "candidate_revision"), ("build_id", "build_id")):
        if candidate.get(key) != gate.get(gate_key) or candidate.get(key) != provenance.get(key):
            raise RuntimeError("Gate revision or build identity differs from the candidate")
    runtime_hash = candidate.get("runtime_source_sha256")
    if not runtime_hash or any(value != runtime_hash for value in (gate.get("runtime_source_sha256"),
            provenance.get("git_runtime_source_sha256"), provenance.get("cloud_build_runtime_source_sha256"))):
        raise RuntimeError("Gate runtime source hashes do not match")
    native_digest = str(revision.get("status", {}).get("imageDigest", "")).rsplit("@", 1)[-1]
    if revision.get("metadata", {}).get("name") != candidate["revision"] or native_digest != provenance.get("revision_image_digest"):
        raise RuntimeError("Native candidate revision or image digest differs from provenance")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("candidate", "configure", "promote", "inspect"))
    parser.add_argument("--arm", choices=("P1", "P2", "P3"), default="P2")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--warm", action="store_true", help="Allow only sample misses for the bounded warming pass")
    args = parser.parse_args()
    ops = CloudOperations()
    REPORTS.mkdir(exist_ok=True)
    before = native(ops)
    if args.action in ("candidate", "configure"):
        primary = [r for r in before["status"]["traffic"] if r.get("percent", 0)]
        if len(primary) != 1 or primary[0].get("revisionName") != "preflight-00021-sus" or primary[0]["percent"] != 100:
            raise RuntimeError("Production baseline changed; candidate was not built")
        if args.live:
            decision = json.loads((REPORTS / "probe_decision.json").read_text())
            if decision.get("selected_arm") != args.arm or not decision.get("live_generation_allowed"):
                raise RuntimeError("Live arm has no passing preregistered receipt")
        if args.action == "candidate":
            old_path = ROOT / "reports/cloud_build.json"
            previous = old_path.read_bytes() if old_path.exists() else None
            try:
                image = build(ops)
                build_receipt = json.loads(old_path.read_text())
                save("build.json", build_receipt)
            finally:
                if previous is not None:
                    old_path.write_bytes(previous)
        else:
            prior = json.loads((REPORTS / "candidate.json").read_text())
            save("candidate_before_configure_" + prior["revision"] + ".json", prior)
            if before["status"]["latestReadyRevisionName"] != prior["revision"]:
                raise RuntimeError("Latest revision differs from the registered candidate")
            image = before["spec"]["template"]["spec"]["containers"][0]["image"]
            build_receipt = json.loads((REPORTS / "build.json").read_text())
        env = {"PREFLIGHT_PREVIEW_ENABLED": "true", "PREFLIGHT_PREVIEW_LIVE_ENABLED": str(args.live).lower(),
               "PREFLIGHT_PREVIEW_WARM_ENABLED": str(args.warm).lower(),
               "PREFLIGHT_IMAGE_LIVE_ARM": args.arm, "PREFLIGHT_IMAGE_LOCATION": "global"}
        ops.command("create no-traffic preview revision", ["gcloud", "run", "services", "update", "preflight",
            "--region", REGION, "--image", image, "--update-env-vars", ",".join(f"{k}={v}" for k,v in env.items()),
            "--no-traffic", "--tag", TAG, "--quiet", "--format=json"])
        after = native(ops)
        receipt = safe_service(after)
        receipt["candidate_url"] = next(row["url"] for row in receipt["traffic"] if row.get("tag") == TAG)
        receipt["build_id"] = build_receipt["build_id"]
        receipt["runtime_source_sha256"] = build_receipt["input_sha256"]
        receipt["live_arm"] = args.arm if args.live else None
        receipt["no_primary_traffic_moved"] = [r for r in receipt["traffic"] if r.get("percent", 0)] == primary
        save("candidate.json", receipt)
        print(json.dumps(receipt))
    elif args.action == "promote":
        gate = json.loads((REPORTS / "gate_decision.json").read_text())
        candidate = json.loads((REPORTS / "candidate.json").read_text())
        provenance = json.loads((REPORTS / "source_match.json").read_text())
        revision = candidate["revision"]
        native_revision = json.loads(ops.command("inspect exact candidate revision", ["gcloud", "run", "revisions", "describe", revision, "--region", REGION, "--format=json"]))
        validate_promotion_records(gate, candidate, provenance, native_revision)
        tagged = next((r for r in before["status"]["traffic"] if r.get("tag") == TAG), {})
        if tagged.get("revisionName") != revision:
            raise RuntimeError("Candidate tag identity changed; production unchanged")
        primary = [row for row in before["status"]["traffic"] if row.get("percent", 0)]
        if len(primary) != 1 or primary[0].get("revisionName") != "preflight-00021-sus" or primary[0]["percent"] != 100:
            raise RuntimeError("Production baseline changed since candidate preparation")
        ops.command("promote passed candidate", ["gcloud", "run", "services", "update-traffic", "preflight",
            "--region", REGION, "--to-revisions", revision + "=100", "--quiet", "--format=json"])
        receipt = safe_service(native(ops))
        receipt["passed_revision"] = revision
        receipt["production_commit"] = gate["production_commit"]
        receipt["traffic_verified"] = any(r.get("revisionName") == revision and r.get("percent") == 100 for r in receipt["traffic"])
        save("promotion.json", receipt)
        print(json.dumps(receipt))
    else:
        print(json.dumps(safe_service(before)))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"error_type":type(error).__name__, "message":str(error)[:300]}), file=sys.stderr)
        raise SystemExit(1)
