"""Validated, immutable rewrites recorded by the real agent for the five samples."""

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path


FIXTURE_PATH = Path(__file__).with_name("sample_rewrites.json")


def load_sample_rewrites(samples, path=None):
    """An absent fixture enables no saved rewrites; an invalid fixture fails startup."""
    path = Path(path or FIXTURE_PATH)
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1 or data.get("source") != "real-rewrite-agent":
        raise ValueError("Sample rewrite provenance is unavailable")
    generated_at = data.get("generated_at", "")
    generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    if generated.tzinfo is None:
        raise ValueError("Sample rewrite timestamp needs a timezone")
    rows = data.get("samples", [])
    if len(rows) != len(samples) or {row.get("prompt") for row in rows} != set(samples):
        raise ValueError("Sample rewrite fixture must contain every exact sample once")
    pinned = {}
    for row in rows:
        rewrite = deepcopy(row["rewrite"])
        before, after = rewrite.get("p_fail_before"), rewrite.get("p_fail_after")
        if (not isinstance(rewrite.get("rewritten_prompt"), str)
                or not rewrite["rewritten_prompt"].strip()
                or len(rewrite["rewritten_prompt"]) > 4000
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not 0 <= value <= 1 for value in (before, after))
                or rewrite.get("rewrite_status") not in ("improved", "no_safe_rewrite")):
            raise ValueError("Sample rewrite is missing its guarded score snapshot")
        if rewrite["rewrite_status"] == "improved" and not after < before:
            raise ValueError("Saved rewrite does not meet the strict improvement guard")
        if rewrite["rewrite_status"] == "no_safe_rewrite" and (
                rewrite["rewritten_prompt"] != row["prompt"] or after != before):
            raise ValueError("Saved unchanged rewrite differs from its original")
        # These fields describe the saved run, never a session or tool call this request made.
        for name in ("session_id", "session_verified", "session_event_count", "session_service"):
            rewrite.pop(name, None)
        rewrite.update(rewrite_source="pinned-sample", rewrite_saved_at=generated_at,
                       agent_trace_saved=True, rewrite_model_calls_this_request=0)
        pinned[row["prompt"]] = rewrite
    return pinned
