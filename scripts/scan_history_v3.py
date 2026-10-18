#!/usr/bin/env python3
"""Scan every reachable Git history object without printing matched values."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_secrets import forbidden_markers
from scripts.verify_rewrites import save_report


def markers() -> dict[str, re.Pattern]:
    patterns = forbidden_markers()
    # Assemble marker names/prefixes so this scanner does not flag itself.
    private_field = b"private" + b"_key"
    patterns["private-key-json-field"] = re.compile(rb'["\x27]' + private_field + rb'["\x27]\s*:')
    fields = b"|".join(b"_".join(parts) for parts in (
        (b"client", b"secret"), (b"access", b"token"), (b"refresh", b"token"), (b"api", b"key")))
    patterns["literal-secret-field"] = re.compile(rb'(?i)["\x27]?(?:' + fields + rb')["\x27]?\s*[:=]\s*["\x27][^"\x27\r\n]{16,}["\x27]')
    prefixes = (b"gh" + b"p_", b"github" + b"_pat_", b"xox" + b"b-", b"xox" + b"p-", b"sk" + b"-proj-")
    patterns["service-token-prefix"] = re.compile(b"(?:" + b"|".join(prefixes) + rb")[A-Za-z0-9_-]{16,}")
    return patterns


def command(*parts: str) -> bytes:
    result = subprocess.run(["git", "-C", str(ROOT), *parts], capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError("git-command-failed")
    return result.stdout


def inspect() -> dict:
    expressions = markers()
    commits = command("rev-list", "--all").splitlines()
    listing = command("rev-list", "--objects", "--all").splitlines()
    objects = {}
    for line in listing:
        object_id, _, raw_path = line.partition(b" ")
        path = raw_path.decode("utf-8", "replace")
        for expression in expressions.values():
            path = expression.sub(b"[redacted-marker]", path.encode()).decode("utf-8", "replace")
        objects[object_id.decode("ascii")] = path
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "head": command("rev-parse", "HEAD").decode().strip(),
              "method": "all refs: git rev-list --all and every reachable blob/commit/tag object, deduplicated by object ID; binary payloads included; only marker names, object IDs, paths and line numbers retained",
              "commits_scanned": len(commits), "reachable_objects": len(objects),
              "payload_objects_scanned": 0, "blob_objects_scanned": 0,
              "commit_tag_objects_scanned": 0, "binary_payloads_scanned": 0,
              "marker_names": sorted(expressions), "hits": [], "errors": []}
    process = subprocess.Popen(["git", "-C", str(ROOT), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        for object_id, path in objects.items():
            process.stdin.write(object_id.encode() + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[0].decode("ascii") != object_id:
                report["errors"].append({"object": object_id, "reason": "invalid-object-header"})
                break
            kind, size = header[1], int(header[2])
            payload = process.stdout.read(size)
            delimiter = process.stdout.read(1)
            if len(payload) != size or delimiter != b"\n":
                report["errors"].append({"object": object_id, "reason": "truncated-object"})
                break
            if kind not in (b"blob", b"commit", b"tag"):
                continue
            report["payload_objects_scanned"] += 1
            report["blob_objects_scanned"] += int(kind == b"blob")
            report["commit_tag_objects_scanned"] += int(kind != b"blob")
            report["binary_payloads_scanned"] += int(b"\x00" in payload)
            for name, expression in expressions.items():
                for match in expression.finditer(payload):
                    report["hits"].append({"object": object_id, "object_type": kind.decode(),
                        "file": path or None, "marker": name,
                        "line": payload.count(b"\n", 0, match.start()) + 1})
    finally:
        process.stdin.close()
        process.stdout.close()
        if process.wait(timeout=10) != 0:
            report["errors"].append({"reason": "cat-file-exit-nonzero"})
    report["hit_count"] = len(report["hits"])
    report["complete"] = not report["errors"]
    report["passed"] = report["complete"] and report["hit_count"] == 0
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("Preserve the existing scan receipt; choose a new report path")
    report = inspect()
    save_report(args.report, report)
    print(json.dumps({key: report[key] for key in ("head", "commits_scanned", "blob_objects_scanned", "hit_count", "complete", "passed", "errors")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"scan_error_type": type(error).__name__, "complete": False}), file=sys.stderr)
        raise SystemExit(2)
