#!/usr/bin/env python3
"""Check exact token overlap with an external method reference.

This is a copy-overlap check, not proof of authorship or creation date. It does
not retain or print source snippets from the reference.
"""
from __future__ import annotations

import argparse
from collections import Counter
import io
import json
import os
from pathlib import Path
import re
import tokenize

OMIT_DIRECTORIES = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".cache",
})
IGNORED_PYTHON_KINDS = frozenset({
    tokenize.ENCODING, tokenize.ENDMARKER, tokenize.COMMENT, tokenize.NEWLINE,
    tokenize.NL, tokenize.INDENT, tokenize.DEDENT,
})


def python_tokens(payload: bytes) -> list[str]:
    return [
        token.string for token in tokenize.tokenize(io.BytesIO(payload).readline)
        if token.type not in IGNORED_PYTHON_KINDS
    ]


def whitespace_tokens(payload: bytes) -> list[str]:
    return re.findall(r"\S+", payload.decode("utf-8-sig"))


def windows(tokens: list[str], width: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[index:index + width]) for index in range(len(tokens) - width + 1)}


def compare_repository(root: Path, reference: Path, width: int = 20) -> dict[str, object]:
    if width < 1:
        raise ValueError("window width must be positive")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError("root must be a directory")
    reference = reference.resolve(strict=True)
    reference_data = reference.read_bytes()
    reference_windows = {
        "python-lexical": windows(python_tokens(reference_data), width),
        "text-whitespace": windows(whitespace_tokens(reference_data), width),
    }
    matches: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    scanned = Counter()
    def fail_on_directory_error(problem: OSError) -> None:
        raise problem

    for directory, names, files in os.walk(root, followlinks=False, onerror=fail_on_directory_error):
        names[:] = sorted(name for name in names if name not in OMIT_DIRECTORIES)
        for name in names[:]:
            item = Path(directory, name)
            if item.is_symlink():
                names.remove(name)
                errors.append({"file": str(item.relative_to(root)), "reason": "symlink-not-followed"})
        for name in sorted(files):
            item = Path(directory, name)
            relative = str(item.relative_to(root))
            if item.is_symlink():
                errors.append({"file": relative, "reason": "symlink-not-followed"})
                continue
            try:
                payload = item.read_bytes()
            except OSError:
                errors.append({"file": relative, "reason": "unreadable"})
                continue
            mode = "python-lexical" if item.suffix.lower() == ".py" else "text-whitespace"
            try:
                tokens = python_tokens(payload) if mode == "python-lexical" else whitespace_tokens(payload)
            except UnicodeError:
                skipped.append({"file": relative, "reason": "binary-or-non-utf8"})
                continue
            except (tokenize.TokenError, IndentationError, SyntaxError):
                errors.append({"file": relative, "reason": "python-tokenization-failed"})
                continue
            if b"\x00" in payload and mode == "text-whitespace":
                skipped.append({"file": relative, "reason": "binary-nul-byte"})
                continue
            scanned[mode] += 1
            overlap = windows(tokens, width) & reference_windows[mode]
            if overlap:
                matches.append({"file": relative, "mode": mode, "shared_windows": len(overlap)})
    return {
        "check": "V1", "window_tokens": width, "matching_file_count": len(matches),
        "matches": matches, "files_scanned": dict(scanned), "skipped_files": skipped,
        "errors": errors, "complete": not errors,
        "excluded_directory_names": sorted(OMIT_DIRECTORIES),
        "methods": {
            "python-lexical": "exact Python token strings; comments, whitespace, indentation and line breaks excluded",
            "text-whitespace": "exact UTF-8 tokens split on whitespace for other text files",
        },
        "limitation": "zero overlap does not establish code creation date or independent authorship",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--window", type=int, default=20)
    arguments = parser.parse_args()
    try:
        report = compare_repository(arguments.root, arguments.reference, arguments.window)
    except (OSError, ValueError, tokenize.TokenError, SyntaxError, UnicodeError):
        print(json.dumps({"check": "V1", "complete": False, "error": "invalid-input-or-reference"}))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if report["errors"] else int(bool(report["matching_file_count"]))


if __name__ == "__main__":
    raise SystemExit(main())
