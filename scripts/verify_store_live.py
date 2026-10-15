#!/usr/bin/env python3
"""Read-only comparison of imported Firestore content against local exports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.import_firestore import authenticated_store, read_export


ROOT = Path(__file__).resolve().parents[1]


def canonical_hash(record: dict) -> str:
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_content(store, artifact_dir: Path) -> dict:
    """Read all documents; never write database records or expose their values."""
    expected = {name: read_export(artifact_dir / (name + ".jsonl")) for name in ("prompts_v1", "items_v1")}
    if any(len(records) != 508 for records in expected.values()):
        raise ValueError("The expected historical export must contain 508 records per collection")
    if {row["id"] for row in expected["prompts_v1"]} != {row["id"] for row in expected["items_v1"]}:
        raise ValueError("Historical prompt and item identities do not match")
    collections = {}
    for name, records in expected.items():
        snapshots = list(store.client.collection(name).stream(timeout=30))
        remote = {snapshot.id: snapshot.to_dict() for snapshot in snapshots if snapshot.exists}
        expected_ids = {row["id"] for row in records}
        matching = 0
        missing = 0
        changed_documents = 0
        field_diffs = 0
        hash_diffs = 0
        for record in records:
            observed = remote.get(record["id"])
            if observed is None:
                missing += 1
                field_diffs += len(record)
                hash_diffs += 1
                continue
            # Extra top-level postcheck counters are intentional. Each original
            # exported field, including the complete outcomes map, must match.
            changed_fields = sum(key not in observed or observed[key] != value for key, value in record.items())
            changed_hash = observed.get("source_record_sha256") != canonical_hash(record)
            field_diffs += changed_fields
            hash_diffs += int(changed_hash)
            changed_documents += int(bool(changed_fields or changed_hash))
            matching += int(not changed_fields and not changed_hash)
        extra_ids = set(remote) - expected_ids
        extra_historical = sum(
            name == "items_v1" or any(field in remote[identifier] for field in ("both_bad_rate", "vote_count", "outcomes"))
            for identifier in extra_ids
        )
        collections[name] = {
            "expected_documents": len(records),
            "remote_documents": len(remote),
            "matching_expected_documents": matching,
            "missing_expected_documents": missing,
            "changed_expected_documents": changed_documents,
            "expected_field_differences": field_diffs,
            "source_hash_differences": hash_diffs,
            "extra_historical_documents": extra_historical,
            "extra_feedback_only_documents": len(extra_ids) - extra_historical,
            "document_difference_count": missing + changed_documents + extra_historical,
        }
    engine_path = artifact_dir / "engine.json"
    engine = json.loads(engine_path.read_text())
    expected_ability = dict(zip(engine["models"], engine["ability"]))
    metadata = store.client.collection("metadata_v1").document("engine").get(timeout=20)
    metadata_document = metadata.to_dict() if metadata.exists else {}
    observed_ability = metadata_document.get("model_ability")
    ability_diffs = sum(
        not isinstance(observed_ability, dict) or name not in observed_ability or observed_ability[name] != value
        for name, value in expected_ability.items()
    )
    extra_ability = len(set(observed_ability) - set(expected_ability)) if isinstance(observed_ability, dict) else 0
    metadata_difference = int(not metadata.exists or ability_diffs > 0 or extra_ability > 0)
    total_diffs = sum(row["document_difference_count"] for row in collections.values()) + metadata_difference
    return {
        "check": "read-only Firestore historical content integrity",
        "expected_historical_documents": sum(len(records) for records in expected.values()),
        "matching_historical_documents": sum(row["matching_expected_documents"] for row in collections.values()),
        "collections": collections,
        "metadata": {
            "exists": bool(metadata.exists),
            "expected_model_abilities": len(expected_ability),
            "ability_value_differences": ability_diffs,
            "extra_model_abilities": extra_ability,
            "document_difference_count": metadata_difference,
        },
        "document_difference_count": total_diffs,
        "passed": total_diffs == 0,
        "read_only": True,
        "ignored_extra_fields": "Only top-level fields absent from local exports, including separate postcheck feedback, are ignored",
        "engine_artifact_sha256": hashlib.sha256(engine_path.read_bytes()).hexdigest(),
        "export_sha256": {name: hashlib.sha256((artifact_dir / (name + ".jsonl")).read_bytes()).hexdigest() for name in expected},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--report", type=Path, default=ROOT / "reports" / "firestore_integrity.json")
    parser.add_argument("--log", type=Path, default=ROOT / "logs" / "firestore_integrity.txt")
    args = parser.parse_args()
    report = verify_content(authenticated_store(), args.artifacts)
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    for path in (args.report, args.log):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded)
    print(json.dumps({
        "expected_historical_documents": report["expected_historical_documents"],
        "matching_historical_documents": report["matching_historical_documents"],
        "document_difference_count": report["document_difference_count"],
        "metadata_ability_difference_count": report["metadata"]["ability_value_differences"] + report["metadata"]["extra_model_abilities"],
    }, sort_keys=True))
    return int(not report["passed"])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as problem:
        print(json.dumps({"verification_error_type": type(problem).__name__, "complete": False}), file=sys.stderr)
        raise SystemExit(2)
