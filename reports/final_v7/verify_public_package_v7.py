#!/usr/bin/env python3
"""Verify public main and fixed tags against the approved post-J runtime baseline.

v7 delta from the v5 verifier: new frozen runtime digest, v4 annotated tag
object checked independently of its source commit, and no Track D verdict.
No runtime or cloud mutation occurs.

Run after pushing the expected commit. The temporary anonymous clone and all
downloaded pages live in /private/tmp and are deleted on completion. This check
does not establish that a YouTube video is public, or complete blocked tracks.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
from zoneinfo import ZoneInfo

REPOSITORY = "https://github.com/testofschool/preflight"
STARTING_MAIN = "246b176763b6ace5af426939431566e09d1f925a"
EXPECTED_TAGS = {
    "aibc-2026-submission": "dd12f279e364cbd217a4178b51c1d270cacebbdd",
    "aibc-2026-submission-v2": "bdcdecdf6db6b0c2bebea8a35ed350de5f005940",
    "aibc-2026-submission-v3": "d638c0690cb17d60316922eb30a14f150fe7c23c",
    "aibc-2026-submission-v4": "a59bf91d65d81096b3bc930ef8eebf0e73b89b79",
}
EXPECTED_RUNTIME = "5ecfefe996dd08ef9dc9fe4bdc38e7dc735e28c487018a426fb6521918e88a21"
EXPECTED_RUNTIME_FILES = 25
EXPECTED_DESCRIPTION_SHA256 = "3bac4ff63ca67bf51c54d329abad0c3cb16da13f697bd35e3041e40959f6ef23"
EXPLICIT_PATHS = {
    "Dockerfile", "requirements-cloud.lock", "app.py",
    "artifacts/engine.json", "artifacts/vectorizer.joblib", "artifacts/prompt_vectors.npz",
    "cloud/sample_rewrites.py", "cloud/sample_rewrites.json",
}
ENVIRONMENT = {
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/usr/bin/false",
    "SSH_ASKPASS": "/usr/bin/false", "GIT_CONFIG_COUNT": "0",
}
GIT = [
    "/usr/bin/git", "-c", "credential.helper=", "-c", "http.extraHeader=",
    "-c", "core.askPass=/usr/bin/false", "-c", "core.hooksPath=/dev/null",
    "-c", "init.templateDir=",
]


class VerificationError(Exception):
    """Only fixed local step names are included in error metadata."""


def run(parts: list[str], step: str, cwd: Path | None = None) -> bytes:
    try:
        result = subprocess.run(parts, cwd=cwd, env=ENVIRONMENT,
                                capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise VerificationError(step + "-unavailable") from None
    if result.returncode:
        raise VerificationError(step + "-failed")
    return result.stdout


def git(parts: list[str], step: str, cwd: Path | None = None) -> bytes:
    return run(GIT + parts, step, cwd)


def runtime_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return path in EXPLICIT_PATHS or (
        len(parts) > 1 and parts[0] in {"cloud", "preflight_core", "static"}
        and "__pycache__" not in parts
    )


def runtime_digest(clone: Path, revision: str) -> tuple[int, str]:
    entries = git(["ls-tree", "-rz", "--full-tree", revision], "runtime-tree", clone)
    files: dict[str, bytes] = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        header, raw_path = entry.split(b"\t", 1)
        mode, kind, object_id = header.split(b" ")
        path = raw_path.decode("utf-8")
        if not runtime_path(path):
            continue
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            raise VerificationError("runtime-nonregular-file")
        files[path] = git(["cat-file", "blob", object_id.decode("ascii")], "runtime-blob", clone)
    if not EXPLICIT_PATHS <= files.keys():
        raise VerificationError("runtime-inputs-incomplete")
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.encode("utf-8") + b"\0" + files[path])
    return len(files), digest.hexdigest()


def http_get(url: str, destination: Path) -> int:
    status = run([
        "/usr/bin/curl", "-q", "--silent", "--show-error", "--location",
        "--max-time", "60", "--proto", "=https", "--proto-redir", "=https",
        "--output", str(destination), "--write-out", "%{http_code}", url,
    ], "public-http").decode("ascii").strip()
    if not re.fullmatch(r"[0-9]{3}", status):
        raise VerificationError("public-http-status-invalid")
    return int(status)


def inspect(expected_commit: str, report: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="preflight-final-v7-public-", dir="/private/tmp") as folder:
        temporary = Path(folder)
        clone = temporary / "clone"
        git(["clone", "--depth=1", "--single-branch", "--branch", "main",
             "--no-tags", "--no-checkout", REPOSITORY + ".git", str(clone)], "anonymous-clone")
        report["anonymous_clone_exit_code"] = 0
        cloned_head = git(["rev-parse", "HEAD"], "cloned-head", clone).decode("ascii").strip()
        report["cloned_main_commit"] = cloned_head
        report["main_matches_expected"] = cloned_head == expected_commit

        ref_names = ["refs/heads/main"] + ["refs/tags/" + tag for tag in EXPECTED_TAGS]
        listing = git(["ls-remote", REPOSITORY + ".git", *ref_names], "public-refs")
        refs = {}
        for line in listing.decode("ascii").splitlines():
            object_id, ref_name = line.split("\t", 1)
            refs[ref_name] = object_id
        report["remote_main_commit"] = refs.get("refs/heads/main")
        report["remote_main_matches_expected"] = refs.get("refs/heads/main") == expected_commit
        report["remote_tags"] = {tag: refs.get("refs/tags/" + tag) for tag in EXPECTED_TAGS}
        report["all_fixed_tags_match"] = all(
            refs.get("refs/tags/" + tag) == target for tag, target in EXPECTED_TAGS.items()
        )

        source_tag = "aibc-2026-submission-v4"
        git(["fetch", "--depth=1", "--no-tags", "origin", "refs/tags/" + source_tag],
            "source-tag-fetch", clone)
        source_commit = git(["rev-parse", "FETCH_HEAD^{commit}"], "source-tag-target", clone).decode("ascii").strip()
        report["cloned_source_tag_commit"] = source_commit
        report["cloned_source_tag_matches_expected"] = source_commit == "59fb23b262af480709461b648e84d26010e26060"
        main_count, main_digest = runtime_digest(clone, cloned_head)
        tag_count, tag_digest = runtime_digest(clone, source_commit)
        report.update({
            "cloned_main_runtime_file_count": main_count,
            "cloned_main_runtime_sha256": main_digest,
            "cloned_source_tag_runtime_file_count": tag_count,
            "cloned_source_tag_runtime_sha256": tag_digest,
            "runtime_matches_frozen_baseline": (
                main_count == tag_count == EXPECTED_RUNTIME_FILES
                and main_digest == tag_digest == EXPECTED_RUNTIME
            ),
        })

        readme = git(["show", cloned_head + ":README.md"], "cloned-readme", clone)
        notes = git(["show", cloned_head + ":docs/submission-notes.md"], "cloned-submission-notes", clone)
        report["repo_http_status"] = http_get(REPOSITORY, temporary / "repository.html")
        report["raw_readme_http_status"] = http_get(
            "https://raw.githubusercontent.com/testofschool/preflight/main/README.md",
            temporary / "README.md",
        )
        report["public_readme_matches_clone"] = (temporary / "README.md").read_bytes() == readme
        prefix = "Brief description = "
        descriptions = [line[len(prefix):] for line in notes.decode("utf-8").splitlines()
                        if line.startswith(prefix)]
        if len(descriptions) != 1:
            raise VerificationError("brief-description-count-invalid")
        description = descriptions[0]
        description_digest = hashlib.sha256(description.encode("utf-8")).hexdigest()
        report.update({
            "brief_description_characters": len(description),
            "brief_description_within1024": len(description) <= 1024,
            "brief_description_sha256": description_digest,
            "brief_description_matches_starting_baseline": description_digest == EXPECTED_DESCRIPTION_SHA256,
            "readme_video_placeholder_count": readme.count(b"<VIDEO_URL>"),
            "submission_notes_video_placeholder_count": notes.count(b"<VIDEO_URL>"),
            "youtube_public_status": "NOT_CHECKED_BY_THIS_SCRIPT",
            "track_d_checked_by_this_script": False,
        })
        report["pass"] = all([
            report["main_matches_expected"], report["remote_main_matches_expected"],
            report["all_fixed_tags_match"], report["cloned_source_tag_matches_expected"],
            report["runtime_matches_frozen_baseline"], report["repo_http_status"] == 200,
            report["raw_readme_http_status"] == 200, report["public_readme_matches_clone"],
            report["brief_description_within1024"], report["brief_description_matches_starting_baseline"],
        ])
    report["temporary_clone_removed_after_check"] = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit", required=True, help="Full 40-character commit pushed to main")
    parser.add_argument("--report", type=Path, required=True, help="New sanitized JSON receipt; must not exist")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_commit):
        parser.error("--expected-commit must be a full lowercase commit SHA")
    if args.report.exists():
        parser.error("Preserve the existing receipt; choose a new report path")
    report = {
        "checked_at_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "repository": REPOSITORY, "expected_main_commit": args.expected_commit,
        "starting_main_commit": STARTING_MAIN,
        "expected_fixed_tag_objects": EXPECTED_TAGS,
        "expected_source_tag_commit": "59fb23b262af480709461b648e84d26010e26060",
        "frozen_runtime_sha256": EXPECTED_RUNTIME,
        "frozen_runtime_file_count": EXPECTED_RUNTIME_FILES,
        "credentials_provided": False, "credential_helper": "empty",
        "global_config": "/dev/null", "system_config_disabled": True,
        "terminal_prompts_disabled": True, "extra_headers": "empty",
        "git_hooks": "disabled", "curlrc": "disabled", "tls_verification": True,
        "raw_diagnostics_saved": False, "pass": False, "errors": [],
    }
    try:
        inspect(args.expected_commit, report)
    except VerificationError as error:
        report["pass"] = False
        report["errors"].append(str(error))
        report["temporary_clone_removed_after_check"] = True
    except (OSError, ValueError, UnicodeError):
        report["pass"] = False
        report["errors"].append("local-metadata-processing-failed")
        report["temporary_clone_removed_after_check"] = "NOT_CONFIRMED"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report.get(key) for key in (
        "pass", "cloned_main_commit", "all_fixed_tags_match", "runtime_matches_frozen_baseline",
        "repo_http_status", "raw_readme_http_status", "brief_description_characters", "errors",
    )}, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
