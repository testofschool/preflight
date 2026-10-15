import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from preflight_core import PreflightEngine, read_votes
from preflight_core.irt import fit_items


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        rows = [
            ("red bird", "A", "B", "leftvote"),
            ("red bird", "A", "B", "tievote"),
            ("red bird", "A", "B", "bothbad_vote"),
            ("blue bird", "A", "B", "rightvote"),
            ("a green tree", "A", "B", "bothbad_vote"),
            ("yellow car", "A", "B", "tievote"),
            ("purple moon", "A", "B", "leftvote"),
            ("silver boat", "A", "B", "rightvote"),
        ]
        pd.DataFrame(rows, columns=["prompt", "left_model", "right_model", "vote_type"]).to_parquet(self.directory / "votes.parquet")
        self.dataset = read_votes(self.directory / "votes.parquet")

    def tearDown(self):
        self.temporary.cleanup()

    def test_outcome_coding_and_counts(self):
        index = self.dataset.prompts.index("red bird")
        np.testing.assert_allclose(self.dataset.matrix[index], [0.5, 1 / 6])
        np.testing.assert_array_equal(self.dataset.observation_counts[index], [3, 3])
        self.assertEqual(self.dataset.vote_counts[index], 3)
        self.assertEqual(self.dataset.both_bad_rates[index], 1 / 3)

    def test_unknown_category_rejected(self):
        source = self.dataset.votes.copy()
        source.loc[0, "vote_type"] = "unrecognized"
        source.to_parquet(self.directory / "invalid.parquet")
        with self.assertRaises(ValueError):
            read_votes(self.directory / "invalid.parquet")

    def test_probability_bounds_and_no_prompt_model_routing(self):
        fitted = fit_items(self.dataset.matrix)
        self.assertTrue(fitted.diagnostics["converged"])
        self.assertTrue(np.all((fitted.discrimination >= 0.3) & (fitted.discrimination <= 4)))
        self.assertTrue(np.all((fitted.probabilities() > 0) & (fitted.probabilities() < 1)))
        self.assertTrue(np.all(np.argmax(fitted.probabilities(), axis=1) == np.argmax(fitted.ability)))

    def test_neighbour_mean_roundtrip_and_oov_abstention(self):
        predictor = PreflightEngine(self.dataset, fit_items(self.dataset.matrix))
        indices, similarities, _ = predictor.neighbours("red bird")
        result = predictor.predict("red bird")
        self.assertEqual(result["p_fail"], float(np.mean(self.dataset.both_bad_rates[indices])))
        self.assertTrue(result["supported"])
        self.assertEqual(result["nearest_prompts"][0]["prompt"], "red bird")
        self.assertGreater(similarities[0], 0.99)
        predictor.save(self.directory / "saved")
        restored = PreflightEngine.load(self.directory / "saved")
        self.assertEqual(result, restored.predict("red bird"))
        unavailable = restored.predict("zzzzqxxxwwvv")
        self.assertFalse(unavailable["supported"])
        self.assertIsNone(unavailable["p_fail"])
        self.assertEqual(unavailable["p_success_by_model"], {})
        self.assertNotIn("rewritten_prompt", unavailable)

    def test_training_partition_excludes_heldout_vocabulary(self):
        subset = self.dataset.subset(np.asarray([i for i, text in enumerate(self.dataset.prompts) if text != "purple moon"]))
        predictor = PreflightEngine(subset, fit_items(subset.matrix))
        self.assertNotIn("purple", predictor.vectorizer.vocabulary_)
        self.assertEqual(predictor.predict("purple moon")["coverage"]["matched_features"], 0)


if __name__ == "__main__":
    unittest.main()
