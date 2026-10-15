from pathlib import Path
import subprocess
import sys

import pytest

from preflight_core.provenance import read_frozen_votes


ROOT = Path(__file__).resolve().parents[1]


def test_supplied_bytes_accepted():
    dataset, _ = read_frozen_votes(ROOT / "data/genai_video_test.parquet")
    assert len(dataset.votes) == 1911


@pytest.mark.parametrize("script", ["build_data.py", "evaluate.py"])
def test_changed_input_stops_before_outputs_are_touched(tmp_path, script):
    payload = bytearray((ROOT / "data/genai_video_test.parquet").read_bytes())
    payload[len(payload) // 2] ^= 1
    changed = tmp_path / "changed.parquet"
    changed.write_bytes(payload)
    output = tmp_path / "protected_output"
    output.mkdir()
    sentinel = output / "keep.txt"
    sentinel.write_text("Existing outputs must survive a rejected input.")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--data", str(changed), "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "Frozen data SHA-256 mismatch" in result.stderr
    assert "STOP" in result.stderr
    assert list(output.iterdir()) == [sentinel]
    assert sentinel.read_text() == "Existing outputs must survive a rejected input."
