"""TF-IDF neighbours and historical item parameters for local prediction."""

import json
from pathlib import Path

import joblib
import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.feature_extraction.text import TfidfVectorizer

from .dataset import Dataset
from .irt import ItemFit


class PreflightEngine:
    def __init__(
        self,
        dataset: Dataset,
        fitted: ItemFit,
        vectorizer: TfidfVectorizer | None = None,
        tie_policy: str = "stable",
    ):
        self.prompts = dataset.prompts
        self.models = dataset.models
        self.rates = dataset.both_bad_rates
        self.vote_counts = dataset.vote_counts
        self.ability = fitted.ability
        self.difficulty = fitted.difficulty
        self.discrimination = fitted.discrimination
        self.fit_diagnostics = fitted.diagnostics
        self.tie_policy = tie_policy
        self.vectorizer = vectorizer or TfidfVectorizer(ngram_range=(1, 2))
        self.prompt_vectors = self.vectorizer.transform(self.prompts) if vectorizer is not None else self.vectorizer.fit_transform(self.prompts)

    def neighbours(self, prompt: str, count: int = 5) -> tuple[np.ndarray, np.ndarray, int]:
        encoded = self.vectorizer.transform([prompt])
        scores = (self.prompt_vectors @ encoded.T).toarray().ravel()
        # Stable ordering makes zero-similarity ties reproducible; no target is used.
        nearest = np.argsort(-scores, kind="stable" if self.tie_policy == "stable" else "quicksort")[: min(count, len(self.prompts))]
        return nearest, scores[nearest], int(encoded.nnz)

    def estimates(self, prompt: str) -> dict:
        indices, scores, tokens = self.neighbours(prompt)
        mean_difficulty = float(np.mean(self.difficulty[indices]))
        mean_discrimination = float(np.mean(self.discrimination[indices]))
        return {
            "indices": indices,
            "similarities": scores,
            "matched_features": tokens,
            "p_fail": float(np.mean(self.rates[indices])),
            "difficulty": mean_difficulty,
            "discrimination": mean_discrimination,
            "success": expit(mean_discrimination * (self.ability - mean_difficulty)),
        }

    def predict(self, prompt: str) -> dict:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("A nonempty prompt is required")
        computed = self.estimates(prompt)
        supported = computed["matched_features"] > 0
        neighbours = [
            {
                "prompt": self.prompts[int(index)],
                "rate": float(self.rates[index]),
                "both_bad_rate": float(self.rates[index]),
                "similarity": float(score),
                "vote_count": int(self.vote_counts[index]),
            }
            for index, score in zip(computed["indices"], computed["similarities"])
        ]
        coverage = {
            "matched_features": computed["matched_features"],
            "positive_similarity_neighbours": int(np.count_nonzero(computed["similarities"] > 0)),
            "max_similarity": float(np.max(computed["similarities"])),
            "mean_similarity": float(np.mean(computed["similarities"])),
            "neighbour_vote_count": int(np.sum(self.vote_counts[computed["indices"]])),
            "zero_similarity_ties_included": bool(np.any(computed["similarities"] == 0)),
        }
        reasons = [
            "Risk is the arithmetic mean of both-bad vote rates in five text neighbours from historical public data.",
            "These comparisons involve older video models; the score is not a calibrated chance that a new model fails.",
        ]
        if coverage["zero_similarity_ties_included"]:
            reasons.append("Some neighbours have zero text similarity and are included only by the fixed five-neighbour protocol.")
        if not supported:
            reasons.insert(0, "No prompt words match the historical vocabulary, so risk and IRT estimates are unavailable.")
        return {
            "p_fail": computed["p_fail"] if supported else None,
            "p_success_by_model": dict(zip(self.models, map(float, computed["success"]))) if supported else {},
            "nearest_prompts": neighbours,
            "difficulty": computed["difficulty"] if supported else None,
            "discrimination": computed["discrimination"] if supported else None,
            "reasons": reasons,
            "est_cost_usd": None,
            "supported": supported,
            "coverage": coverage,
        }

    def save(self, artifact_dir: str | Path) -> None:
        destination = Path(artifact_dir)
        destination.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": 1,
            "prompts": self.prompts,
            "models": self.models,
            "both_bad_rates": self.rates.tolist(),
            "vote_counts": self.vote_counts.tolist(),
            "ability": self.ability.tolist(),
            "difficulty": self.difficulty.tolist(),
            "discrimination": self.discrimination.tolist(),
            "fit_diagnostics": self.fit_diagnostics,
            "tie_policy": self.tie_policy,
            "risk_aggregation": "unweighted arithmetic mean of five nearest prompt both-bad vote rates",
        }
        (destination / "engine.json").write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")
        joblib.dump(self.vectorizer, destination / "vectorizer.joblib")
        sparse.save_npz(destination / "prompt_vectors.npz", self.prompt_vectors)

    @classmethod
    def load(cls, artifact_dir: str | Path) -> "PreflightEngine":
        source = Path(artifact_dir)
        document = json.loads((source / "engine.json").read_text())
        engine = cls.__new__(cls)
        engine.prompts = document["prompts"]
        engine.models = document["models"]
        engine.rates = np.asarray(document["both_bad_rates"], dtype=float)
        engine.vote_counts = np.asarray(document["vote_counts"], dtype=int)
        engine.ability = np.asarray(document["ability"], dtype=float)
        engine.difficulty = np.asarray(document["difficulty"], dtype=float)
        engine.discrimination = np.asarray(document["discrimination"], dtype=float)
        engine.fit_diagnostics = document["fit_diagnostics"]
        engine.tie_policy = document.get("tie_policy", "stable")
        engine.vectorizer = joblib.load(source / "vectorizer.joblib")
        engine.prompt_vectors = sparse.load_npz(source / "prompt_vectors.npz")
        if engine.prompt_vectors.shape[0] != len(engine.prompts):
            raise ValueError("Prompt-vector count does not match engine metadata")
        return engine
