"""Offline synthetic verifier regressions; no owner fixtures or cloud calls."""

import copy
from datetime import datetime, timezone
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

import scripts.verify_postcheck as verifier


def synthetic_reference(tmp_path, count=3):
    clips = []
    for index in range(count):
        source = tmp_path / f"synthetic-unit-{index}.mp4"
        source.write_bytes(f"SYNTHETIC UNIT TEST BYTES {index}".encode())
        clips.append({
            "id": f"synthetic-{index}", "path": str(source),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "duration_seconds": 10.0, "prompt": "Synthetic neutral test scene", "model": "synthetic test model",
            "known_defects": [{"id": "synthetic-label", "category": "physics", "seconds": 2.0, "confidence": "confirmed", "reason": "Synthetic label for an offline unit test only."}],
        })
    return {
        "schema_version": 1, "frozen_at_utc": "2020-01-01T00:00:00+00:00",
        "owner_confirmed": True,
        "label_provenance": "SYNTHETIC UNIT TEST ONLY; this is not an actual human-owner attestation",
        "tolerance_seconds": 2,
        "pass_rule": {"minimum_matched_defects": 2, "required_clips": 3, "one_to_one": True},
        "clips": clips,
    }


def fresh_receipt(clip):
    return {
        "http_status": 200, "started_at_utc": "2020-01-02T00:00:00+00:00", "elapsed_seconds": 1.0,
        "response": {
            "source_sha256": clip["sha256"], "pass_bool": False,
            "defects": [{"category": "physics", "seconds": 2.0, "timecode": "00:02", "reason": "Synthetic model observation."}],
            "analysis": {"sampling_fps": 2, "backend": "vertex", "actual_model_calls": 2},
            "model_calls_this_request": 2, "reused_stored_review": False,
            "concurrent_review_discarded": False, "feedback_recorded": True, "feedback_created": True,
        },
    }


def test_partial_is_explicit_and_never_changes_full_rule(tmp_path):
    for count in (1, 2):
        reference = synthetic_reference(tmp_path, count)
        with pytest.raises(ValueError, match="Exactly three"):
            verifier.validate_reference(reference)
        clips = verifier.validate_reference(reference, allow_partial=True)
        rows = [{"checks": verifier.assess_clip(clip, fresh_receipt(clip), frozen_at_utc=reference["frozen_at_utc"])} for clip in clips]
        summary = verifier.summarize(rows)
        assert summary["status"] == "PARTIAL" and summary["V8_pass"] is None
        assert summary["mechanical_match_pass"] is None
        assert summary["required_clips"] == 3 and summary["minimum_matched_defects"] == 2
        assert summary["tolerance_seconds"] == 2 and summary["one_to_one"] is True


def test_full_three_keeps_mechanical_rule_and_requires_manual_reason_review(tmp_path):
    reference = synthetic_reference(tmp_path)
    clips = verifier.validate_reference(reference)
    rows = [{"checks": verifier.assess_clip(clip, fresh_receipt(clip), frozen_at_utc=reference["frozen_at_utc"])} for clip in clips]
    summary = verifier.summarize(rows)
    assert summary["V8_pass"] is None and summary["mechanical_match_pass"] is True and summary["matched_defects"] == 3
    assert summary["status"] == "MECHANICAL_PASS_PENDING_MANUAL_REVIEW"
    assert summary["manual_reason_review_status"] == "REQUIRED_NOT_PERFORMED_BY_THIS_HELPER"
    assert summary["accuracy_claim_status"] == "NOT_ESTABLISHED_BY_THIS_HELPER"


def test_known_model_call_counts_are_separate_from_three_clip_cohort_completeness(tmp_path):
    reference = synthetic_reference(tmp_path, 2)
    rows = [{"checks": verifier.assess_clip(clip, fresh_receipt(clip), frozen_at_utc=reference["frozen_at_utc"])} for clip in reference["clips"]]
    result = verifier.summarize(rows)
    assert result["model_call_count_complete"] is True
    assert result["reported_model_calls_for_this_batch"] == 4
    assert result["cohort_complete"] is False and result["status"] == "PARTIAL"
    rows[0]["checks"]["model_calls_for_this_request"] = None
    assert verifier.summarize(rows)["model_call_count_complete"] is False
    assert verifier.summarize([])["model_call_count_complete"] is False


def test_human_owner_confirmation_cannot_be_inferred_from_assistant_notes(tmp_path):
    reference = synthetic_reference(tmp_path)
    del reference["owner_confirmed"]
    with pytest.raises(ValueError, match="human-owner"):
        verifier.validate_reference(reference)


