#!/usr/bin/env python3
"""Record frozen runtime, source video, and Git-tag identity without cloud access."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = "de0d563530405adf3dae5a26f5ded3f7a009917d"
EXPECTED_RAW = "d1f3772d1187ee7ce1aeed1e0efe3f432c09337e90cc0b7113b6ca37aa94ab78"
EXPECTED_TAGS = {
    "aibc-2026-submission": "dd12f279e364cbd217a4178b51c1d270cacebbdd",
    "aibc-2026-submission-v2": "bdcdecdf6db6b0c2bebea8a35ed350de5f005940",
    "aibc-2026-submission-v3": "d638c0690cb17d60316922eb30a14f150fe7c23c",
}
EXPLICIT = {
    "Dockerfile", "requirements-cloud.lock", "app.py", "artifacts/engine.json",
    "artifacts/vectorizer.joblib", "artifacts/prompt_vectors.npz",
    "cloud/sample_rewrites.py", "cloud/sample_rewrites.json",
}


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def runtime(path):
    parts = PurePosixPath(path).parts
    return path in EXPLICIT or (
        len(parts) > 1 and parts[0] in ("cloud", "preflight_core", "static")
        and "__pycache__" not in parts
    )


def main():
    paths = [p.decode() for p in git("ls-tree", "-rz", "--name-only", BASE).split(b"\0")
             if p and runtime(p.decode())]
    working_runtime = [str(p.relative_to(ROOT)) for folder in ("cloud", "preflight_core", "static")
                       for p in (ROOT / folder).rglob("*")
                       if p.is_file() and runtime(str(p.relative_to(ROOT)))]
    all_paths = set(paths) | set(working_runtime) | EXPLICIT
    rows = []
    digest = hashlib.sha256()
    for path in sorted(all_paths):
        before = git("show", BASE + ":" + path) if path in paths else None
        current = (ROOT / path).read_bytes() if (ROOT / path).is_file() else None
        if current is not None:
            digest.update(path.encode() + b"\0" + current)
        rows.append({"path": path, "matches": current is not None and current == before,
                     "sha256": hashlib.sha256(current).hexdigest() if current is not None else None})
    tags = {tag: git("rev-parse", tag).decode().strip() for tag in EXPECTED_TAGS}
    raw = ROOT / "demo/preflight_demo_raw.mp4"
    raw_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
    dataless = subprocess.check_output(
        ["find", str(ROOT), "-flags", "+dataless", "-type", "f", "-print"], text=True
    ).splitlines()
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "base": BASE, "head": git("rev-parse", "HEAD").decode().strip(),
        "runtime_file_count": len(rows), "runtime_digest": digest.hexdigest(),
        "runtime_unchanged": all(r["matches"] for r in rows), "files": rows,
        "tags": tags, "tags_unchanged": tags == EXPECTED_TAGS,
        "raw_sha256": raw_hash, "raw_unchanged": raw_hash == EXPECTED_RAW,
        "dataless_count": len(dataless),
    }
    report["passed"] = (report["runtime_unchanged"] and report["tags_unchanged"]
                        and report["raw_unchanged"] and not dataless)
    target = ROOT / "reports/final_v5/runtime_scope_final.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("files", "tags")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
