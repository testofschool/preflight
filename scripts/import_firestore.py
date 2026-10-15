"""Idempotently import verified local exports into the dedicated Firestore store."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cloud.store import FirestoreDifficultyStore, prompt_id


def read_export(path: Path) -> list[dict]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    identifiers = set()
    for record in records:
        if record.get("id") != prompt_id(record["prompt"]):
            raise ValueError("Export prompt identity does not match its exact hash")
        if record["id"] in identifiers:
            raise ValueError("Export has duplicate prompt identities")
        identifiers.add(record["id"])
    return records


def import_exports(store: FirestoreDifficultyStore, artifact_dir: Path, batch_size: int = 400) -> dict:
    if not 1 <= batch_size <= 400:
        raise ValueError("Import batches must contain between one and 400 writes")
    exports = {name: read_export(artifact_dir / (name + ".jsonl")) for name in ("prompts_v1", "items_v1")}
    if {record["id"] for record in exports["prompts_v1"]} != {record["id"] for record in exports["items_v1"]}:
        raise ValueError("Prompt and item exports have different identities")
    operations = [(name, record) for name, records in exports.items() for record in records]
    for start in range(0, len(operations), batch_size):
        batch = store.client.batch()
        for collection, record in operations[start : start + batch_size]:
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
            batch.set(
                store.client.collection(collection).document(record["id"]),
                {**record, "source_record_sha256": hashlib.sha256(canonical.encode()).hexdigest()},
                merge=True,
            )
        batch.commit(timeout=30)
    engine = json.loads((artifact_dir / "engine.json").read_text())
    store.client.collection("metadata_v1").document("engine").set({
        "schema_version": engine["schema_version"],
        "model_ability": dict(zip(engine["models"], engine["ability"])),
        "fit_diagnostics": engine["fit_diagnostics"],
        "prompts_export_sha256": hashlib.sha256((artifact_dir / "prompts_v1.jsonl").read_bytes()).hexdigest(),
        "items_export_sha256": hashlib.sha256((artifact_dir / "items_v1.jsonl").read_bytes()).hexdigest(),
    }, merge=True, timeout=30)
    return {"status": "imported", "export_counts": {name: len(records) for name, records in exports.items()}, "collection_counts": store.collection_counts()}


def authenticated_store() -> FirestoreDifficultyStore:
    """Use ADC in production; a local gcloud token only when ADC is absent."""
    from google.auth.exceptions import DefaultCredentialsError
    from google.oauth2.credentials import Credentials

    try:
        return FirestoreDifficultyStore.from_env()
    except DefaultCredentialsError:
        access = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
            check=False,
        )
        token = access.stdout.strip()
        if access.returncode != 0 or not token:
            raise RuntimeError("Local cloud authentication is unavailable") from None
        return FirestoreDifficultyStore.from_env(credentials=Credentials(token=token))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.dry_run:
            result = {"status": "validated-local-only", "export_counts": {name: len(read_export(args.artifacts / (name + ".jsonl"))) for name in ("prompts_v1", "items_v1")}}
        else:
            result = import_exports(authenticated_store(), args.artifacts)
        print(json.dumps(result, sort_keys=True))
    except Exception as error:
        # SDK exception messages can contain project/resource identities.
        print(json.dumps({"status": "error", "error_type": type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
