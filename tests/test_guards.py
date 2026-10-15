"""Behavioral checks for the copy-overlap and credential guards."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


freshness = load_script("check_freshness")
secrets = load_script("check_secrets")


def marker_fixtures() -> list[bytes]:
    return [
        b"AI" + b"za" + b"synthetic-value",
        b"-" * 5 + b"BEGIN" + b" PRIVATE KEY" + b"-" * 5,
        b"_".join((b"GEMINI", b"API", b"KEY")) + b"=synthetic-value",
    ]


def test_secret_guard_finds_source_readme_and_logs_without_echoing_values(tmp_path: Path):
    values = marker_fixtures()
    for filename, value in zip(("app.py", "README.md", "request.log"), values):
        (tmp_path / filename).write_bytes(b"innocent first line\n" + value)
    report = secrets.inspect_repository(tmp_path)
    assert report["hit_count"] == 3
    assert {row["file"] for row in report["hits"]} == {"app.py", "README.md", "request.log"}
    assert all(row["line"] == 2 for row in report["hits"])
    rendered = json.dumps(report).encode()
    assert all(value not in rendered for value in values)


def test_secret_guard_accepts_runtime_lookup_and_fragmented_guard_source(tmp_path: Path):
    name = "_".join(("GEMINI", "API", "KEY"))
    (tmp_path / "app.py").write_text(f'key = os.environ.get("{name}")\n')
    (tmp_path / "guard.py").write_bytes((ROOT / "scripts" / "check_secrets.py").read_bytes())
    report = secrets.inspect_repository(tmp_path)
    assert report["hit_count"] == 0
    assert report["complete"]


def test_secret_guard_catches_spaced_or_quoted_assignment(tmp_path: Path):
    name = b"_".join((b"GEMINI", b"API", b"KEY"))
    (tmp_path / "config.json").write_bytes(b'{"' + name + b'": "synthetic-value"}')
    (tmp_path / ".env").write_bytes(name + b" = synthetic-value")
    assert secrets.inspect_repository(tmp_path)["hit_count"] == 2


def test_secret_guard_has_no_report_or_log_exclusion(tmp_path: Path):
    directory = tmp_path / "audit_reports"
    directory.mkdir()
    (directory / "evidence.json").write_bytes(marker_fixtures()[0])
    assert secrets.inspect_repository(tmp_path)["hit_count"] == 1


def test_secret_guard_scans_binary_input_data(tmp_path: Path):
    (tmp_path / "data.parquet").write_bytes(bytes((0, 255)) + marker_fixtures()[0])
    report = secrets.inspect_repository(tmp_path)
    assert report["hit_count"] == 1
    assert report["binary_files_scanned"] == 1
    assert report["skipped_files"] == []


def test_secret_guard_checks_index_even_when_working_copy_is_clean(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    payload = tmp_path / "staged.txt"
    payload.write_bytes(marker_fixtures()[0])
    subprocess.run(["git", "-C", str(tmp_path), "add", "staged.txt"], check=True)
    payload.write_text("clean replacement\n")
    report = secrets.inspect_repository(tmp_path, include_index=True)
    assert report["hit_count"] == 1
    assert report["hits"][0]["source"] == "git-index"
    assert report["indexed_files_scanned"] == 1


def test_secret_guard_does_not_follow_external_symlinks(tmp_path: Path):
    external = tmp_path / "outside"
    external.write_bytes(marker_fixtures()[0])
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "linked.txt").symlink_to(external)
    report = secrets.inspect_repository(repository)
    assert report["hit_count"] == 0
    assert not report["complete"]
    assert report["errors"][0]["reason"] == "symlink-not-followed"


def test_secret_cli_exit_is_nonzero_on_hit_and_contains_no_values(tmp_path: Path):
    marker = marker_fixtures()[0]
    (tmp_path / "request.log").write_bytes(marker)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_secrets.py"), "--root", str(tmp_path)],
        capture_output=True, check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["hit_count"] == 1
    assert marker not in result.stdout + result.stderr


def test_both_guards_reject_file_as_root(tmp_path: Path):
    payload = tmp_path / "source.py"
    payload.write_text("result = 1\n")
    with pytest.raises(NotADirectoryError):
        secrets.inspect_repository(payload)
    with pytest.raises(NotADirectoryError):
        freshness.compare_repository(payload, payload)


REFERENCE = "def convert(value):\n    selected = value + 3\n    return selected * (value - 7) + value / 2\n"


def test_python_overlap_ignores_layout_and_comments(tmp_path: Path):
    reference = tmp_path / "reference.py"
    reference.write_text(REFERENCE)
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "copied.py").write_text(
        "# comment\ndef convert( value ):\n selected=value+3 # trailing\n return selected*(value-7)+value/2\n"
    )
    report = freshness.compare_repository(repository, reference)
    assert report["matching_file_count"] == 1
    assert report["matches"][0]["mode"] == "python-lexical"


def test_short_or_different_python_does_not_trigger_overlap(tmp_path: Path):
    reference = tmp_path / "reference.py"
    reference.write_text(REFERENCE)
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "short.py").write_text("def convert(value):\n    return value\n")
    (repository / "independent.py").write_text("items = [entry.upper() for entry in ['red', 'green']]\n")
    report = freshness.compare_repository(repository, reference)
    assert report["matching_file_count"] == 0
    assert report["complete"]


def test_text_overlap_uses_whitespace_tokens(tmp_path: Path):
    reference = tmp_path / "reference.py"
    reference.write_text("# " + " ".join(f"word{i}" for i in range(25)) + "\n")
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "notes.md").write_text("\n\t".join(f"word{i}" for i in range(25)))
    report = freshness.compare_repository(repository, reference)
    assert report["matching_file_count"] == 1
    assert report["matches"][0]["mode"] == "text-whitespace"


def test_freshness_reports_binary_skip_and_tokenization_error(tmp_path: Path):
    reference = tmp_path / "reference.py"
    reference.write_text(REFERENCE)
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "data.parquet").write_bytes(bytes((0, 255, 13)))
    (repository / "broken.py").write_text("def broken(:\n")
    report = freshness.compare_repository(repository, reference)
    assert not report["complete"]
    assert report["skipped_files"][0]["file"] == "data.parquet"
    assert report["errors"][0]["reason"] == "python-tokenization-failed"


def test_freshness_width_must_be_positive(tmp_path: Path):
    with pytest.raises(ValueError):
        freshness.compare_repository(tmp_path, tmp_path / "unused.py", 0)
