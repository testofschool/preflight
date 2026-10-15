#!/usr/bin/env python3
"""Reject source and log files containing forbidden credential markers.

Only marker names, relative file paths, and line numbers are reported. File
contents and environment values are never printed or read from outside root.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Iterator

EXCLUDED_DIRECTORIES = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".cache",
})


def forbidden_markers() -> dict[str, re.Pattern[bytes]]:
    """Construct markers in fragments so the guard does not flag itself."""
    key_name = b"_".join((b"GEMINI", b"API", b"KEY"))
    return {
        "provider-key-prefix": re.compile(b"AI" + b"za"),
        "private-key-marker": re.compile(b"-" * 5 + b"BEGIN"),
        "gemini-key-assignment": re.compile(
            rb"(?<![A-Za-z0-9_])[\"']?" + key_name + rb"[\"']?\s*[:=]"
        ),
    }


def display_path(path: Path, root: Path) -> str:
    rendered = str(path.relative_to(root)).encode("utf-8", errors="replace")
    for expression in forbidden_markers().values():
        rendered = expression.sub(b"[redacted-marker]", rendered)
    return rendered.decode("utf-8", errors="replace")


def candidate_files(root: Path) -> Iterator[Path]:
    def fail_on_directory_error(problem: OSError) -> None:
        raise problem

    for directory, names, files in os.walk(root, followlinks=False, onerror=fail_on_directory_error):
        names[:] = sorted(name for name in names if name not in EXCLUDED_DIRECTORIES)
        for name in names[:]:
            path = Path(directory, name)
            if path.is_symlink():
                names.remove(name)
                yield path
        for name in sorted(files):
            yield Path(directory, name)


def inspect_repository(root: Path, include_index: bool = False) -> dict[str, object]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError("root must be a directory")
    hits: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    scanned = 0
    binary_scanned = 0
    markers = forbidden_markers()

    def inspect_payload(payload: bytes, relative: str, source: str) -> None:
        for label, expression in markers.items():
            for match in expression.finditer(payload):
                hits.append({
                    "file": relative, "source": source,
                    "line": payload.count(b"\n", 0, match.start()) + 1,
                    "marker": label,
                })

    for path in candidate_files(root):
        relative = display_path(path, root)
        if path.is_symlink():
            errors.append({"file": relative, "reason": "symlink-not-followed"})
            continue
        try:
            payload = path.read_bytes()
        except OSError:
            errors.append({"file": relative, "reason": "unreadable"})
            continue
        scanned += 1
        binary_scanned += int(b"\x00" in payload or path.suffix.lower() in {".parquet", ".arrow", ".joblib", ".npz"})
        inspect_payload(payload, relative, "working-tree")
    staged_scanned = 0
    if include_index:
        listing = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--stage", "-z"],
            capture_output=True, check=False,
        )
        if listing.returncode:
            errors.append({"file": ".git", "reason": "index-unavailable"})
        else:
            for entry in listing.stdout.split(b"\x00"):
                if not entry:
                    continue
                metadata, raw_path = entry.split(b"\t", 1)
                mode, object_id, stage = metadata.split()
                relative_path = Path(os.fsdecode(raw_path))
                if any(part in EXCLUDED_DIRECTORIES for part in relative_path.parts):
                    continue
                relative = display_path(root / relative_path, root)
                if mode == b"120000" or mode == b"160000":
                    errors.append({"file": relative, "reason": "indexed-link-or-submodule-not-followed"})
                    continue
                if stage != b"0":
                    errors.append({"file": relative, "reason": "unmerged-index-entry"})
                    continue
                blob = subprocess.run(
                    ["git", "-C", str(root), "cat-file", "blob", object_id.decode("ascii")],
                    capture_output=True, check=False,
                )
                if blob.returncode:
                    errors.append({"file": relative, "reason": "index-blob-unreadable"})
                    continue
                staged_scanned += 1
                inspect_payload(blob.stdout, relative, "git-index")
    return {
        "check": "V2", "hit_count": len(hits), "files_scanned": scanned,
        "hits": hits, "skipped_files": [], "errors": errors,
        "binary_files_scanned": binary_scanned, "indexed_files_scanned": staged_scanned,
        "excluded_directory_names": sorted(EXCLUDED_DIRECTORIES),
        "method": "byte regex over every other file, including README and logs; no values emitted",
        "complete": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--include-index", action="store_true", help="also inspect every tracked staged blob")
    arguments = parser.parse_args()
    try:
        report = inspect_repository(arguments.root, include_index=arguments.include_index)
    except OSError:
        print(json.dumps({"check": "V2", "complete": False, "error": "invalid-root"}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if report["errors"] else int(bool(report["hit_count"]))


if __name__ == "__main__":
    raise SystemExit(main())
