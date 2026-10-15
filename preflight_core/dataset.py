"""Convert public pairwise judgements into the preregistered cell outcomes."""

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import numpy as np
import pandas as pd


@dataclass
class Dataset:
    prompts: list[str]
    models: list[str]
    matrix: np.ndarray
    observation_counts: np.ndarray
    both_bad_rates: np.ndarray
    vote_counts: np.ndarray
    both_bad_counts: np.ndarray
    votes: pd.DataFrame

    def subset(self, indices: np.ndarray) -> "Dataset":
        return Dataset(
            prompts=[self.prompts[int(i)] for i in indices],
            models=self.models.copy(),
            matrix=self.matrix[indices].copy(),
            observation_counts=self.observation_counts[indices].copy(),
            both_bad_rates=self.both_bad_rates[indices].copy(),
            vote_counts=self.vote_counts[indices].copy(),
            both_bad_counts=self.both_bad_counts[indices].copy(),
            votes=self.votes[self.votes["prompt"].isin([self.prompts[int(i)] for i in indices])].copy(),
        )


def read_votes(path: str | Path | BinaryIO) -> Dataset:
    votes = pd.read_parquet(path)
    required = {"prompt", "left_model", "right_model", "vote_type"}
    if not required.issubset(votes.columns):
        raise ValueError("The vote table is missing required columns")
    if votes[list(required)].isna().any().any():
        raise ValueError("Missing vote fields are not valid observations")
    scoring = {
        "leftvote": (1.0, 0.0),
        "rightvote": (0.0, 1.0),
        "tievote": (0.5, 0.5),
        "bothbad_vote": (0.0, 0.0),
    }
    if not set(votes["vote_type"]).issubset(scoring):
        raise ValueError("Unrecognized vote categories")
    prompts = sorted(votes["prompt"].unique().tolist())
    models = sorted(set(votes["left_model"]) | set(votes["right_model"]))
    prompt_index = {value: index for index, value in enumerate(prompts)}
    model_index = {value: index for index, value in enumerate(models)}
    sums = np.zeros((len(prompts), len(models)), dtype=float)
    counts = np.zeros(sums.shape, dtype=int)
    totals = np.zeros(len(prompts), dtype=int)
    rejected = np.zeros(len(prompts), dtype=int)
    for row in votes.itertuples(index=False):
        prompt_id = prompt_index[row.prompt]
        totals[prompt_id] += 1
        rejected[prompt_id] += int(row.vote_type == "bothbad_vote")
        for name, value in zip((row.left_model, row.right_model), scoring[row.vote_type]):
            model_id = model_index[name]
            sums[prompt_id, model_id] += value
            counts[prompt_id, model_id] += 1
    outcomes = np.full(sums.shape, np.nan)
    np.divide(sums, counts, out=outcomes, where=counts > 0)
    return Dataset(prompts, models, outcomes, counts, rejected / totals, totals, rejected, votes)
