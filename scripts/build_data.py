"""Build reproducible local artifacts; this does not connect to a cloud store."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight_core import PreflightEngine
from preflight_core.irt import fit_items
from preflight_core.provenance import read_frozen_votes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/genai_video_test.parquet"))
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    dataset, source_digest = read_frozen_votes(args.data)
    fitted = fit_items(dataset.matrix)
    engine = PreflightEngine(dataset, fitted)
    engine.save(args.output)
    np.savez_compressed(
        args.output / "dataset.npz",
        outcomes=dataset.matrix,
        observation_counts=dataset.observation_counts,
        both_bad_counts=dataset.both_bad_counts,
        vote_counts=dataset.vote_counts,
    )
    prompt_records = []
    item_records = []
    for index, prompt in enumerate(dataset.prompts):
        identifier = hashlib.sha256(prompt.encode()).hexdigest()
        prompt_records.append({
            "id": identifier,
            "prompt": prompt,
            "outcomes": {
                name: {"mean": float(dataset.matrix[index, column]), "observations": int(dataset.observation_counts[index, column])}
                for column, name in enumerate(dataset.models)
                if np.isfinite(dataset.matrix[index, column])
            },
            "both_bad_rate": float(dataset.both_bad_rates[index]),
            "both_bad_votes": int(dataset.both_bad_counts[index]),
            "vote_count": int(dataset.vote_counts[index]),
            "source": "TIGER-Lab/GenAI-Bench video_generation/test",
        })
        item_records.append({
            "id": identifier,
            "prompt": prompt,
            "difficulty": float(fitted.difficulty[index]),
            "discrimination": float(fitted.discrimination[index]),
        })
    for name, records in (("prompts_v1", prompt_records), ("items_v1", item_records)):
        (args.output / (name + ".jsonl")).write_text("".join(json.dumps(record, allow_nan=False) + "\n" for record in records))
    manifest = {
        "source_name": "TIGER-Lab/GenAI-Bench video_generation/test",
        "source_license_declared_by_handoff": "CC-BY-4.0",
        "source_sha256": source_digest,
        "source_sha256_verified": True,
        "rows": len(dataset.votes),
        "prompts": len(dataset.prompts),
        "models": len(dataset.models),
        "observed_cells": int(np.isfinite(dataset.matrix).sum()),
        "density": float(np.isfinite(dataset.matrix).mean()),
        "both_bad_votes": int(dataset.both_bad_counts.sum()),
        "both_bad_vote_fraction": float(dataset.both_bad_counts.sum() / dataset.vote_counts.sum()),
        "vote_categories": {str(k): int(v) for k, v in dataset.votes["vote_type"].value_counts().items()},
        "coding": "win 1; loss 0; tie 0.5; both-bad 0 for both sides; cell is arithmetic observation mean",
        "local_export_counts": {"prompts_v1": len(prompt_records), "items_v1": len(item_records)},
        "firestore_populated": False,
        "fit": fitted.diagnostics,
    }
    (args.output / "source_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    print(json.dumps(manifest, indent=2, allow_nan=False))
    if not fitted.diagnostics["converged"]:
        raise SystemExit("The artifact was written, but optimization did not converge")


if __name__ == "__main__":
    main()
