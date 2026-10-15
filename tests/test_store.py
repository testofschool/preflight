import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from cloud.store import FirestoreDifficultyStore, StoreBudgetExhausted, StoreDataUnavailable, StoreRateLimited, prompt_id
from scripts.import_firestore import import_exports, read_export


class Snapshot:
    def __init__(self, reference, value):
        self.reference = reference
        self.exists = value is not None
        self.value = copy.deepcopy(value)

    def to_dict(self):
        return copy.deepcopy(self.value)


class Reference:
    def __init__(self, client, path):
        self.client = client
        self.path = path

    def get(self, transaction=None):
        return Snapshot(self, self.client.documents.get(self.path))

    def set(self, value, merge=False, timeout=None):
        existing = self.client.documents.get(self.path, {}) if merge else {}
        self.client.documents[self.path] = {**existing, **copy.deepcopy(value)}


class Collection:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def document(self, identifier):
        return Reference(self.client, self.name + "/" + identifier)

    def count(self):
        count = sum(path.startswith(self.name + "/") for path in self.client.documents)
        return SimpleNamespace(get=lambda timeout: [[SimpleNamespace(value=count)]])


class Writes:
    def __init__(self, client):
        self.client = client
        self.operations = []

    def set(self, reference, record, merge=False):
        self.operations.append((reference, record, merge))

    def commit(self, timeout=None):
        self.client.committed_batch_sizes.append(len(self.operations))
        for reference, record, merge in self.operations:
            reference.set(record, merge=merge)


class MemoryClient:
    def __init__(self):
        self.documents = {}
        self.committed_batch_sizes = []
        self.read_count = 0

    def collection(self, name):
        return Collection(self, name)

    def get_all(self, references, timeout=None):
        self.read_count += len(references)
        # Firestore does not promise requested snapshot order.
        return reversed([reference.get() for reference in references])

    def batch(self):
        return Writes(self)

    def transaction(self):
        return Writes(self)


def atomic_test_transaction(function):
    def run(transaction):
        result = function(transaction)
        transaction.commit()
        return result
    return run


class StoreTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict("os.environ", {"PREFLIGHT_TOTAL_REQUEST_LIMIT": "1000"})
        environment.start()
        self.addCleanup(environment.stop)
        self.client = MemoryClient()
        self.engine = SimpleNamespace(models=["A", "B"], ability=np.asarray([1.0, -1.0]))
        self.store = FirestoreDifficultyStore(self.client, transaction_decorator=atomic_test_transaction).attach(self.engine)
        self.result = {
            "supported": True,
            "p_fail": 0.99,
            "difficulty": 0,
            "discrimination": 1,
            "nearest_prompts": [{"prompt": f"prompt {i}", "similarity": 1 / (i + 1), "rate": 0.99} for i in range(5)],
            "reasons": [],
            "coverage": {},
        }
        for index in range(5):
            text = f"prompt {index}"
            identifier = prompt_id(text)
            self.client.collection("prompts_v1").document(identifier).set({"prompt": text, "both_bad_rate": index / 10, "both_bad_votes": index, "vote_count": 10})
            self.client.collection("items_v1").document(identifier).set({"prompt": text, "difficulty": float(index), "discrimination": 1.0})

    def test_prediction_reads_live_rates_and_item_parameters(self):
        response = self.store.live_risk(self.result, prompt="prompt 0")
        self.assertAlmostEqual(response["p_fail"], 0.2)
        self.assertEqual(response["difficulty"], 2.0)
        self.assertEqual(self.client.read_count, 10)
        self.assertEqual(self.result["p_fail"], 0.99)
        target = self.client.collection("prompts_v1").document(prompt_id("prompt 0"))
        target.set({"both_bad_rate": 1, "both_bad_votes": 10}, merge=True)
        second = self.store.live_risk(self.result)
        self.assertAlmostEqual(second["p_fail"], 0.4)
        self.assertEqual(self.client.read_count, 20)
        self.assertEqual(second["evidence_store"], "firestore")

    def test_missing_historical_document_fails_without_local_fallback(self):
        del self.client.documents["items_v1/" + prompt_id("prompt 3")]
        with self.assertRaises(StoreDataUnavailable):
            self.store.live_risk(self.result)

    def test_verdict_is_idempotent_and_preserves_human_counts(self):
        first = self.store.record_verdict("prompt 0", "A", False, [{"timecode": "00:01", "reason": "flicker"}], verdict_id="clip-review")
        second = self.store.record_verdict("prompt 0", "A", False, [{"timecode": "00:01", "reason": "flicker"}], verdict_id="clip-review")
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        record = self.client.documents["prompts_v1/" + prompt_id("prompt 0")]
        self.assertEqual(record["both_bad_votes"], 0)
        self.assertEqual(record["vote_count"], 10)
        self.assertEqual(record["postcheck_feedback"]["count"], 1)
        updated = self.store.live_risk(self.result, prompt="prompt 0")
        self.assertAlmostEqual(updated["historical_p_fail"], 0.2)
        self.assertGreater(updated["p_fail"], updated["historical_p_fail"])
        self.assertIn("MIXED", updated["risk_semantics"])
        with self.assertRaises(ValueError):
            self.store.record_verdict("prompt 0", "A", True, [], verdict_id="clip-review")
        self.assertEqual(record["postcheck_feedback"]["count"], 1)

    def test_unseen_prompt_feedback_adjusts_next_query_separately(self):
        self.store.record_verdict("new composition", "B", False, [], verdict_id="new-clip")
        updated = self.store.live_risk(self.result, prompt="new composition")
        self.assertAlmostEqual(updated["p_fail"], 11 / 51)
        self.assertAlmostEqual(updated["historical_p_fail"], 0.2)
        self.assertEqual(updated["postcheck_feedback"]["exact_unseen_prompt"]["postcheck_count"], 1)
        self.assertEqual(updated["postcheck_feedback"]["exact_unseen_prompt"]["prior_effective_count"], 50)

    def test_import_hash_identity_batches_and_feedback_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            prompts = [{"id": prompt_id(f"prompt {i}"), "prompt": f"prompt {i}", "both_bad_rate": 0.0, "both_bad_votes": 0, "vote_count": 10} for i in range(401)]
            items = [{"id": record["id"], "prompt": record["prompt"], "difficulty": 0, "discrimination": 1} for record in prompts]
            for name, rows in (("prompts_v1", prompts), ("items_v1", items)):
                (folder / (name + ".jsonl")).write_text("".join(json.dumps(row) + "\n" for row in rows))
            (folder / "engine.json").write_text(json.dumps({"schema_version": 1, "models": ["A"], "ability": [1], "fit_diagnostics": {"converged": True}}))
            self.store.record_verdict("prompt 0", "A", True, [], verdict_id="before-import")
            imported = import_exports(self.store, folder)
            self.assertEqual(imported["collection_counts"], {"prompts_v1": 401, "items_v1": 401, "verdicts_v1": 1})
            self.assertTrue(all(size <= 400 for size in self.client.committed_batch_sizes))
            self.assertEqual(self.client.documents["prompts_v1/" + prompt_id("prompt 0")]["postcheck_feedback"]["count"], 1)
            again = import_exports(self.store, folder)
            self.assertEqual(again["collection_counts"], imported["collection_counts"])
            prompts[0]["id"] = "wrong"
            (folder / "invalid.jsonl").write_text(json.dumps(prompts[0]))
            with self.assertRaises(ValueError):
                read_export(folder / "invalid.jsonl")

    def test_rolling_budget_shared_across_store_instances_and_rejection_is_atomic(self):
        second_instance = FirestoreDifficultyStore(self.client, transaction_decorator=atomic_test_transaction)
        with patch("cloud.store.time", return_value=1000.0):
            self.assertEqual(self.store.admit_request(limit=2)["remaining"], 1)
        with patch("cloud.store.time", return_value=1010.0):
            self.assertEqual(second_instance.admit_request(limit=2)["remaining"], 0)
        before = copy.deepcopy(self.client.documents["service_v1/global-budget"])
        with patch("cloud.store.time", return_value=1030.2):
            with self.assertRaises(StoreRateLimited) as caught:
                self.store.admit_request(limit=2)
            self.assertEqual(caught.exception.retry_after, 30)
        self.assertEqual(self.client.documents["service_v1/global-budget"], before)
        # The oldest request expires exactly at its sixty-second boundary.
        with patch("cloud.store.time", return_value=1060.0):
            admitted = second_instance.admit_request(limit=2)
        self.assertEqual(admitted["remaining"], 0)
        self.assertEqual(self.client.documents["service_v1/global-budget"]["request_timestamps"], [1010.0, 1060.0])
        self.assertEqual(self.client.documents["service_v1/global-budget"]["total_count"], 3)

    def test_cumulative_budget_survives_minute_expiration(self):
        with patch.dict("os.environ", {"PREFLIGHT_TOTAL_REQUEST_LIMIT": "2"}):
            with patch("cloud.store.time", return_value=1000.0):
                self.assertEqual(self.store.admit_request()["total_remaining"], 1)
            with patch("cloud.store.time", return_value=1061.0):
                admitted = self.store.admit_request()
                self.assertEqual(admitted["total_count"], 2)
                self.assertEqual(admitted["total_remaining"], 0)
            before = copy.deepcopy(self.client.documents["service_v1/global-budget"])
            with patch("cloud.store.time", return_value=2000.0):
                with self.assertRaises(StoreBudgetExhausted) as caught:
                    self.store.admit_request()
            self.assertFalse(hasattr(caught.exception, "retry_after"))
            self.assertEqual(self.client.documents["service_v1/global-budget"], before)

    def test_invalid_total_request_limit_fails_before_writing(self):
        for setting in ("0", "-1", "1.5", "invalid", "1001"):
            with self.subTest(setting=setting):
                with patch.dict("os.environ", {"PREFLIGHT_TOTAL_REQUEST_LIMIT": setting}):
                    with self.assertRaises(ValueError):
                        self.store.admit_request()
        self.assertNotIn("service_v1/global-budget", self.client.documents)


if __name__ == "__main__":
    unittest.main()
