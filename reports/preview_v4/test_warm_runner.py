"""Offline warm-path tests with a fake provider and in-memory Firestore store."""
import asyncio
import base64
from contextlib import nullcontext
from datetime import datetime
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import warm_preview_v4 as warm
from scripts import probe_preview_v4 as probe


class MemoryStore:
    def __init__(self):
        self.docs = {}

    def get_preview(self, key):
        return self.docs.get(key)

    def save_preview(self, key, data):
        self.docs[key] = data


class WarmSafetyTests(unittest.TestCase):
    def test_unknown_model_call_is_preserved_without_summary_error(self):
        report = warm.report_for([{"http_status": 503, "model_calls": None,
                                   "image_bytes": 0, "cache_saved": False}], "fixture")
        self.assertEqual(report["summary"]["unknown_call_rows"], 1)
        self.assertEqual(report["summary"]["new_image_attempts"], 1)

    def test_fixture_has_ten_actions_and_nine_exact_texts(self):
        actions = warm.actions()
        self.assertEqual(len(actions), 10)
        self.assertEqual(len({row["prompt"] for row in actions}), 9)
        self.assertEqual(actions[6]["prompt"], actions[7]["prompt"])

    def run_offline(self, failed_action=None):
        from PIL import Image
        from cloud.store import FirestoreDifficultyStore

        with tempfile.TemporaryDirectory(prefix="offline_warm_test_", dir=probe.REPORTS) as folder:
            reports = Path(folder)
            plan = json.loads((probe.REPORTS / "preregistration.json").read_text())
            (reports / "preregistration.json").write_text(json.dumps(plan))
            probe._append(reports / "call_ledger.jsonl", {"event": "baseline",
                "budget_date_kst": probe.DATE, "initial_image_calls": 44, "daily_cap": 85})
            raw = io.BytesIO()
            Image.frombytes("RGB", (256, 144), os.urandom(256 * 144 * 3)).save(raw, format="PNG")
            image_data = raw.getvalue()
            store = MemoryStore()
            calls = []
            reserve_original, append_original = probe.reserve_attempt, probe.append_result
            budget_original, model_original = probe.budget_state, probe.exclusive_model

            async def fake_provider(arm, prompt, project, report_dir, attempt_id, previous=0):
                calls.append(attempt_id)
                row = {"attempt_id": attempt_id, "arm": "P2", "model": warm.MODEL,
                       "http_status": 429 if attempt_id == failed_action else 200,
                       "started_at_kst": probe.now(), "finished_at_kst": probe.now(),
                       "latency_seconds": .01, "traffic_type": "ON_DEMAND",
                       "pass_image": attempt_id != failed_action,
                       "cost": {"list_price_usd": .03871}, "image_bytes": len(image_data)}
                if row["pass_image"]:
                    image_path = reports / (attempt_id + ".png")
                    image_path.write_bytes(image_data)
                    row.update(image_file=str(image_path.relative_to(ROOT)),
                               image_sha256=probe.sha(image_data))
                else:
                    row.update(error_class="ProviderHTTPError", image_bytes=0)
                return row

            with patch.object(warm, "REPORTS", reports), patch.object(warm, "SPACING", 0), \
                    patch.object(warm, "load_service_configuration", return_value="offline"), \
                    patch.object(probe, "validate", return_value={"valid": True}), \
                    patch.object(probe, "call_once", side_effect=fake_provider), \
                    patch.object(probe, "reserve_attempt", side_effect=lambda *args, **kwargs:
                                 reserve_original(*args, reports=reports)), \
                    patch.object(probe, "append_result", side_effect=lambda row:
                                 append_original(row, reports)), \
                    patch.object(probe, "budget_state", side_effect=lambda reports_arg=reports:
                                 budget_original(reports_arg)), \
                    patch.object(probe, "exclusive_model", side_effect=lambda model:
                                 model_original(model, reports)), \
                    patch.object(FirestoreDifficultyStore, "from_env", return_value=store):
                result = asyncio.run(warm.warm(SimpleNamespace(execute=True, limit=None)))
                before = list(calls)
                second = asyncio.run(warm.warm(SimpleNamespace(execute=True, limit=None)))
                self.assertEqual(calls, before, "A resumed warm must never repeat a dispatched prompt")
            self.assertEqual(len(result["rows"]), 10)
            self.assertEqual(result["rows"], second["rows"])
            self.assertEqual(len(calls), 9)
            self.assertEqual(budget_original(reports)["today_conservative_attempts"], 53)
            return result

    def test_successful_duplicate_uses_cache_and_rerun_makes_zero_calls(self):
        result = self.run_offline()
        self.assertTrue(result["summary"]["all_ten_actions_ready"])
        self.assertEqual(result["rows"][7]["model_calls"], 0)
        self.assertEqual(result["rows"][7]["cache"], "hit")
        self.assertTrue(all(10 * 1024 < row["image_bytes"] <= 900 * 1024 for row in result["rows"]))

    def test_failed_duplicate_is_recorded_twice_without_a_second_attempt(self):
        result = self.run_offline("WARM-07")
        self.assertFalse(result["summary"]["all_ten_actions_ready"])
        self.assertEqual(result["rows"][6]["http_status"], 429)
        self.assertEqual(result["rows"][7]["http_status"], 429)
        self.assertEqual(result["rows"][7]["model_calls"], 0)
        self.assertEqual(result["rows"][7]["error_class"], "PreviouslyDispatchedPromptNotRetried")

    def test_app_mode_sends_all_ten_requests_and_preserves_prior_direct_receipt(self):
        import httpx
        from PIL import Image
        from cloud.preview import sample_preview_cache_key

        raw = io.BytesIO()
        Image.frombytes("RGB", (256, 144), os.urandom(256 * 144 * 3)).save(raw, format="JPEG", quality=90)
        jpeg = raw.getvalue()
        sent, reservations, results = [], [], []
        seen = {"a cat and a dog"}

        class FakeClient:
            def __init__(self, **kwargs):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            async def post(self, url, json):
                assert json.get("variant") in ("original", "rewrite"), "PreviewInput requires variant"
                prompt = json["prompt"]
                sent.append(prompt)
                cache = "hit" if prompt in seen else "miss"
                seen.add(prompt)
                data = {"image_data_url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode(),
                        "model": warm.MODEL, "size": "1K", "model_calls": 0 if cache == "hit" else 1,
                        "cache": cache, "generated_at": probe.now(), "generated_date": probe.DATE,
                        "cost_usd": 0 if cache == "hit" else .03871}
                return SimpleNamespace(status_code=200, headers={"X-Preview-Cache": cache}, json=lambda: data)

        with tempfile.TemporaryDirectory(prefix="offline_app_warm_", dir=probe.REPORTS) as folder:
            reports = Path(folder)
            (reports / "preregistration.json").write_bytes((probe.REPORTS / "preregistration.json").read_bytes())
            original = {"fixture_sha256": probe.sha(warm.FIXTURE.read_bytes()), "rows": [
                {"action_id": "WARM-01", "prompt": "a cat and a dog", "variant": "original",
                 "http_status": 200, "image_bytes": len(jpeg), "model_calls": 1,
                 "cache_key": sample_preview_cache_key("a cat and a dog")} ]}
            old_bytes = json.dumps(original).encode()
            (reports / "warm.json").write_bytes(old_bytes)
            with patch.object(warm, "REPORTS", reports), patch.object(warm, "SPACING", 0), \
                    patch.object(warm, "runtime_budget_before_app_warm", return_value={"fits": True}) as budget_check, \
                    patch.object(probe, "validate", return_value={"valid": True}), \
                    patch.object(probe, "_read_rows", return_value=[]), \
                    patch.object(probe, "budget_state", return_value={"offline_test": True}), \
                    patch.object(probe, "reserve_attempt", side_effect=lambda *args: reservations.append(args)), \
                    patch.object(probe, "append_result", side_effect=lambda row: results.append(row)), \
                    patch.object(probe, "exclusive_model", return_value=nullcontext()), \
                    patch.object(httpx, "AsyncClient", FakeClient):
                args = SimpleNamespace(execute=True, url="https://offline.invalid", limit=None,
                                       remaining_qa_admissions=22)
                result = asyncio.run(warm.warm_through_app(args))
                budget_check.assert_called_once_with(10, 22)
            self.assertEqual(len(sent), 10)
            self.assertEqual(len(reservations), 10)
            self.assertEqual(len(results), 10)
            self.assertEqual(len(set(sent)), 9)
            self.assertEqual(result["summary"]["known_model_calls"], 8)
            self.assertTrue(result["summary"]["all_ten_actions_ready"])
            self.assertEqual((reports / "warm_direct_before_steering.json").read_bytes(), old_bytes)


if __name__ == "__main__":
    unittest.main()
