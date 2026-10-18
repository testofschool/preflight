"""Compare a commit's runtime inputs with native Cloud Build/Run provenance.

Cloud metadata and the generation-pinned source archive stay in memory or a
private temporary directory. Receipts omit project, repository and bucket IDs.
The digest matches release_cloud.build_digest: sorted path UTF-8, NUL, bytes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REGION = "asia-southeast1"
EXPLICIT_PATHS = {"Dockerfile", "requirements-cloud.lock", "app.py",
                  "artifacts/engine.json", "artifacts/vectorizer.joblib", "artifacts/prompt_vectors.npz",
                  "cloud/sample_rewrites.py", "cloud/sample_rewrites.json"}
DIGEST_METHOD = "SHA256 of sorted relative path UTF-8 + NUL + file bytes concatenated for runtime Docker COPY inputs"


class ProvenanceError(Exception):
    """Messages are fixed local descriptions, never raw subprocess diagnostics."""


def command(arguments: list[str], label: str) -> bytes:
    result = subprocess.run(arguments, cwd=ROOT, capture_output=True,
        env={**os.environ, "CLOUDSDK_CORE_DISABLE_PROMPTS": "1"}, timeout=180)
    if result.returncode:
        raise ProvenanceError(label + " failed; native diagnostics were not copied")
    return result.stdout


def runtime_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return path in EXPLICIT_PATHS or (bool(parts) and parts[0] in ("cloud", "preflight_core", "static")
                                      and len(parts) > 1 and "__pycache__" not in parts)


def runtime_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.encode("utf-8") + b"\x00" + files[path])
    return digest.hexdigest()


def committed_inputs(commit: str) -> tuple[str, dict[str, bytes]]:
    resolved = command(["git", "rev-parse", "--verify", commit + "^{commit}"], "Commit resolution").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40,64}", resolved):
        raise ProvenanceError("Commit resolution returned an invalid object ID")
    entries = command(["git", "ls-tree", "-rz", "--full-tree", resolved], "Committed tree lookup")
    files = {}
    for entry in entries.split(b"\x00"):
        if not entry:
            continue
        header, raw_path = entry.split(b"\t", 1)
        mode, kind, _ = header.split(b" ")
        path = raw_path.decode("utf-8")
        if runtime_path(path):
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise ProvenanceError("Committed runtime inputs must be regular files")
            files[path] = command(["git", "show", resolved + ":" + path], "Committed input read")
    if not EXPLICIT_PATHS <= files.keys():
        raise ProvenanceError("Committed runtime inputs are incomplete")
    return resolved, files


def archived_inputs(archive_path: Path) -> dict[str, bytes]:
    files = {}
    with tarfile.open(archive_path, "r:*") as archive:
        for member in archive:
            raw = member.name
            while raw.startswith("./"):
                raw = raw[2:]
            path = PurePosixPath(raw)
            if path.is_absolute() or ".." in path.parts:
                raise ProvenanceError("Native archive contains an unsafe path")
            name = str(path)
            if member.isdir() or not runtime_path(name):
                continue
            if not member.isfile() or name in files:
                raise ProvenanceError("Native runtime inputs contain a link or duplicate path")
            source = archive.extractfile(member)
            if source is None:
                raise ProvenanceError("Native runtime input could not be read")
            with source:
                files[name] = source.read()
    if not EXPLICIT_PATHS <= files.keys():
        raise ProvenanceError("Native runtime inputs are incomplete")
    return files


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_digest(value) -> str:
    match = re.search(r"(?:^|@)(sha256:[0-9a-f]{64})$", str(value or ""))
    if not match:
        raise ProvenanceError("Native image digest is missing or invalid")
    return match.group(1)


def native_json(arguments: list[str], label: str) -> dict:
    try:
        value = json.loads(command(arguments, label))
    except (UnicodeError, ValueError):
        raise ProvenanceError(label + " returned invalid JSON") from None
    if not isinstance(value, dict):
        raise ProvenanceError(label + " returned an invalid record")
    return value


def verify(args) -> dict:
    commit, git_files = committed_inputs(args.commit)
    build = native_json(["gcloud", "builds", "describe", args.build_id, "--region", REGION,
                         "--format=json"], "Native build lookup")
    revision = native_json(["gcloud", "run", "revisions", "describe", args.revision, "--region", REGION,
                            "--format=json"], "Native revision lookup")
    if build.get("id") != args.build_id or revision.get("metadata", {}).get("name") != args.revision:
        raise ProvenanceError("Native build or revision identity differs from the requested identity")
    storage = build.get("sourceProvenance", {}).get("resolvedStorageSource", {})
    bucket, object_name, generation = (storage.get(key) for key in ("bucket", "object", "generation"))
    if not isinstance(bucket, str) or not bucket or not isinstance(object_name, str) or not object_name or not str(generation).isdigit():
        raise ProvenanceError("Native generation-pinned source archive is unavailable")
    source_uri = "gs://" + bucket + "/" + object_name + "#" + str(generation)
    revision_digest = image_digest(revision.get("status", {}).get("imageDigest"))
    build_digests = [image_digest(row.get("digest")) for row in build.get("results", {}).get("images", [])]
    if not build_digests:
        raise ProvenanceError("Native build image results are missing")
    with tempfile.TemporaryDirectory(prefix="preflight-preview-source-") as folder:
        archive_path = Path(folder) / "source.tgz"
        command(["gcloud", "storage", "cp", source_uri, str(archive_path), "--quiet"], "Native source archive download")
        archive_sha = file_sha256(archive_path)
        archive_files = archived_inputs(archive_path)
    git_hash, archive_hash = runtime_digest(git_files), runtime_digest(archive_files)
    files = []
    for path in sorted(git_files.keys() | archive_files.keys()):
        git_bytes, archive_bytes = git_files.get(path), archive_files.get(path)
        files.append({"path": path,
            "git_size_bytes": len(git_bytes) if git_bytes is not None else None,
            "archive_size_bytes": len(archive_bytes) if archive_bytes is not None else None,
            "git_sha256": hashlib.sha256(git_bytes).hexdigest() if git_bytes is not None else None,
            "archive_sha256": hashlib.sha256(archive_bytes).hexdigest() if archive_bytes is not None else None,
            "matches": git_bytes is not None and archive_bytes is not None and git_bytes == archive_bytes})
    matches = git_files.keys() == archive_files.keys() and git_hash == archive_hash and all(row["matches"] for row in files)
    expected_runtime_files = len(git_files)
    count_matches = len(archive_files) == expected_runtime_files
    digest_matches = revision_digest in build_digests
    passed = build.get("status") == "SUCCESS" and matches and count_matches and digest_matches
    return {"source": "native Cloud Build resolvedStorageSource archive",
        "verified_at_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "build_id": args.build_id, "build_status": build.get("status"), "revision": args.revision,
        "commit": commit, "digest_method": DIGEST_METHOD,
        "git_runtime_source_sha256": git_hash, "cloud_build_runtime_source_sha256": archive_hash,
        "runtime_matches_commit": matches, "expected_runtime_file_count": expected_runtime_files,
        "git_runtime_file_count": len(git_files), "archive_runtime_file_count": len(archive_files),
        "runtime_file_count_matches": count_matches,
        "native_provenance_archive_sha256": archive_sha,
        "build_image_digests": build_digests, "revision_image_digest": revision_digest,
        "image_digest_matches": digest_matches, "files": files, "pass": passed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/preview_v4/source_match.json")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", args.build_id) or not re.fullmatch(r"preflight-[a-z0-9-]+", args.revision):
        raise SystemExit("Build ID or revision format is invalid")
    try:
        report = verify(args)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_suffix(args.report.suffix + ".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(args.report)
    except (ProvenanceError, subprocess.TimeoutExpired):
        raise SystemExit("Native provenance verification failed; no raw cloud diagnostics or identifiers were copied") from None
    print(json.dumps({"pass": report["pass"], "files": report["git_runtime_file_count"],
                      "runtime_matches_commit": report["runtime_matches_commit"],
                      "image_digest_matches": report["image_digest_matches"],
                      "git_runtime_source_sha256": report["git_runtime_source_sha256"],
                      "cloud_build_runtime_source_sha256": report["cloud_build_runtime_source_sha256"]}))
    if not report["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
