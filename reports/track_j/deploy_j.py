#!/usr/bin/env python3
"""One-shot Track J release; importing this file performs no operations.

Runtime source is frozen to an explicit commit. All cloud metadata stays in
memory; public receipts contain hashes, revision/build identities and approved
settings only. Five HTTP probes are attempted once each, without retries.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import certifi

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/track_j"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from cloud_ops import BUILD_ACCOUNT, CloudOperations, REGION
from cloud.preview import LIVE_LIMITED_MESSAGE
import verify_preview_source_v4 as source

BASELINE = "preflight-00027-pit"
SOURCE_BASE = "8d155f0c0f15db2513df294cb09f7999c57e5dff"
OLD_IMAGE_DIGEST = "sha256:4bf0668ae549f7ab924f17e36105b621f1f25676aefb6e53e06154db4384e932"
CANDIDATE_TAG = "track-j-candidate"
SOURCE_TAG = "aibc-2026-submission-v4"
REPOSITORY = "https://github.com/testofschool/preflight.git"
KST = ZoneInfo("Asia/Seoul")
DEADLINE = datetime(2026, 10, 18, 20, 30, tzinfo=KST)
PRIOR_TAGS = {
    "aibc-2026-submission": "dd12f279e364cbd217a4178b51c1d270cacebbdd",
    "aibc-2026-submission-v2": "bdcdecdf6db6b0c2bebea8a35ed350de5f005940",
    "aibc-2026-submission-v3": "d638c0690cb17d60316922eb30a14f150fe7c23c",
}
SAMPLE = "a spoon and a laptop"
TYPED = "a dog catching a frisbee on a beach at sunset"
TEST_NAME = "test_total_request_limit_accepts_3000_and_rejects_invalid_settings"
VOLATILE_ANNOTATIONS = {
    "run.googleapis.com/client-name", "run.googleapis.com/client-version",
    "run.googleapis.com/operation-id", "run.googleapis.com/urls",
    "run.googleapis.com/ingress-status", "serving.knative.dev/creator",
    "serving.knative.dev/lastModifier",
}


class ReleaseError(RuntimeError):
    """Only fixed local descriptions are allowed in failure receipts."""


def now():
    return datetime.now(KST)


def guard(step, minimum_seconds=0):
    remaining = (DEADLINE - now()).total_seconds()
    if remaining <= minimum_seconds:
        raise ReleaseError(step + ": hard deadline reached or insufficient time remains")
    return remaining


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


class SafeOperations(CloudOperations):
    def command(self, label, arguments, *, data=None, timeout=120):
        remaining = guard(label)
        try:
            result = subprocess.run(arguments, input=data, capture_output=True,
                text=True, cwd=ROOT, timeout=min(timeout, max(0.1, remaining)),
                env={**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"})
        except subprocess.TimeoutExpired:
            raise ReleaseError(label + ": command timed out; raw diagnostics not retained") from None
        if result.returncode:
            raise ReleaseError(label + ": command failed; raw diagnostics not retained")
        if getattr(self, "key", "") and self.key in result.stdout + result.stderr:
            raise ReleaseError(label + ": credential guard rejected captured output")
        return result.stdout

    def binary_command(self, label, arguments, *, timeout=120):
        remaining = guard(label)
        try:
            result = subprocess.run(arguments, capture_output=True, cwd=ROOT,
                timeout=min(timeout, max(0.1, remaining)),
                env={**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"})
        except subprocess.TimeoutExpired:
            raise ReleaseError(label + ": command timed out; raw diagnostics not retained") from None
        if result.returncode:
            raise ReleaseError(label + ": command failed; raw diagnostics not retained")
        credential = getattr(self, "key", "").encode()
        if credential and credential in result.stdout + result.stderr:
            raise ReleaseError(label + ": credential guard rejected captured output")
        return result.stdout


def save(ops, name, value):
    value = {"recorded_at_kst": now().isoformat(), **value}
    payload = ops.scrub(json.dumps(value, indent=2, sort_keys=True)) + "\n"
    temporary = OUT / (name + ".tmp")
    temporary.write_text(payload)
    temporary.replace(OUT / name)


def git(ops, *arguments):
    return ops.command("Git " + arguments[0], ["git", "-C", str(ROOT),
        "-c", "core.hooksPath=/dev/null", "-c", "tag.gpgSign=false", *arguments])


def native(ops, resource="services", name="preflight"):
    return json.loads(ops.command("read native " + resource,
        ["gcloud", "run", resource, "describe", name, "--region", REGION, "--format=json"]))


def primary(service):
    return [(row["revisionName"], row["percent"])
        for row in service["status"]["traffic"] if row.get("percent")]


def values(revision):
    return {row["name"]: row.get("value") for row in revision["spec"]["containers"][0].get("env", [])}


def normalized_spec(revision):
    spec = deepcopy(revision["spec"])
    spec["containers"][0]["image"] = revision["status"]["imageDigest"]
    spec["containers"][0]["env"] = sorted(spec["containers"][0].get("env", []), key=lambda row: row["name"])
    return spec


def settings_annotations(metadata):
    return {key: value for key, value in metadata.get("annotations", {}).items()
        if key not in VOLATILE_ANNOTATIONS}


def spec_hash(spec):
    return sha(json.dumps(spec, sort_keys=True, separators=(",", ":")).encode())


def safe_summary(service, revision):
    spec = revision["spec"]
    return {"revision": revision["metadata"]["name"],
        "traffic": [{"revision": row.get("revisionName"), "percent": row.get("percent", 0),
                     "tag": row.get("tag")} for row in service["status"]["traffic"]],
        "image_digest": source.image_digest(revision["status"]["imageDigest"]),
        "allowed_env": {key: value for key, value in values(revision).items()
            if key.startswith("PREFLIGHT_") and "SESSION" not in key},
        "timeout_seconds": spec["timeoutSeconds"],
        "concurrency": spec["containerConcurrency"],
        "resources": spec["containers"][0]["resources"],
        "normalized_spec_sha256": spec_hash(normalized_spec(revision)),
        "runtime_annotations": settings_annotations(revision.get("metadata", {}))}


def verify_full_suite(path, commit, files):
    path = path.resolve()
    require(path.is_relative_to(ROOT), "Full-suite XML must be inside the repository")
    require(path.is_file(), "Full-suite XML is absent")
    root = ET.parse(path).getroot()
    suites = list(root.iter("testsuite"))
    require(bool(suites), "Full-suite XML has no test suites")
    counts = {name: sum(int(row.attrib.get(name, "0")) for row in suites)
              for name in ("tests", "failures", "errors", "skipped")}
    cases = list(root.iter("testcase"))
    # pytest-subtests includes successful subtests in suite totals without
    # adding separate testcase rows. Preserve both counts rather than treating
    # that native representation as a failed or incomplete run.
    require(counts["tests"] >= len(cases) >= 94, "Full-suite XML has an incomplete case count")
    require(counts["failures"] == counts["errors"] == counts["skipped"] == 0, "Full unit suite did not pass")
    require(not list(root.iter("failure")) and not list(root.iter("error")) and not list(root.iter("skipped")),
            "Full-suite XML includes an unsuccessful case")
    matching = [case for case in cases if case.get("name") == TEST_NAME]
    require(len(matching) == 1 and not any(list(matching[0].iter(kind)) for kind in ("failure", "error", "skipped")),
            "The adjusted boundary test did not pass")
    require(path.stat().st_mtime >= max((ROOT / "cloud/store.py").stat().st_mtime,
                                      (ROOT / "tests/test_store.py").stat().st_mtime),
            "Full-suite XML predates the source or boundary test")
    return {**counts, "testcase_rows": len(cases), "additional_subtest_count": counts["tests"] - len(cases),
        "pass": True, "xml_sha256": sha(path.read_bytes()),
        "source_commit": commit, "store_sha256": sha(files["cloud/store.py"]),
        "adjusted_boundary_test": TEST_NAME, "xml_path": str(path.relative_to(ROOT))}


def source_preconditions(ops, commit):
    require(git(ops, "rev-parse", "HEAD").strip() == commit, "Local HEAD differs from the source commit")
    resolved, files = source.committed_inputs(commit)
    _, baseline_files = source.committed_inputs(SOURCE_BASE)
    require(resolved == commit and len(files) == len(baseline_files) == 25, "Runtime manifest must contain exactly 25 files")
    require(files.keys() == baseline_files.keys(), "Runtime manifest paths changed")
    changed = [path for path in files if files[path] != baseline_files[path]]
    require(changed == ["cloud/store.py"], "Runtime diff includes changes beyond the single code ceiling")
    old = b"        if not 1 <= total_limit <= 1000:\n"
    new = b"        if not 1 <= total_limit <= 3000:\n"
    require(baseline_files["cloud/store.py"].count(old) == 1 and
            files["cloud/store.py"] == baseline_files["cloud/store.py"].replace(old, new, 1),
            "The store diff is not the exact one-line ceiling change")
    old_provenance = json.loads((ROOT / "reports/preview_v4/source_match.json").read_text())
    require(old_provenance.get("pass") is True and old_provenance["revision_image_digest"] == OLD_IMAGE_DIGEST,
            "Prior native runtime provenance is unavailable")
    recorded = {row["path"]: row for row in old_provenance["files"]}
    require(recorded.keys() == files.keys() and all(
        sha(baseline_files[path]) == recorded[path]["git_sha256"] == recorded[path]["archive_sha256"]
        for path in files), "H/I runtime inputs do not match the prior native provenance")
    require(all((ROOT / path).read_bytes() == payload for path, payload in files.items()),
            "Working runtime files differ from the committed build inputs")
    changed_code = git(ops, "diff", "--name-only", SOURCE_BASE, commit, "--", "*.py").splitlines()
    require(set(changed_code) <= {"cloud/store.py", "tests/test_store.py"} and "tests/test_store.py" in changed_code,
            "Source commit contains an additional Python code change")
    tests_bytes = ops.command("read committed boundary test", ["git", "-C", str(ROOT), "show", commit + ":tests/test_store.py"]).encode()
    require(tests_bytes == (ROOT / "tests/test_store.py").read_bytes(), "Working unit test differs from the source commit")
    require(TEST_NAME.encode() in tests_bytes and b'"3001"' in tests_bytes, "The committed boundary test is missing")
    return files


def build_image(ops, commit, files, build_id):
    runtime_hash = source.runtime_digest(files)
    used_existing_build = build_id is not None
    if build_id is None:
        guard("submit new image build", 300)
        with tempfile.TemporaryDirectory(prefix="preflight-track-j-build-", dir="/private/tmp") as folder:
            snapshot = Path(folder)
            for path, payload in files.items():
                destination = snapshot / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(payload)
            config = ops.command("read committed build configuration",
                ["git", "-C", str(ROOT), "show", commit + ":cloudbuild.yaml"])
            require(config == ops.command("read baseline build configuration",
                ["git", "-C", str(ROOT), "show", SOURCE_BASE + ":cloudbuild.yaml"]),
                "Build configuration changed")
            (snapshot / "cloudbuild.yaml").write_text(config)
            image = f"{REGION}-docker.pkg.dev/{ops.project}/preflight/app:{runtime_hash[:20]}"
            data = json.loads(ops.command("submit frozen image build", ["gcloud", "builds", "submit", str(snapshot),
                "--config", str(snapshot / "cloudbuild.yaml"), "--substitutions", "_IMAGE=" + image,
                "--region", REGION, "--service-account",
                f"projects/{ops.project}/serviceAccounts/{BUILD_ACCOUNT}@{ops.project}.iam.gserviceaccount.com",
                "--async", "--format=json", "--quiet"]))
            build_id = data["id"]
    require(bool(re.fullmatch(r"[0-9a-fA-F-]{36}", build_id)), "Native build ID has an invalid format")
    while True:
        data = json.loads(ops.command("read frozen image build", ["gcloud", "builds", "describe", build_id,
            "--region", REGION, "--format=json"]))
        save(ops, "build.json", {"build_id": build_id, "source_commit": commit,
            "runtime_source_sha256": runtime_hash, "status": data.get("status"),
            "used_existing_build": used_existing_build})
        require(data.get("id") == build_id, "Native build identity changed")
        status = data.get("status")
        if status == "SUCCESS":
            break
        require(status in {"QUEUED", "PENDING", "WORKING"}, "Native image build did not succeed")
        remaining = guard("wait for image build")
        time.sleep(min(10, remaining))
    storage = data.get("sourceProvenance", {}).get("resolvedStorageSource", {})
    bucket, object_name, generation = (storage.get(key) for key in ("bucket", "object", "generation"))
    require(isinstance(bucket, str) and bucket and isinstance(object_name, str) and object_name
        and str(generation).isdigit(), "Native generation-pinned source archive is unavailable")
    with tempfile.TemporaryDirectory(prefix="preflight-track-j-provenance-", dir="/private/tmp") as folder:
        archive = Path(folder) / "source.tgz"
        ops.command("download generation-pinned native source", ["gcloud", "storage", "cp",
            "gs://" + bucket + "/" + object_name + "#" + str(generation), str(archive), "--quiet"])
        archived = source.archived_inputs(archive)
        archive_sha = source.file_sha256(archive)
    require(archived == files and source.runtime_digest(archived) == runtime_hash,
            "Native build source differs from the exact source commit")
    images = data.get("results", {}).get("images", [])
    require(len(images) == 1, "Native build must have exactly one image result")
    image_name, digest = images[0].get("name", ""), source.image_digest(images[0].get("digest"))
    repository = f"{REGION}-docker.pkg.dev/{ops.project}/preflight/app"
    require(image_name == repository or image_name.startswith(repository + ":") or image_name.startswith(repository + "@"),
            "Native image repository differs from this app")
    require(digest != OLD_IMAGE_DIGEST, "New source unexpectedly resolved to the old image")
    receipt = {"build_id": build_id, "source_commit": commit, "build_status": "SUCCESS",
        "git_runtime_source_sha256": runtime_hash, "cloud_build_runtime_source_sha256": source.runtime_digest(archived),
        "runtime_file_count": len(files), "native_provenance_archive_sha256": archive_sha,
        "source_generation": str(generation), "generation_pinned": True,
        "source_object_identity_sha256": sha((bucket + "/" + object_name).encode()),
        "build_image_digest": digest, "pass": True}
    save(ops, "build_source.json", receipt)
    return build_id, repository + "@" + digest, receipt


def verify_baseline(service, baseline):
    require(primary(service) == [(BASELINE, 100)], "Production no longer retains the required baseline at 100 percent")
    require(service["status"]["latestReadyRevisionName"] == BASELINE, "Service template has an unexpected ready revision")
    require(source.image_digest(baseline["status"]["imageDigest"]) == OLD_IMAGE_DIGEST, "Baseline image differs from native provenance")
    baseline_env = values(baseline)
    require(baseline_env.get("PREFLIGHT_TOTAL_REQUEST_LIMIT") == "1000", "Baseline cumulative limit differs")
    require(baseline_env.get("PREFLIGHT_PREVIEW_ENABLED") == "true" and
            baseline_env.get("PREFLIGHT_PREVIEW_LIVE_ENABLED") == "false" and
            baseline_env.get("PREFLIGHT_PREVIEW_WARM_ENABLED") == "false", "Baseline preview mode differs")
    require(baseline_env.get("PREFLIGHT_PREVIEW_DAILY_LIMIT") == "500", "Baseline preview daily allowance differs")
    template = deepcopy(service["spec"]["template"]["spec"])
    template["containers"][0]["image"] = baseline["status"]["imageDigest"]
    template["containers"][0].setdefault("name", baseline["spec"]["containers"][0]["name"])
    require(template == baseline["spec"], "Mutable service template differs from the immutable baseline")


def verify_candidate(candidate, baseline, image):
    expected = normalized_spec(baseline)
    expected["containers"][0]["image"] = image
    matches = [entry for entry in expected["containers"][0]["env"] if entry["name"] == "PREFLIGHT_TOTAL_REQUEST_LIMIT"]
    require(len(matches) == 1, "Baseline total limit is ambiguous")
    matches[0]["value"] = "3000"
    require(normalized_spec(candidate) == expected, "Candidate changed a setting beyond the image and total allowance")
    require(settings_annotations(candidate.get("metadata", {})) == settings_annotations(baseline.get("metadata", {})),
            "Candidate runtime annotation settings differ from the immutable baseline")


def read_allowance(ops, baseline, effective_limit):
    env = values(baseline)
    database = env["PREFLIGHT_FIRESTORE_DATABASE"]
    require(env.get("GOOGLE_CLOUD_PROJECT") == ops.project and database != "(default)", "Allowance read has an unexpected database")
    token = ops.command("obtain private read-only access credential", ["gcloud", "auth", "print-access-token"]).strip()
    request = Request("https://firestore.googleapis.com/v1/projects/" + ops.project + "/databases/" + database
        + "/documents/service_v1/global-budget", headers={"Authorization": "Bearer " + token})
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())), NoRedirect())
    try:
        with opener.open(request, timeout=min(30, guard("read allowance"))) as response:
            document = json.load(response)
    except Exception:
        raise ReleaseError("Read-only allowance lookup failed; private diagnostics not retained") from None
    fields = document.get("fields", {})
    try:
        used = int(fields["total_count"]["integerValue"])
        stored_limit = int(fields["total_request_limit"]["integerValue"])
    except (KeyError, TypeError, ValueError):
        raise ReleaseError("Read-only allowance response lacks integer counters") from None
    require(0 <= used <= effective_limit, "Read-only allowance contains an invalid count")
    return {"checked_at_kst": now().isoformat(), "used": used, "effective_limit": effective_limit,
        "remaining": effective_limit - used, "stored_last_admission_limit": stored_limit,
        "read_only": True}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def remote(base, path, payload=None):
    remaining = guard("single HTTP gate " + path)
    request = Request(base + path, data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"}, method="POST" if payload is not None else "GET")
    opener = build_opener(HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())), NoRedirect())
    try:
        with opener.open(request, timeout=min(55, remaining)) as response:
            return response.status, dict(response.headers), json.load(response)
    except HTTPError as error:
        try:
            return error.code, dict(error.headers), json.loads(error.read())
        except (ValueError, UnicodeError):
            raise ReleaseError("Single HTTP gate returned a non-JSON error response") from None
    except Exception:
        raise ReleaseError("Single HTTP gate failed; no retry attempted") from None


def run_gate(ops, url, revision, baseline):
    gate = {"revision": revision, "http_attempts": [], "pass": False,
        "allowance_before_gate": read_allowance(ops, baseline, 3000), "no_retries": True}
    save(ops, "gate_in_progress.json", gate)

    def probe(label, path, payload=None):
        # Save the attempt before touching the network so interruption cannot hide it.
        gate["http_attempts"].append({"probe": label, "path": path, "attempt": 1, "state": "started"})
        save(ops, "gate_in_progress.json", gate)
        status, headers, response = remote(url, path, payload)
        gate["http_attempts"][-1].update(state="finished", http_status=status)
        save(ops, "gate_in_progress.json", gate)
        return status, headers, response

    status, _, response = probe("status", "/api/status")
    gate["status"] = {"http_status": status, "preview_mode": response.get("preview_mode"), "preview": response.get("preview")}
    save(ops, "gate_in_progress.json", gate)
    require(status == 200 and response.get("preview_mode") == "samples", "Status gate failed")
    for label, prompt in (("sample_preflight", SAMPLE), ("typed_preflight", TYPED)):
        status, _, response = probe(label, "/preflight", {"prompt": prompt})
        gate[label] = {"http_status": status, "prompt": prompt, **{key: response.get(key)
            for key in ("rewrite_source", "rewrite_model_calls_this_request", "p_fail", "p_fail_after")}}
        save(ops, "gate_in_progress.json", gate)
        require(status == 200, label + " gate failed")
    status, headers, response = probe("sample_preview", "/preview", {"prompt": SAMPLE, "variant": "original"})
    cache_header = next((value for key, value in headers.items() if key.lower() == "x-preview-cache"), None)
    gate["sample_preview"] = {"http_status": status, "cache_header": cache_header, **{key: response.get(key)
        for key in ("cache", "model_calls", "cost_usd", "model", "generated_at", "metadata_label")}}
    image = response.get("image_data_url")
    if isinstance(image, str) and "," in image:
        try:
            payload = base64.b64decode(image.split(",", 1)[1], validate=True)
            gate["sample_preview"].update(image_bytes=len(payload), image_sha256=sha(payload))
        except (ValueError, TypeError):
            raise ReleaseError("Sample preview image encoding is invalid") from None
    save(ops, "gate_in_progress.json", gate)
    require(status == 200 and cache_header == response.get("cache") == "hit" and response.get("model_calls") == 0,
            "Sample preview is not a saved cache hit with zero model calls")
    status, _, response = probe("typed_preview", "/preview", {"prompt": TYPED, "variant": "original"})
    gate["typed_preview"] = {"http_status": status, "detail": response.get("detail")}
    save(ops, "gate_in_progress.json", gate)
    require(status == 503 and response.get("detail") == LIVE_LIMITED_MESSAGE, "Typed preview limited-copy gate failed")
    gate["allowance_after_gate"] = read_allowance(ops, baseline, 3000)
    require(gate["allowance_after_gate"]["stored_last_admission_limit"] == 3000,
            "Admitted candidate did not persist the 3000 allowance")
    require(gate["allowance_after_gate"]["used"] >= gate["allowance_before_gate"]["used"] + 2,
            "Allowance counter did not include the two admitted gates")
    require(len(gate["http_attempts"]) == 5, "Gate made an unexpected number of HTTP attempts")
    gate["observed_cumulative_counter_delta"] = gate["allowance_after_gate"]["used"] - gate["allowance_before_gate"]["used"]
    gate["pass"] = True
    save(ops, "gate.json", gate)
    return gate


def public_refs(ops):
    names = ["refs/heads/main"] + ["refs/tags/" + tag for tag in (*PRIOR_TAGS, SOURCE_TAG)]
    listing = git(ops, "ls-remote", REPOSITORY, *names, *[name + "^{}" for name in names if name.startswith("refs/tags/")])
    return dict((name, object_id) for object_id, name in (line.split("\t", 1) for line in listing.splitlines()))


def verify_prior_refs(refs):
    require(all(refs.get("refs/tags/" + name) == commit
        for name, commit in PRIOR_TAGS.items()), "An existing public source tag differs")


def anonymous_verify(ops, commit, runtime_hash, expected_tag_object):
    spec = importlib.util.spec_from_file_location("track_j_public_helpers", ROOT / "reports/final_v5/verify_public_package.py")
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)

    def anonymous_git(parts, cwd=None):
        remaining = guard("anonymous clone verification")
        try:
            result = subprocess.run(helpers.GIT + parts, cwd=cwd, env=helpers.ENVIRONMENT,
                capture_output=True, timeout=min(120, remaining))
        except (OSError, subprocess.TimeoutExpired):
            raise ReleaseError("Anonymous Git verification unavailable; diagnostics not retained") from None
        require(result.returncode == 0, "Anonymous Git verification failed; diagnostics not retained")
        return result.stdout

    # runtime_digest calls the helper's global git; give it the same deadline guard.
    helpers.git = lambda parts, step, cwd=None: anonymous_git(parts, cwd)
    with tempfile.TemporaryDirectory(prefix="preflight-track-j-anonymous-", dir="/private/tmp") as folder:
        clone = Path(folder) / "clone"
        anonymous_git(["clone", "--depth=1", "--single-branch", "--branch", SOURCE_TAG,
            "--no-checkout", REPOSITORY, str(clone)])
        cloned = anonymous_git(["rev-parse", "HEAD^{commit}"], clone).decode().strip()
        tag_object = anonymous_git(["rev-parse", "refs/tags/" + SOURCE_TAG], clone).decode().strip()
        require(anonymous_git(["cat-file", "-t", tag_object], clone).strip() == b"tag",
                "Anonymous source ref is not an annotated tag")
        count, digest = helpers.runtime_digest(clone, cloned)
        listing = anonymous_git(["ls-remote", REPOSITORY, "refs/heads/main",
            *["refs/tags/" + tag for tag in (*PRIOR_TAGS, SOURCE_TAG)],
            *["refs/tags/" + tag + "^{}" for tag in (*PRIOR_TAGS, SOURCE_TAG)]]).decode()
        refs = dict((name, object_id) for object_id, name in (line.split("\t", 1) for line in listing.splitlines()))
        verify_prior_refs(refs)
        require(cloned == commit and count == 25 and digest == runtime_hash, "Anonymous source/runtime identity differs")
        require(tag_object == expected_tag_object and refs.get("refs/tags/" + SOURCE_TAG) == expected_tag_object and
            refs.get("refs/tags/" + SOURCE_TAG + "^{}") == commit and refs.get("refs/heads/main") == commit,
            "Anonymous public main or annotated-tag identity differs")
    receipt = {"pass": True, "credentials_provided": False, "credential_helper": "empty",
        "global_config": "/dev/null", "system_config_disabled": True, "git_hooks": "disabled",
        "raw_diagnostics_saved": False, "cloned_source_commit": cloned,
        "annotated_tag_object": tag_object, "source_tag": SOURCE_TAG,
        "runtime_file_count": count, "runtime_source_sha256": digest,
        "all_prior_tag_commits_unchanged": True, "temporary_clone_removed": True}
    save(ops, "anonymous_clone.json", receipt)
    return receipt


def publish(ops, commit, runtime_hash):
    guard("publish source and annotated tag", 300)
    require(git(ops, "rev-parse", "HEAD").strip() == commit, "Local HEAD moved before publication")
    remote = git(ops, "remote", "get-url", "origin").strip()
    require(remote in {REPOSITORY, REPOSITORY.removesuffix(".git"), "git@github.com:testofschool/preflight.git"},
            "Origin differs from the authorized public repository")
    refs = public_refs(ops)
    verify_prior_refs(refs)
    require("refs/tags/" + SOURCE_TAG not in refs, "The new public source tag already exists; no overwrite allowed")
    local_tags = git(ops, "tag", "--list", SOURCE_TAG).strip()
    require(not local_tags, "The new local source tag already exists; no overwrite allowed")
    remote_main = refs.get("refs/heads/main")
    require(remote_main and re.fullmatch(r"[0-9a-f]{40}", remote_main), "Public main identity is unavailable")
    git(ops, "merge-base", "--is-ancestor", remote_main, commit)
    guard("create annotated source tag")
    git(ops, "tag", "-a", SOURCE_TAG, commit, "-m", "AI Builder Cup 2026 Track J source: cumulative check ceiling 3000")
    tag_object = git(ops, "rev-parse", "refs/tags/" + SOURCE_TAG).strip()
    require(git(ops, "rev-parse", SOURCE_TAG + "^{commit}").strip() == commit, "Local source tag points elsewhere")
    require(git(ops, "cat-file", "-t", tag_object).strip() == "tag", "Local source ref is not an annotated tag")
    # The scan runs after the annotated tag exists and includes every reachable ref.
    ops.command("scan all reachable Git history", [sys.executable, str(ROOT / "scripts/scan_history_v3.py"),
        "--report", str(OUT / "history_scan.json")])
    scan = json.loads((OUT / "history_scan.json").read_text())
    require(scan.get("complete") is True and scan.get("passed") is True and scan.get("hit_count") == 0 and
        scan.get("errors") == [] and scan.get("head") == commit, "All-history secret scan did not pass at the source commit")
    require(git(ops, "rev-parse", "HEAD").strip() == commit, "Local HEAD moved before atomic push")
    fresh = public_refs(ops)
    require(fresh == refs, "Public refs changed before publication")
    guard("atomic source and tag push", 240)
    git(ops, "push", "--atomic", "origin", commit + ":refs/heads/main", "refs/tags/" + SOURCE_TAG)
    anonymous = anonymous_verify(ops, commit, runtime_hash, tag_object)
    receipt = {"pass": True, "source_commit": commit, "source_tag": SOURCE_TAG,
        "annotated_tag_object": tag_object, "prior_public_main": remote_main,
        "fast_forward_only": True, "atomic_push": True, "history_scan_hit_count": 0,
        "anonymous_clone_pass": anonymous["pass"]}
    save(ops, "publication.json", receipt)
    return receipt


def main(args):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", args.commit)), "A full lowercase source commit SHA is required")
    guard("start Track J", 600)
    OUT.mkdir(parents=True, exist_ok=True)
    # Refuse a second execution; a failed or interrupted gate is never retried.
    descriptor = os.open(OUT / "deployment_started.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as marker:
        json.dump({"source_commit": args.commit, "started_at_kst": now().isoformat(), "one_shot": True}, marker)
        marker.write("\n")
    ops = None
    promotion_attempted = False
    candidate_name = None
    try:
        ops = SafeOperations()
        # Native provenance helper remains unchanged, but its subprocesses share
        # this harness's deadline and fixed-diagnostic policy.
        source.command = lambda arguments, label: ops.binary_command(label, arguments)
        files = source_preconditions(ops, args.commit)
        tests = verify_full_suite(args.tests, args.commit, files)
        save(ops, "full_suite.json", tests)
        service_before = native(ops)
        baseline = native(ops, "revisions", BASELINE)
        verify_baseline(service_before, baseline)
        before_receipt = safe_summary(service_before, baseline)
        before_receipt["allowance_before_candidate"] = read_allowance(ops, baseline, 1000)
        save(ops, "before.json", before_receipt)
        build_id, image, build_receipt = build_image(ops, args.commit, files, args.build_id)
        # Recheck the immutable baseline and mutable service immediately before mutation.
        fresh_before = native(ops)
        verify_baseline(fresh_before, baseline)
        require(settings_annotations(fresh_before.get("metadata", {})) == settings_annotations(service_before.get("metadata", {})) and
            settings_annotations(fresh_before["spec"]["template"].get("metadata", {})) ==
                settings_annotations(service_before["spec"]["template"].get("metadata", {})),
            "Service settings changed during the build")
        guard("create no-traffic candidate", 420)
        ops.command("create no-traffic Track J candidate", ["gcloud", "run", "services", "update", "preflight",
            "--region", REGION, "--image", image, "--update-env-vars", "PREFLIGHT_TOTAL_REQUEST_LIMIT=3000",
            "--no-traffic", "--tag", CANDIDATE_TAG, "--quiet", "--format=json"])
        prepared = native(ops)
        candidate_name = prepared["status"]["latestReadyRevisionName"]
        require(candidate_name != BASELINE and primary(prepared) == [(BASELINE, 100)], "Candidate preparation moved production traffic")
        candidate = native(ops, "revisions", candidate_name)
        verify_candidate(candidate, baseline, image)
        require(settings_annotations(prepared.get("metadata", {})) == settings_annotations(service_before.get("metadata", {})) and
            settings_annotations(prepared["spec"]["template"].get("metadata", {})) ==
                settings_annotations(service_before["spec"]["template"].get("metadata", {})),
            "Candidate preparation changed service or template annotation settings")
        tags = [row for row in prepared["status"]["traffic"] if row.get("tag") == CANDIDATE_TAG]
        require(len(tags) == 1 and tags[0].get("revisionName") == candidate_name and not tags[0].get("percent"),
                "Candidate tag does not identify the zero-traffic candidate")
        url = tags[0]["url"]
        receipt = safe_summary(prepared, candidate)
        receipt.update(source_commit=args.commit, build_id=build_id, no_primary_traffic_moved=True,
            only_image_and_total_allowance_changed=True)
        save(ops, "candidate.json", receipt)
        provenance = source.verify(SimpleNamespace(commit=args.commit, build_id=build_id, revision=candidate_name))
        require(provenance.get("pass") is True and provenance["git_runtime_source_sha256"] ==
            provenance["cloud_build_runtime_source_sha256"] == build_receipt["git_runtime_source_sha256"] and
            provenance["revision_image_digest"] == build_receipt["build_image_digest"],
            "Native candidate source/image provenance did not pass")
        provenance.update(source_generation=build_receipt["source_generation"], generation_pinned=True,
            source_object_identity_sha256=build_receipt["source_object_identity_sha256"])
        save(ops, "source_match.json", provenance)
        require(primary(native(ops)) == [(BASELINE, 100)], "Production changed before the HTTP gate")
        gate = run_gate(ops, url, candidate_name, baseline)
        require(gate["pass"] is True, "Candidate HTTP gate did not pass")
        publication = publish(ops, args.commit, build_receipt["git_runtime_source_sha256"])
        require(publication["pass"] is True, "Public source verification did not pass")
        ready = native(ops)
        require(primary(ready) == [(BASELINE, 100)], "Production changed before promotion")
        tag = next((row for row in ready["status"]["traffic"] if row.get("tag") == CANDIDATE_TAG), {})
        require(tag.get("revisionName") == candidate_name, "Candidate route changed before promotion")
        verify_candidate(native(ops, "revisions", candidate_name), baseline, image)
        require(git(ops, "rev-parse", "HEAD").strip() == args.commit, "Local source HEAD moved before promotion")
        # Leave five minutes for native verification and one bounded restoration.
        guard("promote verified candidate", 300)
        promotion_attempted = True
        ops.command("promote passed Track J candidate", ["gcloud", "run", "services", "update-traffic", "preflight",
            "--region", REGION, "--to-revisions", candidate_name + "=100", "--quiet", "--format=json"], timeout=90)
        after = native(ops)
        require(primary(after) == [(candidate_name, 100)], "Post-promotion traffic verification failed")
        final_revision = native(ops, "revisions", candidate_name)
        verify_candidate(final_revision, baseline, image)
        allowance_after = read_allowance(ops, baseline, 3000)
        require(allowance_after["stored_last_admission_limit"] == 3000, "Final stored allowance differs from the promoted limit")
        promotion = safe_summary(after, final_revision)
        promotion.update(pass_=True, source_commit=args.commit, source_tag=SOURCE_TAG, build_id=build_id,
            gate_passed=True, native_provenance_pass=True, history_scan_hit_count=0,
            anonymous_clone_pass=True, allowance_after_promotion=allowance_after,
            git_runtime_source_sha256=provenance["git_runtime_source_sha256"],
            cloud_build_runtime_source_sha256=provenance["cloud_build_runtime_source_sha256"],
            exact_http_attempts=5, cumulative_check_gate_attempts=2)
        promotion["pass"] = promotion.pop("pass_")
        save(ops, "promotion.json", promotion)
        print(json.dumps({"pass": True, "revision": candidate_name, "traffic_percent": 100,
            "source_commit": args.commit, "image_digest": build_receipt["build_image_digest"],
            "used": allowance_after["used"], "limit": 3000, "http_gate_attempts": 5}))
        return 0
    except Exception as error:
        failure = {"pass": False, "error_type": type(error).__name__,
            "failure": str(error) if isinstance(error, ReleaseError) else "Local processing failed; raw diagnostics not retained",
            "candidate_revision": candidate_name, "promotion_attempted": promotion_attempted,
            "no_failed_gate_retry": True, "baseline_retained_at_100": "UNVERIFIED"}
        if ops is not None:
            try:
                current = native(ops)
                if primary(current) != [(BASELINE, 100)]:
                    # Includes an unexpected traffic move during candidate creation.
                    guard("restore baseline after failed Track J")
                    failure["rollback_attempted"] = True
                    ops.command("restore required baseline after failed Track J", ["gcloud", "run", "services", "update-traffic", "preflight",
                        "--region", REGION, "--to-revisions", BASELINE + "=100", "--quiet", "--format=json"], timeout=60)
                    current = native(ops)
                failure["baseline_retained_at_100"] = primary(current) == [(BASELINE, 100)]
                failure["traffic"] = [{"revision": row.get("revisionName"), "percent": row.get("percent", 0)}
                    for row in current["status"]["traffic"]]
            except Exception as inspection_error:
                failure["restoration_or_inspection_error"] = type(inspection_error).__name__
            try:
                save(ops, "failure.json", failure)
            except Exception:
                failure["receipt_write_failed"] = True
            print(ops.scrub(json.dumps(failure)))
        else:
            print(json.dumps(failure))
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--build-id", help="Reuse this already-submitted native build; never submit a duplicate")
    parser.add_argument("--tests", type=Path, default=OUT / "fulltests.xml")
    arguments = parser.parse_args()
    try:
        raise SystemExit(main(arguments))
    except Exception as error:
        # No native diagnostics, private paths or account identifiers are printed.
        print(json.dumps({"pass": False, "error_type": type(error).__name__,
            "failure": str(error) if isinstance(error, ReleaseError) else "Track J did not start; private diagnostics not retained"}))
        raise SystemExit(1)
