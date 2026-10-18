#!/usr/bin/env python3
"""Anonymous exact-HEAD check for the later approved 21:30 submission state.

The generic Git/HTTP helpers are reused from the earlier verifier. Its old
frozen-J expectations and verdict are not run: later user-approved releases
changed the public UI, selected deck, video and exact brief description.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("public_helpers", HERE / "verify_public_package_v7.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
EXPECTED_RUNTIME = "a13b334ba0d2eabdc7773b4babb86ebd7c4bc48fe0019bd2e31adff84cc0131b"
VIDEO_URL = "https://youtu.be/1A8I-9NZ3Kc"
EXPECTED_ARTIFACTS = {
    "README.md": "e28cd1ce7f586e2e18457e423276eebaa6db72e96cea03fd2df95f84c2489bf7",
    "docs/submission-notes.md": "95a50e0ad317ad92b5889701a496f3f92bd06b643b985487c6f03f73b2a50b34",
    "docs/Preflight_pitch_deck.pdf": "15ecda0625f41e3a846e03da4685270e3cc4f276c4582808bad11fe2913f514a",
    "docs/Preflight_pitch_deck.pptx": "6e322734aafafd873cff29bba04b0b3c1e61d983aa5268ebd17c9d724aa03313",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_commit) or args.report.exists():
        parser.error("Require a full lowercase commit and a new receipt path")
    r = {"checked_at_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
         "expected_commit": args.expected_commit, "anonymous": True,
         "credentials_provided": False, "curlrc_disabled": True,
         "tls_verification": True, "pass": False, "errors": [],
         "youtube_visibility_checked_by_this_script": False}
    try:
        with tempfile.TemporaryDirectory(prefix="preflight-f2130-verify-", dir="/private/tmp") as folder:
            tmp = Path(folder)
            clone = tmp / "repo"
            helper.git(["clone", "--depth=1", "--single-branch", "--branch", "main",
                        "--no-tags", "--no-checkout", helper.REPOSITORY + ".git", str(clone)],
                       "anonymous-clone")
            head = helper.git(["rev-parse", "HEAD"], "clone-head", clone).decode().strip()
            r["cloned_main_commit"] = head
            r["commit_matches"] = head == args.expected_commit
            count, digest = helper.runtime_digest(clone, head)
            r.update(runtime_file_count=count, runtime_sha256=digest,
                     runtime_preserved=count == 25 and digest == EXPECTED_RUNTIME)
            refs = helper.git(["ls-remote", helper.REPOSITORY + ".git",
                               *["refs/tags/" + t for t in helper.EXPECTED_TAGS]], "tag-refs")
            found = dict(line.split("\t", 1)[::-1] for line in refs.decode().splitlines())
            r["tag_objects"] = {t: found.get("refs/tags/" + t) for t in helper.EXPECTED_TAGS}
            r["four_tag_objects_preserved"] = r["tag_objects"] == helper.EXPECTED_TAGS
            r["selected_artifacts"] = []
            for path, expected in EXPECTED_ARTIFACTS.items():
                data = helper.git(["show", head + ":" + path], "artifact-blob", clone)
                sha = hashlib.sha256(data).hexdigest()
                r["selected_artifacts"].append({"path": path, "bytes": len(data),
                                                "sha256": sha, "matches": sha == expected})
            readme = helper.git(["show", head + ":README.md"], "readme", clone)
            notes = helper.git(["show", head + ":docs/submission-notes.md"], "notes", clone)
            r["repo_http"] = helper.http_get(helper.REPOSITORY, tmp / "repo.html")
            r["readme_http"] = helper.http_get(
                "https://raw.githubusercontent.com/testofschool/preflight/main/README.md", tmp / "README.md")
            r["public_readme_matches_clone"] = (tmp / "README.md").read_bytes() == readme
            r["video_url_in_readme_and_notes"] = all(VIDEO_URL.encode() in b for b in (readme, notes))
            prefix = "Brief description = "
            descriptions = [s[len(prefix):] for s in notes.decode().splitlines() if s.startswith(prefix)]
            if len(descriptions) != 1:
                raise helper.VerificationError("brief-count-invalid")
            brief = descriptions[0]
            r["brief_characters"] = len(brief)
            r["brief_sha256"] = hashlib.sha256(brief.encode()).hexdigest()
            r["approved_brief_preserved"] = len(brief) == 1017 and brief.endswith(
                "Firebase: we use Cloud Firestore; Hosting and Auth are not used.")
            r["pass"] = all([r["commit_matches"], r["runtime_preserved"],
                r["four_tag_objects_preserved"], all(x["matches"] for x in r["selected_artifacts"]),
                r["repo_http"] == 200, r["readme_http"] == 200,
                r["public_readme_matches_clone"], r["video_url_in_readme_and_notes"],
                r["approved_brief_preserved"]])
        r["temporary_clone_removed"] = True
    except helper.VerificationError as e:
        r["errors"].append(str(e))
    except (OSError, ValueError, UnicodeError):
        r["errors"].append("local-verification-processing-error")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(r, indent=2) + "\n")
    print(json.dumps({k: r.get(k) for k in ("pass", "cloned_main_commit", "runtime_preserved",
        "four_tag_objects_preserved", "brief_characters", "repo_http", "readme_http", "errors")}))
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