def test_frozen_timestamp_requires_timezone_and_cannot_be_future(tmp_path):
    reference = synthetic_reference(tmp_path)
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    for invalid in ("not-a-date", "2020-01-01T00:00:00", "2026-10-17T00:00:00Z"):
        reference["frozen_at_utc"] = invalid
        with pytest.raises(ValueError, match="timestamp|timezone|future"):
            verifier.validate_reference(reference, now=now)
    reference["frozen_at_utc"] = "2026-10-16T08:00:00+09:00"
    assert len(verifier.validate_reference(reference, now=now)) == 3


@pytest.mark.parametrize("changes", [
    {"model_calls_this_request": 0, "reused_stored_review": True},
    {"model_calls_this_request": 2, "reused_stored_review": True},
    {"model_calls_this_request": 2, "concurrent_review_discarded": True},
    {"model_calls_this_request": 1},
    {"concurrent_review_discarded": None},
])
def test_cached_or_discarded_or_nonfresh_reviews_receive_zero_credit(tmp_path, changes):
    reference = synthetic_reference(tmp_path)
    clip = reference["clips"][0]
    receipt = fresh_receipt(clip)
    receipt["response"].update(changes)
    checked = verifier.assess_clip(clip, receipt, frozen_at_utc=reference["frozen_at_utc"])
    assert checked["verified_response"]
    assert checked["v8_credit_eligible"] is False and checked["matched_defects"] == 0


def test_reference_after_request_cannot_credit_a_fresh_response(tmp_path):
    clip = synthetic_reference(tmp_path)["clips"][0]
    checked = verifier.assess_clip(clip, fresh_receipt(clip), frozen_at_utc="2020-01-03T00:00:00+00:00")
    assert checked["reference_precedes_request"] is False and checked["matched_defects"] == 0


def test_one_to_one_matcher_uses_augmenting_paths_and_cannot_double_count():
    expected = [{"category": "flicker", "seconds": 2.0}, {"category": "flicker", "seconds": 5.0}]
    predicted = [{"category": "flicker", "seconds": 3.5}, {"category": "flicker", "seconds": 0.2}]
    assert verifier.match_defects(expected, predicted)["matched_defects"] == 2
    assert verifier.match_defects(expected, predicted[:1])["matched_defects"] == 1


def test_attempt_ledger_blocks_unknown_repeats_changed_labels_and_concurrent_starts(tmp_path):
    path = tmp_path / "external-ledger.json"
    identity, labels = "a" * 64, "b" * 64
    first = verifier.AttemptLedger(path)
    first.begin(identity, labels, "c" * 64)
    assert json.loads(path.read_text())["sources"][identity]["status"] == "ATTEMPT_STARTED"
    with pytest.raises(ValueError, match="already reviewed or attempted"):
        verifier.AttemptLedger(path).begin(identity, labels, "c" * 64)
    with pytest.raises(ValueError, match="Labels changed"):
        verifier.AttemptLedger(path).begin(identity, "d" * 64, "c" * 64)
    assert list(json.loads(path.read_text())["sources"]) == [identity]
    race_path = tmp_path / "race-ledger.json"

    def start(_index):
        try:
            verifier.AttemptLedger(race_path).begin(identity, labels, "c" * 64)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(start, range(2))) == 1


