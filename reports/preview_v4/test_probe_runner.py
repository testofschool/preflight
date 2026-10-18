"""Offline safety checks: no provider clients or network access are used."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("probe_v4", ROOT / "scripts/probe_preview_v4.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class ProbeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="offline_probe_test_", dir=ROOT / "reports/preview_v4")
        self.reports = Path(self.temp.name)
        probe._append(self.reports / "call_ledger.jsonl", {
            "event": "baseline", "budget_date_kst": probe.DATE,
            "initial_image_calls": 44, "daily_cap": 85})
        self.plan = json.loads((probe.REPORTS / "preregistration.json").read_text())
        (self.reports / "preregistration.json").write_text(json.dumps(self.plan))

    def tearDown(self):
        self.temp.cleanup()

    def reserve(self, i):
        return probe.reserve_attempt(f"test-{i}", "model", "offline_test", "a" * 64, self.reports)

    def test_unknown_attempt_stays_charged_and_cannot_retry(self):
        self.reserve(1)
        self.assertEqual(probe.budget_state(self.reports)["today_conservative_attempts"], 45)
        with self.assertRaisesRegex(ValueError, "already reserved"):
            self.reserve(1)

    def test_preregistration_cannot_change_after_first_reservation(self):
        self.reserve(1)
        plan_path = self.reports / "preregistration.json"
        plan_path.write_text(plan_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "Preregistration changed"):
            self.reserve(2)

    def test_concurrent_reservations_cannot_cross_cap(self):
        def try_reserve(i):
            try:
                self.reserve(i)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(try_reserve, range(60)))
        self.assertEqual(sum(results), 41)
        self.assertEqual(probe.budget_state(self.reports)["today_conservative_attempts"], 85)

    def test_v4_scope_amendment_preserves_existing_call_and_excludes_v3(self):
        self.reserve(0)
        amendment = {"scope": "preview_v4_only", "daily_cap": 85,
                     "initial_image_calls": 0, "historical_v3_attempts_excluded": 44}
        path = self.reports / "budget_amendment_001.json"
        path.write_text(json.dumps(amendment))
        probe._append(self.reports / "call_ledger.jsonl", {"event": "budget_amendment",
                      "file": path.name, "sha256": probe.sha(path.read_bytes())})
        state = probe.budget_state(self.reports)
        self.assertEqual(state["today_conservative_attempts"], 1)
        self.assertEqual(state["all_runs_today_conservative_attempts"], 45)
        self.assertEqual(state["remaining"], 84)
        for i in range(1, 85):
            self.reserve(i)
        self.assertEqual(probe.budget_state(self.reports)["today_conservative_attempts"], 85)
        with self.assertRaisesRegex(ValueError, "cap reached"):
            self.reserve(85)
        path.write_text(path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "amendment differs"):
            probe.budget_state(self.reports)

    def test_result_requires_reservation_and_cannot_duplicate(self):
        with self.assertRaisesRegex(ValueError, "No durable reservation"):
            probe.append_result({"attempt_id": "missing"}, self.reports)
        self.reserve(1)
        probe.append_result({"attempt_id": "test-1", "http_status": 429}, self.reports)
        with self.assertRaisesRegex(ValueError, "already exists"):
            probe.append_result({"attempt_id": "test-1", "http_status": 200}, self.reports)

    def test_model_cannot_overlap_itself(self):
        with probe.exclusive_model("P1-model", self.reports):
            with self.assertRaisesRegex(ValueError, "Another run"):
                with probe.exclusive_model("P1-model", self.reports):
                    self.fail("Same model acquired the exclusive lock twice")
            with probe.exclusive_model("other-model", self.reports):
                pass

    def test_only_verified_qa_cache_hit_refunds_potential_call(self):
        for i, purpose, status, cache, calls in ((1, "qa", 200, "hit", 0),
                                                (2, "qa", 503, "hit", 0),
                                                (3, "probe", 200, "hit", 0),
                                                (4, "qa", 200, "hit", None)):
            probe.reserve_attempt(f"refund-{i}", "model", purpose, "a" * 64, self.reports)
            probe.append_result({"attempt_id": f"refund-{i}", "http_status": status,
                                 "cache": cache, "model_calls": calls}, self.reports)
        state = probe.budget_state(self.reports)
        self.assertEqual(state["v4_reserved_attempts"], 4)
        self.assertEqual(state["verified_zero_call_qa_hits"], 1)
        self.assertEqual(state["today_conservative_attempts"], 47)
        with self.assertRaisesRegex(ValueError, "already reserved"):
            probe.reserve_attempt("refund-1", "model", "qa", "a" * 64, self.reports)

    def add_rows(self, arm, n, successes, price):
        for i in range(n):
            probe._append(self.reports / "call_ledger.jsonl", {
                "event": "attempt_result", "attempt_id": f"{arm}-{i + 1:02}", "arm": arm,
                "pass_image": i < successes, "cost": {"list_price_usd": price}})

    def test_19_of_19_is_incomplete(self):
        self.add_rows("P1", 19, 19, .06048)
        decision = probe.summarize(self.reports)
        self.assertFalse(decision["live_generation_allowed"])
        self.assertEqual(decision["arms"][0]["status"], "incomplete")

    def test_higher_success_count_precedes_price(self):
        self.add_rows("P1", 20, 20, .06048)
        self.add_rows("P2", 20, 19, .0387)
        self.assertEqual(probe.summarize(self.reports)["selected_arm"], "P1")

    def test_price_breaks_success_tie(self):
        self.add_rows("P2", 20, 20, .0387)
        self.add_rows("P3", 20, 20, .04482)
        self.assertEqual(probe.summarize(self.reports)["selected_arm"], "P2")

    def test_priority_cost_tracks_returned_traffic_type(self):
        arm = self.plan["arms"][0]
        usage = {"promptTokenCount": 100, "candidatesTokensDetails": [
            {"modality": "IMAGE", "tokenCount": 1120}], "trafficType": "ON_DEMAND_PRIORITY"}
        priority = probe._cost(arm, usage, 1)["list_price_usd"]
        usage["trafficType"] = "ON_DEMAND"
        standard = probe._cost(arm, usage, 1)["list_price_usd"]
        self.assertAlmostEqual(priority / standard, 1.8)
        usage.pop("trafficType")
        self.assertIsNone(probe._cost(arm, usage, 1)["list_price_usd"])

    def test_run_without_execute_cannot_call_provider(self):
        args = SimpleNamespace(reports=probe.REPORTS, arm="P1", execute=False, limit=None)
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "offline-test"}):
            with self.assertRaisesRegex(ValueError, "explicit --execute"):
                asyncio.run(probe.run_arm(args))


if __name__ == "__main__":
    unittest.main()
