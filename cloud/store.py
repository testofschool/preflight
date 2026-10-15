"""Firestore-backed historical evidence and separately identified clip feedback."""

import copy
import hashlib
import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from time import time

import numpy as np
from scipy.special import expit


def prompt_id(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


class StoreDataUnavailable(RuntimeError):
    """A required historical document is absent or inconsistent."""


class StoreRateLimited(RuntimeError):
    def __init__(self, retry_after: int):
        super().__init__("The shared request budget has been reached")
        self.retry_after = max(1, int(retry_after))


class StoreBudgetExhausted(RuntimeError):
    """The durable admitted-request allowance has been consumed."""


def feedback_adjustment(document: dict) -> dict:
    """Keep human pairwise counts and single-clip feedback distinguishable."""
    count = int(document.get("vote_count", 0))
    bad = int(document.get("both_bad_votes", 0))
    feedback = document.get("postcheck_feedback", {})
    feedback_count = int(feedback.get("count", 0))
    failures = int(feedback.get("failures", 0))
    if count < 0 or bad < 0 or bad > count or feedback_count < 0 or failures < 0 or failures > feedback_count:
        raise StoreDataUnavailable("Evidence counters are inconsistent")
    historical = float(document["both_bad_rate"]) if count else None
    if historical is not None and (not np.isfinite(historical) or not 0 <= historical <= 1):
        raise StoreDataUnavailable("Historical vote rate is invalid")
    if historical is not None and abs(historical - bad / count) > 1e-9:
        raise StoreDataUnavailable("Historical counts and rate disagree")
    adjusted = (bad + failures) / (count + feedback_count) if count + feedback_count else None
    return {
        "historical_rate": historical,
        "historical_vote_count": count,
        "postcheck_count": feedback_count,
        "postcheck_failures": failures,
        "postcheck_failure_rate": failures / feedback_count if feedback_count else None,
        "risk_rate": float(adjusted) if adjusted is not None else None,
    }


class FirestoreDifficultyStore:
    """Synchronous API: use a FastAPI sync route or asyncio.to_thread."""

    def __init__(self, client, transaction_decorator=None):
        self.client = client
        self.engine = None
        self.transaction_decorator = transaction_decorator

    @classmethod
    def from_env(cls, credentials=None) -> "FirestoreDifficultyStore":
        from google.cloud import firestore

        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise ValueError("The cloud project runtime setting is required")
        database = os.environ.get("PREFLIGHT_FIRESTORE_DATABASE", "preflight-aibc")
        if database == "(default)":
            raise ValueError("A dedicated Firestore database is required")
        return cls(firestore.Client(project=project, database=database, credentials=credentials))

    def attach(self, engine) -> "FirestoreDifficultyStore":
        self.engine = engine
        return self

    def admit_request(self, limit: int = 20) -> dict:
        """Atomically share a rolling one-minute request budget across instances."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("The shared request limit must be a positive integer")
        try:
            total_limit = int(os.environ.get("PREFLIGHT_TOTAL_REQUEST_LIMIT", "1000"))
        except (TypeError, ValueError):
            raise ValueError("The total request limit must be a positive integer") from None
        if not 1 <= total_limit <= 1000:
            raise ValueError("The total request limit must be between one and 1000")
        reference = self.client.collection("service_v1").document("global-budget")
        decorator = self.transaction_decorator
        if decorator is None:
            from google.cloud import firestore

            decorator = firestore.transactional

        @decorator
        def admit(transaction):
            now = time()
            snapshot = reference.get(transaction=transaction)
            document = snapshot.to_dict() if snapshot.exists else {}
            total_count = document.get("total_count", 0)
            if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0:
                raise StoreDataUnavailable("The total request counter is invalid")
            if total_count >= total_limit:
                raise StoreBudgetExhausted("The cumulative preview request allowance is exhausted")
            timestamps = sorted(float(value) for value in document.get("request_timestamps", []) if float(value) > now - 60)
            if not all(math.isfinite(value) for value in timestamps):
                raise StoreDataUnavailable("The shared request budget is invalid")
            if len(timestamps) >= limit:
                raise StoreRateLimited(math.ceil(timestamps[0] + 60 - now))
            timestamps.append(now)
            total_count += 1
            transaction.set(reference, {"request_timestamps": timestamps, "window_seconds": 60, "limit": limit, "total_count": total_count, "total_request_limit": total_limit}, merge=True)
            return {"remaining": limit - len(timestamps), "reset_after_seconds": max(1, math.ceil(timestamps[0] + 60 - now)), "total_count": total_count, "total_remaining": total_limit - total_count}

        return admit(self.client.transaction())

    def live_risk(self, engine_result: dict, prompt: str | None = None) -> dict:
        """Read all five neighbour rates and item parameters on every supported query."""
        result = copy.deepcopy(engine_result)
        if not result.get("supported"):
            result["evidence_store"] = "firestore; query abstained before historical lookup"
            return result
        if self.engine is None:
            raise RuntimeError("Attach the bundled vector engine before live prediction")
        neighbours = result.get("nearest_prompts", [])
        if len(neighbours) != 5:
            raise StoreDataUnavailable("Five historical neighbours are required")
        ids = [prompt_id(item["prompt"]) for item in neighbours]
        references = [self.client.collection(name).document(identifier) for name in ("prompts_v1", "items_v1") for identifier in ids]
        exact_id = prompt_id(prompt) if prompt else None
        exact_extra = bool(exact_id and exact_id not in ids)
        if exact_extra:
            references.append(self.client.collection("prompts_v1").document(exact_id))
        snapshots = list(self.client.get_all(references, timeout=10))
        records = {snapshot.reference.path: snapshot.to_dict() for snapshot in snapshots if snapshot.exists}
        historical_rates, adjusted_rates, difficulties, discriminations = [], [], [], []
        all_feedback_count = 0
        all_feedback_failures = 0
        for neighbour, identifier in zip(neighbours, ids):
            historical_doc = records.get(f"prompts_v1/{identifier}")
            item_doc = records.get(f"items_v1/{identifier}")
            if not historical_doc or not item_doc:
                raise StoreDataUnavailable("Historical Firestore evidence has not been fully imported")
            if historical_doc.get("prompt") != neighbour["prompt"] or item_doc.get("prompt") != neighbour["prompt"]:
                raise StoreDataUnavailable("Historical prompt identity does not match")
            evidence = feedback_adjustment(historical_doc)
            if evidence["historical_rate"] is None:
                raise StoreDataUnavailable("A historical neighbour has no human votes")
            difficulty = float(item_doc["difficulty"])
            discrimination = float(item_doc["discrimination"])
            if not np.isfinite(difficulty) or not np.isfinite(discrimination) or not 0.3 <= discrimination <= 4:
                raise StoreDataUnavailable("Stored item parameters are invalid")
            historical_rates.append(evidence["historical_rate"])
            adjusted_rates.append(evidence["risk_rate"])
            difficulties.append(difficulty)
            discriminations.append(discrimination)
            all_feedback_count += evidence["postcheck_count"]
            all_feedback_failures += evidence["postcheck_failures"]
            neighbour.update(
                rate=evidence["historical_rate"],
                both_bad_rate=evidence["historical_rate"],
                risk_rate=evidence["risk_rate"],
                vote_count=evidence["historical_vote_count"],
                postcheck_count=evidence["postcheck_count"],
                postcheck_failures=evidence["postcheck_failures"],
                postcheck_failure_rate=evidence["postcheck_failure_rate"],
                evidence_store="firestore",
            )
        historical_risk = float(np.mean(historical_rates))
        mixed_risk = float(np.mean(adjusted_rates))
        exact_feedback = None
        if exact_extra:
            exact_doc = records.get(f"prompts_v1/{exact_id}")
            if exact_doc:
                exact_feedback = feedback_adjustment(exact_doc)
                if exact_feedback["postcheck_count"]:
                    # A new prompt has no fitted item/vector. Its own clip feedback
                    # adjusts a historical-neighbour prior without altering that history.
                    effective_count = sum(item["vote_count"] for item in neighbours)
                    mixed_risk = float((mixed_risk * effective_count + exact_feedback["postcheck_failures"]) / (effective_count + exact_feedback["postcheck_count"]))
                    all_feedback_count += exact_feedback["postcheck_count"]
                    all_feedback_failures += exact_feedback["postcheck_failures"]
                    exact_feedback["prior_effective_count"] = effective_count
        difficulty = float(np.mean(difficulties))
        discrimination = float(np.mean(discriminations))
        result.update(
            p_fail=mixed_risk,
            historical_p_fail=historical_risk,
            feedback_adjusted_risk=mixed_risk,
            difficulty=difficulty,
            discrimination=discrimination,
            p_success_by_model=dict(zip(self.engine.models, map(float, expit(discrimination * (self.engine.ability - difficulty))))),
            evidence_store="firestore",
            postcheck_feedback={
                "count": all_feedback_count,
                "failures": all_feedback_failures,
                "failure_rate": all_feedback_failures / all_feedback_count if all_feedback_count else None,
                "exact_unseen_prompt": exact_feedback,
            },
            risk_semantics=(
                "MIXED heuristic proxy: human pairwise both-bad evidence plus separately counted single-clip postcheck failures; not a calibrated failure probability."
                if all_feedback_count else
                "Arithmetic mean of five Firestore human pairwise both-bad vote rates; not a calibrated failure probability."
            ),
        )
        result["coverage"]["firestore_prompt_documents"] = 5
        result["coverage"]["firestore_item_documents"] = 5
        result["coverage"]["neighbour_vote_count"] = sum(item["vote_count"] for item in neighbours)
        result["reasons"].append("Neighbour vote rates and item parameters were read from Firestore for this request.")
        if all_feedback_count:
            result["reasons"].append("The updated risk mixes historical pairwise votes and separate Gemini clip verdicts; historical_p_fail preserves the human-only statistic.")
        return result

    def difficulty(self, prompt: str) -> dict:
        if self.engine is None:
            raise RuntimeError("Attach the bundled vector engine before live prediction")
        return self.live_risk(self.engine.predict(prompt), prompt=prompt)

    def record_verdict(
        self,
        prompt: str,
        model: str,
        pass_bool: bool,
        defects: list[dict],
        verdict_id: str | None = None,
        source: str = "gemini_single_clip_postcheck",
    ) -> dict:
        """Atomically persist one clip verdict and update separate feedback counters."""
        if not isinstance(pass_bool, bool) or not prompt.strip() or not model.strip():
            raise ValueError("A prompt, model and boolean clip verdict are required")
        identifier = verdict_id or uuid.uuid4().hex
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", identifier):
            raise ValueError("Invalid verdict identifier")
        content = {"prompt": prompt, "model": model, "pass_bool": pass_bool, "defects": defects, "source": source}
        fingerprint = hashlib.sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode()).hexdigest()
        prompt_reference = self.client.collection("prompts_v1").document(prompt_id(prompt))
        verdict_reference = self.client.collection("verdicts_v1").document(identifier)
        decorator = self.transaction_decorator
        if decorator is None:
            from google.cloud import firestore

            decorator = firestore.transactional

        @decorator
        def commit(transaction):
            existing_verdict = verdict_reference.get(transaction=transaction)
            existing_prompt = prompt_reference.get(transaction=transaction)
            if existing_verdict.exists:
                if existing_verdict.to_dict().get("content_sha256") != fingerprint:
                    raise ValueError("Verdict identifier is already bound to different content")
                return {"verdict_id": identifier, "created": False, "feedback": existing_prompt.to_dict().get("postcheck_feedback", {})}
            document = existing_prompt.to_dict() if existing_prompt.exists else {"prompt": prompt, "id": prompt_id(prompt)}
            previous = document.get("postcheck_feedback", {})
            feedback = {
                "count": int(previous.get("count", 0)) + 1,
                "failures": int(previous.get("failures", 0)) + int(not pass_bool),
                "passes": int(previous.get("passes", 0)) + int(pass_bool),
                "semantics": "single-clip postcheck verdicts; separate from human pairwise both-bad votes",
                "updated_at": datetime.now(timezone.utc),
            }
            transaction.set(verdict_reference, {**content, "prompt_id": prompt_id(prompt), "content_sha256": fingerprint, "created_at": datetime.now(timezone.utc)})
            transaction.set(prompt_reference, {"prompt": prompt, "id": prompt_id(prompt), "postcheck_feedback": feedback}, merge=True)
            return {"verdict_id": identifier, "created": True, "feedback": feedback}

        return commit(self.client.transaction())

    def collection_counts(self) -> dict:
        counts = {}
        for name in ("prompts_v1", "items_v1", "verdicts_v1"):
            rows = self.client.collection(name).count().get(timeout=20)
            counts[name] = int(rows[0][0].value)
        return counts