def test_prior_review_receipts_block_new_labels_instead_of_reusing_cached_predictions(tmp_path):
    reference = synthetic_reference(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    old = [fresh_receipt(clip) for clip in reference["clips"][:2]]
    (reports / "synthetic-prior-reviews.json").write_text(json.dumps(old))
    prior = verifier.prior_review_sources(reports)
    assert set(prior) == {clip["sha256"] for clip in reference["clips"][:2]}
    ledger_path = tmp_path / "attempt-ledger.json"
    ledger = verifier.AttemptLedger(ledger_path, prior)
    labels = {clip["sha256"]: verifier.label_hash(reference, clip) for clip in reference["clips"]}
    with pytest.raises(ValueError, match="already reviewed"):
        ledger.check_available(reference["clips"], labels)
    assert json.loads(ledger_path.read_text())["sources"][reference["clips"][0]["sha256"]]["status"] == "PRIOR_MODEL_REVIEW_OBSERVED"


def test_cli_partial_persists_started_before_post_and_new_output_filename_cannot_retry(tmp_path, monkeypatch):
    reference = synthetic_reference(tmp_path, 1)
    path = tmp_path / "synthetic-reference.json"
    path.write_text(json.dumps(reference))
    ledger_path = tmp_path / "external-ledger.json"
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "ATTEMPT_LEDGER", ledger_path)
    sent = []

    def request(_endpoint, clip, _source):
        entry = json.loads(ledger_path.read_text())["sources"][clip["sha256"]]
        assert entry["status"] == "ATTEMPT_STARTED" and entry["label_sha256"] == verifier.label_hash(reference, clip)
        sent.append(clip["sha256"])
        return fresh_receipt(clip)

    monkeypatch.setattr(verifier, "request_once", request)
    monkeypatch.setattr(verifier.sys, "argv", ["verify_postcheck.py", "--url", "https://example.invalid", "--reference", str(path), "--allow-partial"])
    assert verifier.main() == 3
    assert len(sent) == 1
    report = json.loads((tmp_path / "reports" / "postcheck_live.json").read_text())
    assert report["summary"]["V8_pass"] is None and report["summary"]["status"] == "PARTIAL"
    assert json.loads(ledger_path.read_text())["sources"][sent[0]]["status"] == "ATTEMPT_FINISHED"
    monkeypatch.setattr(verifier.sys, "argv", ["verify_postcheck.py", "--url", "https://example.invalid", "--reference", str(path), "--allow-partial", "--report", str(tmp_path / "new-name.json"), "--log", str(tmp_path / "new-name.txt")])
    with pytest.raises(ValueError, match="already reviewed"):
        verifier.main()
    assert len(sent) == 1


def test_interruption_leaves_source_started_and_ineligible_for_resend(tmp_path, monkeypatch):
    reference = synthetic_reference(tmp_path, 1)
    path = tmp_path / "synthetic-reference.json"
    path.write_text(json.dumps(reference))
    ledger_path = tmp_path / "external-ledger.json"
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "ATTEMPT_LEDGER", ledger_path)
    monkeypatch.setattr(verifier, "request_once", lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(verifier.sys, "argv", ["verify_postcheck.py", "--url", "https://example.invalid", "--reference", str(path), "--allow-partial"])
    assert verifier.main() == 130
    assert json.loads(ledger_path.read_text())["sources"][reference["clips"][0]["sha256"]]["status"] == "ATTEMPT_STARTED"


def test_invalid_future_freeze_never_reaches_network(tmp_path, monkeypatch):
    reference = synthetic_reference(tmp_path)
    reference["frozen_at_utc"] = "2100-01-01T00:00:00Z"
    path = tmp_path / "synthetic-reference.json"
    path.write_text(json.dumps(reference))
    called = []
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "ATTEMPT_LEDGER", tmp_path / "must-not-exist.json")
    monkeypatch.setattr(verifier, "request_once", lambda *_args: called.append(True))
    monkeypatch.setattr(verifier.sys, "argv", ["verify_postcheck.py", "--url", "https://example.invalid", "--reference", str(path)])
    with pytest.raises(ValueError, match="future"):
        verifier.main()
    assert not called and not (tmp_path / "must-not-exist.json").exists()


@pytest.mark.parametrize("has_matches,expected_exit", [(True, 3), (False, 1)])
def test_full_cli_cannot_return_success_without_manual_adjudication(tmp_path, monkeypatch, has_matches, expected_exit):
    reference = synthetic_reference(tmp_path)
    path = tmp_path / "synthetic-reference.json"
    path.write_text(json.dumps(reference))
    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "ATTEMPT_LEDGER", tmp_path / "external-ledger.json")

    def request(_endpoint, clip, _source):
        receipt = fresh_receipt(clip)
        if not has_matches:
            receipt["response"]["defects"] = []
            receipt["response"]["pass_bool"] = True
        return receipt

    monkeypatch.setattr(verifier, "request_once", request)
    monkeypatch.setattr(verifier.sys, "argv", ["verify_postcheck.py", "--url", "https://example.invalid", "--reference", str(path)])
    assert verifier.main() == expected_exit
    report = json.loads((tmp_path / "reports" / "postcheck_live.json").read_text())
    assert report["summary"]["mechanical_match_pass"] is has_matches
    assert report["summary"]["V8_pass"] is (None if has_matches else False)
    assert report["summary"]["status"] == ("MECHANICAL_PASS_PENDING_MANUAL_REVIEW" if has_matches else "MECHANICAL_FAIL")
