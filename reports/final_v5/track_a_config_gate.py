"""One-shot config-only admission cap deployment, bound to the unchanged image.

No model, build, runtime-source, IAM, secret, or Firestore mutation APIs are used.
The two admitted remote preview probes consume only saved cache responses.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import ssl
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from cloud_ops import CloudOperations, REGION
from cloud.preview import LIVE_LIMITED_MESSAGE
from cloud.sample_rewrites import load_sample_rewrites
from app import SAMPLES
import certifi

OUT = ROOT / "reports/final_v5"
BASELINE = "preflight-00025-lij"
DIGEST = "sha256:4bf0668ae549f7ab924f17e36105b621f1f25676aefb6e53e06154db4384e932"
TAG = "admission-v5-candidate"
ops = CloudOperations()
promotion_attempted = False


def save(name, value):
    (OUT / ("track_a_" + name + ".json")).write_text(ops.scrub(json.dumps(value, indent=2)) + "\n")


def native(resource="services", name="preflight"):
    return json.loads(ops.command("read native " + resource, ["gcloud", "run", resource,
        "describe", name, "--region", REGION, "--format=json"]))


def traffic(data):
    return [(row["revisionName"], row["percent"]) for row in data["status"]["traffic"] if row.get("percent")]


def env(revision):
    return {row["name"]: row.get("value") for row in revision["spec"]["containers"][0].get("env", [])}


def summary(service, revision):
    spec = revision["spec"]
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "revision": revision["metadata"]["name"], "traffic": service["status"]["traffic"],
        "url": service["status"]["url"],
        "image_digest": revision["status"]["imageDigest"].rsplit("@", 1)[-1],
        "allowed_env": {key: value for key, value in env(revision).items()
            if key.startswith("PREFLIGHT_") and "SESSION" not in key},
        "timeout_seconds": spec["timeoutSeconds"], "concurrency": spec["containerConcurrency"],
        "resources": spec["containers"][0]["resources"]}


def normalized_spec(revision):
    spec = deepcopy(revision["spec"])
    container = spec["containers"][0]
    container["image"] = revision["status"]["imageDigest"]
    container["env"] = sorted(container.get("env", []), key=lambda row: row["name"])
    return spec


def verify_mode(revision, daily):
    values = env(revision)
    assert revision["status"]["imageDigest"].rsplit("@", 1)[-1] == DIGEST
    assert values["PREFLIGHT_PREVIEW_ENABLED"] == "true"
    assert values["PREFLIGHT_PREVIEW_LIVE_ENABLED"] == "false"
    assert values["PREFLIGHT_PREVIEW_WARM_ENABLED"] == "false"
    assert values["PREFLIGHT_PREVIEW_DAILY_LIMIT"] == daily


def remote(base, path, payload=None):
    request = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
    try:
        with urlopen(request, timeout=55, context=ssl.create_default_context(cafile=certifi.where())) as response:
            return response.status, dict(response.headers), json.load(response)
    except HTTPError as error:
        return error.code, dict(error.headers), json.loads(error.read())


def main():
    global promotion_attempted
    tree = ET.parse(OUT / "track_a_tests.junit.xml")
    suites = list(tree.getroot().iter("testsuite"))
    tests = sum(int(row.attrib.get("tests", 0)) for row in suites)
    assert tests >= 90 and all(row.attrib.get("failures", "0") == row.attrib.get("errors", "0") == "0" for row in suites)
    source = json.loads((ROOT / "reports/preview_v4/source_match.json").read_text())
    assert source["revision_image_digest"] == DIGEST and source["runtime_matches_commit"]
    files = source["files"]
    for row in files:
        data = (ROOT / row["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["git_sha256"] == row["archive_sha256"]
    save("source_and_tests", {"unit_tests": tests, "failures": 0, "errors": 0,
        "runtime_files_unchanged": len(files), "source_receipt": "reports/preview_v4/source_match.json",
        "runtime_source_sha256": source["git_runtime_source_sha256"], "image_digest": DIGEST,
        "note": "No build and no runtime source edit; exact deployed image reused."})
    before = native()
    baseline = native("revisions", BASELINE)
    assert traffic(before) == [(BASELINE, 100)]
    assert before["status"]["latestReadyRevisionName"] == BASELINE
    verify_mode(baseline, "60")
    # Service templates retain the image tag and omit Cloud Run's default name;
    # immutable revision specs resolve that same image and name the container.
    template_spec = deepcopy(before["spec"]["template"]["spec"])
    template_spec["containers"][0]["image"] = baseline["status"]["imageDigest"]
    template_spec["containers"][0].setdefault("name", baseline["spec"]["containers"][0]["name"])
    assert template_spec == baseline["spec"], "Service template differs from baseline revision"
    save("before", summary(before, baseline))
    ops.command("create config-only no-traffic candidate", ["gcloud", "run", "services", "update", "preflight",
        "--region", REGION, "--image", baseline["status"]["imageDigest"],
        "--update-env-vars", "PREFLIGHT_PREVIEW_DAILY_LIMIT=500", "--no-traffic", "--tag", TAG,
        "--quiet", "--format=json"])
    prepared = native()
    name = prepared["status"]["latestReadyRevisionName"]
    candidate = native("revisions", name)
    assert name != BASELINE and traffic(prepared) == [(BASELINE, 100)]
    verify_mode(candidate, "500")
    old_spec, new_spec = normalized_spec(baseline), normalized_spec(candidate)
    expected = deepcopy(old_spec)
    next(row for row in expected["containers"][0]["env"] if row["name"] == "PREFLIGHT_PREVIEW_DAILY_LIMIT")["value"] = "500"
    assert new_spec == expected, "Candidate changed configuration beyond the daily cap"
    tag = next(row for row in prepared["status"]["traffic"] if row.get("tag") == TAG)
    assert tag["revisionName"] == name and not tag.get("percent")
    candidate_url = tag["url"]
    receipt = summary(prepared, candidate)
    receipt.update(candidate_url=candidate_url, only_daily_limit_changed=True,
        production_unchanged_before_gate=True, minute_limit=5,
        minute_limit_evidence="Unchanged cloud/store.py admit_preview default and 5/min unit test")
    save("candidate", receipt)
    gates = {"candidate_revision": name, "candidate_url": candidate_url, "image_digest": DIGEST,
        "unit_tests": tests, "runtime_source_unchanged": True, "preview_probes": [], "preflight_probes": []}
    code, headers, status = remote(candidate_url, "/api/status")
    gates["status"] = {"http_status": code, "preview": status.get("preview"), "preview_mode": status.get("preview_mode")}
    assert code == 200 and status["preview"] is True and status["preview_mode"] == "samples"
    original = "a spoon and a laptop"
    rewrite = load_sample_rewrites(SAMPLES)[original]["rewritten_prompt"]
    for prompt, variant in ((original, "original"), (rewrite, "rewrite")):
        code, headers, response = remote(candidate_url, "/preview", {"prompt": prompt, "variant": variant})
        image = response.pop("image_data_url", None)
        entry = {"prompt": prompt, "variant": variant, "http_status": code,
            "cache_header": next((v for k, v in headers.items() if k.lower() == "x-preview-cache"), None), **response}
        if image:
            image_bytes = base64.b64decode(image.split(",", 1)[1])
            entry.update(image_byte_size=len(image_bytes), image_sha256=hashlib.sha256(image_bytes).hexdigest())
        gates["preview_probes"].append(entry)
        save("gate_in_progress", gates)
        assert code == 200 and entry["cache_header"] == response["cache"] == "hit"
        assert response["model_calls"] == response["cost_usd"] == 0
    code, headers, response = remote(candidate_url, "/preview", {"prompt": "a bicycle on a quiet road", "variant": "original"})
    gates["typed_probe"] = {"http_status": code, **response}
    assert code == 503 and response["detail"] == LIVE_LIMITED_MESSAGE
    for prompt in ("a spoon and a laptop", "a cat and a dog"):
        code, headers, response = remote(candidate_url, "/preflight", {"prompt": prompt})
        entry = {key: response.get(key) for key in ("rewrite_source", "rewrite_model_calls_this_request", "p_fail", "p_fail_after")}
        entry.update(http_status=code, prompt=prompt)
        gates["preflight_probes"].append(entry)
        assert code == 200
    gates["pass"] = True
    save("gate", gates)
    # Re-read identities and traffic immediately before promotion.
    ready = native()
    assert traffic(ready) == [(BASELINE, 100)]
    assert next(row for row in ready["status"]["traffic"] if row.get("tag") == TAG)["revisionName"] == name
    verify_mode(native("revisions", name), "500")
    promotion_attempted = True
    ops.command("promote passed candidate", ["gcloud", "run", "services", "update-traffic", "preflight",
        "--region", REGION, "--to-revisions", name + "=100", "--quiet", "--format=json"])
    after = native()
    assert traffic(after) == [(name, 100)]
    verify_mode(native("revisions", name), "500")
    promotion = summary(after, candidate)
    promotion.update(gate_passed=True, traffic_verified=True, minute_limit=5, only_daily_limit_changed=True,
        model_calls_from_two_sample_probes=0)
    save("promotion", promotion)
    print(json.dumps({"pass": True, "revision": name, "traffic_percent": 100,
        "image_digest": DIGEST, "daily_limit": 500, "minute_limit": 5, "unit_tests": tests,
        "sample_cache_hits": 2, "sample_model_calls": 0, "typed_http_status": 503, "preflight_http_200": 2}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        failure = {"pass": False, "error_type": type(error).__name__, "message": str(error)[:500]}
        try:
            current = native()
            if promotion_attempted and traffic(current) != [(BASELINE, 100)]:
                # One bounded rollback only; never re-run a failed candidate gate.
                ops.command("restore baseline after post-promotion verification failure", [
                    "gcloud", "run", "services", "update-traffic", "preflight", "--region", REGION,
                    "--to-revisions", BASELINE + "=100", "--quiet", "--format=json"])
                current = native()
                failure["rollback_attempted"] = True
            failure["traffic"] = current["status"]["traffic"]
            failure["baseline_retained_at_100"] = traffic(current) == [(BASELINE, 100)]
        except Exception as inspection_error:
            failure["traffic_inspection_error"] = type(inspection_error).__name__
        save("failure", failure)
        print(ops.scrub(json.dumps(failure)))
        raise SystemExit(1)
