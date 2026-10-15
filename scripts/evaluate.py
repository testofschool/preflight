"""Run declared splits with fitting restricted to each training partition."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from preflight_core import PreflightEngine
from preflight_core.irt import FitSettings, fit_items
from preflight_core.provenance import read_frozen_votes


def auc(labels: np.ndarray, scores: np.ndarray) -> float | None:
    return float(roc_auc_score(labels, scores)) if np.unique(labels).size == 2 else None


def fallback_means(matrix: np.ndarray, axis: int) -> np.ndarray:
    finite = np.isfinite(matrix)
    count = finite.sum(axis=axis)
    fallback = float(np.nanmean(matrix))
    return np.divide(np.nansum(matrix, axis=axis), count, out=np.full(count.shape, fallback), where=count > 0)


def average(runs: list[dict], key: str) -> float | None:
    values = [row[key] for row in runs if row[key] is not None]
    return float(np.mean(values)) if values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/genai_video_test.parquet"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/evaluation.json"))
    args = parser.parse_args()
    dataset, source_digest = read_frozen_votes(args.data)
    q1_runs, q2_runs, q2_strict_runs, q4_runs, q4_paired_runs, risk_runs = [], [], [], [], [], []
    fit_reports = []
    transductive_vocabulary = TfidfVectorizer(ngram_range=(1, 2)).fit(dataset.prompts)
    for seed in range(5):
        random = np.random.default_rng(seed)
        observed_rows, observed_columns = np.where(np.isfinite(dataset.matrix))
        selected = random.random(observed_rows.size) < 0.3
        held_cells = np.zeros(dataset.matrix.shape, dtype=bool)
        held_cells[observed_rows[selected], observed_columns[selected]] = True
        training_cells = dataset.matrix.copy()
        training_cells[held_cells] = np.nan
        fitted_cells = fit_items(training_cells, seed=seed)
        fit_reports.append({"experiment": "Q1", "seed": seed, **fitted_cells.diagnostics})
        labels = dataset.matrix[held_cells] >= 0.5
        row_ids, model_ids = np.where(held_cells)
        model_mean = fallback_means(training_cells, axis=0)
        prompt_mean = fallback_means(training_cells, axis=1)
        q1_runs.append({
            "seed": seed,
            "n_test_cells": int(labels.size),
            "auc_irt": auc(labels, fitted_cells.probabilities()[held_cells]),
            "auc_model_mean": auc(labels, model_mean[model_ids]),
            "auc_prompt_mean": auc(labels, prompt_mean[row_ids]),
        })

        # A fresh generator makes this experiment independent of the cell-mask experiment.
        n_heldout = int(0.2 * len(dataset.prompts))
        test_ids = np.sort(np.random.default_rng(100 + seed).choice(len(dataset.prompts), n_heldout, replace=False))
        train_ids = np.setdiff1d(np.arange(len(dataset.prompts)), test_ids)
        training = dataset.subset(train_ids)
        fitted_prompts = fit_items(training.matrix, seed=seed, original_item_ids=train_ids, full_item_count=len(dataset.prompts))
        fit_reports.append({"experiment": "Q2", "seed": seed, **fitted_prompts.diagnostics})
        predictor = PreflightEngine(training, fitted_prompts)
        reference_predictor = PreflightEngine(training, fitted_prompts, vectorizer=transductive_vocabulary, tie_policy="default")
        predictions = [predictor.estimates(dataset.prompts[int(index)]) for index in test_ids]
        reference_predictions = [reference_predictor.estimates(dataset.prompts[int(index)]) for index in test_ids]
        probability = np.stack([entry["success"] for entry in predictions])
        reference_probability = np.stack([entry["success"] for entry in reference_predictions])
        test_matrix = dataset.matrix[test_ids]
        observed = np.isfinite(test_matrix)
        model_mean = fallback_means(training.matrix, axis=0)
        baseline_matrix = np.broadcast_to(model_mean, test_matrix.shape)
        q2_common = {
            "seed": seed,
            "n_train_prompts": len(training.prompts),
            "n_test_prompts": n_heldout,
            "n_test_cells": int(observed.sum()),
            "auc_model_mean": auc(test_matrix[observed] >= 0.5, baseline_matrix[observed]),
        }
        q2_strict_runs.append({
            **q2_common,
            "auc_irt_coldstart": auc(test_matrix[observed] >= 0.5, probability[observed]),
            "zero_vocabulary_queries": sum(entry["matched_features"] == 0 for entry in predictions),
            "queries_with_fewer_than_five_positive_neighbours": sum(np.count_nonzero(entry["similarities"] > 0) < 5 for entry in predictions),
        })
        q2_runs.append({
            **q2_common,
            "auc_irt_coldstart": auc(test_matrix[observed] >= 0.5, reference_probability[observed]),
            "zero_vocabulary_queries": sum(entry["matched_features"] == 0 for entry in reference_predictions),
            "queries_with_fewer_than_five_positive_neighbours": sum(np.count_nonzero(entry["similarities"] > 0) < 5 for entry in reference_predictions),
        })

        irt_pick, baseline_pick = int(np.argmax(fitted_prompts.ability)), int(np.argmax(model_mean))
        eligible = np.isfinite(test_matrix[:, irt_pick]) & np.isfinite(test_matrix[:, baseline_pick])
        if eligible.any():
            mean_irt = float(np.mean(test_matrix[eligible, irt_pick]))
            mean_baseline = float(np.mean(test_matrix[eligible, baseline_pick]))
        else:
            mean_irt, mean_baseline = None, None
        q4_paired_runs.append({
            "seed": seed,
            "irt_pick": dataset.models[irt_pick],
            "baseline_pick": dataset.models[baseline_pick],
            "n_paired_observed_prompts": int(eligible.sum()),
            "n_unmeasured_prompts": int((~eligible).sum()),
            "mean_outcome_irt_pick": mean_irt,
            "mean_outcome_baseline_pick": mean_baseline,
            "difference": mean_irt - mean_baseline if mean_irt is not None else None,
        })

        available_irt_outcomes = []
        available_baseline_outcomes = []
        irt_available_picks = []
        baseline_available_picks = []
        for row_index, row in enumerate(test_matrix):
            available = np.flatnonzero(np.isfinite(row))
            if available.size == 0:
                continue
            irt_choice = int(available[np.argmax(reference_probability[row_index, available])])
            baseline_choice = baseline_pick if baseline_pick in available else int(available[np.argmax(model_mean[available])])
            available_irt_outcomes.append(float(row[irt_choice]))
            available_baseline_outcomes.append(float(row[baseline_choice]))
            irt_available_picks.append(dataset.models[irt_choice])
            baseline_available_picks.append(dataset.models[baseline_choice])
        available_irt_mean = float(np.mean(available_irt_outcomes))
        available_baseline_mean = float(np.mean(available_baseline_outcomes))
        q4_runs.append({
            "seed": seed,
            "n_prompts": len(available_irt_outcomes),
            "n_irt_global_best_unobserved": int(np.count_nonzero(~np.isfinite(test_matrix[:, irt_pick]))),
            "n_baseline_global_best_unobserved": int(np.count_nonzero(~np.isfinite(test_matrix[:, baseline_pick]))),
            "mean_outcome_irt_pick": available_irt_mean,
            "mean_outcome_baseline_pick": available_baseline_mean,
            "difference": available_irt_mean - available_baseline_mean,
            "available_choice_disagreements": sum(a != b for a, b in zip(irt_available_picks, baseline_available_picks)),
        })

        risk_by_prompt = {dataset.prompts[int(index)]: entry["p_fail"] for index, entry in zip(test_ids, predictions)}
        reference_risk = {dataset.prompts[int(index)]: entry["p_fail"] for index, entry in zip(test_ids, reference_predictions)}
        held_votes = dataset.votes[dataset.votes["prompt"].isin(risk_by_prompt)]
        vote_targets = (held_votes["vote_type"] == "bothbad_vote").to_numpy()
        risk_scores = held_votes["prompt"].map(risk_by_prompt).to_numpy()
        length_scores = -held_votes["prompt"].str.len().to_numpy()
        any_rejection = dataset.both_bad_counts[test_ids] > 0
        risk_runs.append({
            "seed": seed,
            "n_test_prompts": n_heldout,
            "n_test_votes": len(held_votes),
            "both_bad_test_votes": int(vote_targets.sum()),
            "auc_both_bad_vote": auc(vote_targets, risk_scores),
            "auc_both_bad_vote_transductive": auc(vote_targets, held_votes["prompt"].map(reference_risk).to_numpy()),
            "auc_negative_character_length_vote": auc(vote_targets, length_scores),
            "auc_any_both_bad_prompt_extension": auc(any_rejection, np.asarray([entry["p_fail"] for entry in predictions])),
        })

    full_fit = fit_items(dataset.matrix)
    global_best = int(np.argmax(full_fit.ability))
    q1_irt, q1_base = average(q1_runs, "auc_irt"), average(q1_runs, "auc_model_mean")
    q2_irt, q2_base = average(q2_runs, "auc_irt_coldstart"), average(q2_runs, "auc_model_mean")
    q2_strict_irt = average(q2_strict_runs, "auc_irt_coldstart")
    risk_mean = average(risk_runs, "auc_both_bad_vote")
    q4_difference = average(q4_runs, "difference")
    q4_paired_difference = average(q4_paired_runs, "difference")
    report = {
        "protocol": {
            "source_sha256": source_digest,
            "source_sha256_verified": True,
            "preregistered": ["Q1 cell-mean target >= 0.5", "Q2 20% unseen prompts", "Q3 fitted prompt argmax", "Q4 observed outcome of recommendations"],
            "settings_declared_before_fit": asdict(FitSettings()),
            "seeds": list(range(5)),
            "prompt_split": "floor(20% of sorted prompts), default_rng(100+seed).choice without replacement; sorted remaining prompts train",
            "cell_split": "independent Bernoulli 30% vector of observed cells only; default_rng(seed)",
            "vectorizer": "TF-IDF word unigrams and bigrams; Q2 fits vocabulary on all prompts to match attached reference's transductive method; Q2_strict and primary risk fit training prompts only",
            "neighbours": "cosine top 5; reference default argsort, strict stable training-order ties; arithmetic mean of item parameters and both-bad rates; zero-similarity neighbours included",
            "cell_weighting": "one per observed cell; not weighted by vote count",
            "both_bad_preregistration_status": "PREREG and attached results do not specify a both-bad AUC experiment or binary target; exact claimed AUC reproduction is unverifiable",
            "both_bad_vote_target": "unregistered extension: each held-out human vote is 1 exactly when vote_type is bothbad_vote; all votes for one held-out prompt receive its text-only training-neighbour score",
            "both_bad_prompt_target": "unregistered extension: held-out prompt has at least one both-bad human vote; no threshold tuning",
            "length_baseline": "negative character count; sign fixed from supplied short-prompt risk hypothesis; no fitted threshold",
            "q4_missing_outcomes": "reference method: IRT chooses highest-scored model among models observed for each held-out prompt; baseline chooses global model mean winner when observed, otherwise highest training mean among available models",
            "q4_paired_extension": "stricter unregistered diagnostic: evaluate only prompts with observed outcomes for BOTH fixed global recommendations; unavailable outcomes excluded and counted",
            "q4_interpretation": "Positive available-choice gains can arise from different global model orderings plus missing outcomes; they do not demonstrate prompt-specific routing or measured money saved",
            "historical_scope": "both-bad rate is a relative pairwise-vote statistic, not a calibrated per-generation failure probability",
            "method_correction": "Initial diagnostic preserved separately. Audited reference constants supplied by independent code reviewer: ability L2=1, difficulty L2=.1, discrimination shrinkage to 1 L2=1; seed-dependent Gaussian initialization; splits corrected before final run. No metric thresholds changed.",
            "penalty_preregistration_difference": "PREREG names L2 on ability/difficulty but omits strengths and discrimination penalty; discrimination shrinkage is present in supplied reference and is declared here as an undeclared method detail",
            "solver_difference": "Fresh analytic-gradient L-BFGS-B bounds a directly rather than reference's clipping within an unconstrained objective; close metrics expected, exact floating equality not claimed",
        },
        "dataset": {"rows": len(dataset.votes), "prompts": len(dataset.prompts), "models": len(dataset.models), "observed_cells": int(np.isfinite(dataset.matrix).sum()), "both_bad_vote_fraction": float(dataset.both_bad_counts.sum() / dataset.vote_counts.sum())},
        "Q1": {"runs": q1_runs, "mean_irt": q1_irt, "mean_baseline": q1_base, "margin": q1_irt - q1_base, "pass": bool(q1_irt - q1_base >= 0.03)},
        "Q2": {"runs": q2_runs, "mean_irt": q2_irt, "mean_baseline": q2_base, "margin": q2_irt - q2_base, "pass": bool(q2_irt > q2_base)},
        "Q2_strict": {"runs": q2_strict_runs, "mean_irt": q2_strict_irt, "mean_baseline": q2_base, "margin": q2_strict_irt - q2_base, "pass": bool(q2_strict_irt > q2_base)},
        "Q3": {"global_best": dataset.models[global_best], "share_prompts_with_different_best": float(np.mean(np.argmax(full_fit.probabilities(), axis=1) != global_best)), "positive_discrimination_implication": "Every prompt has the same ability ordering because every discrimination is positive; no prompt-specific model routing"},
        "Q4": {"runs": q4_runs, "mean_irt": average(q4_runs, "mean_outcome_irt_pick"), "mean_baseline": average(q4_runs, "mean_outcome_baseline_pick"), "difference": q4_difference, "pass": bool(q4_difference is not None and q4_difference > 0)},
        "Q4_paired_extension": {"runs": q4_paired_runs, "mean_paired_difference": q4_paired_difference, "pass": bool(q4_paired_difference is not None and q4_paired_difference > 0)},
        "both_bad_risk": {"runs": risk_runs, "mean_vote_auc": risk_mean, "mean_vote_auc_transductive": average(risk_runs, "auc_both_bad_vote_transductive"), "mean_negative_length_vote_auc": average(risk_runs, "auc_negative_character_length_vote"), "mean_any_both_bad_prompt_auc": average(risk_runs, "auc_any_both_bad_prompt_extension"), "declared_vote_metric_meets_0_68": bool(risk_mean >= 0.68), "exact_handoff_reproduction": "UNVERIFIABLE: binary target and aggregation omitted from supplied preregistration/results"},
        "V4": {"numerical_conditions_on_declared_metrics": bool(risk_mean >= 0.68 and q2_irt >= q2_base), "exact_claim_reproduction": "UNVERIFIABLE", "reason": "Both-bad target and aggregation are absent from the supplied preregistration/results. IRT constants follow the audited reference; direct bounded optimization is a documented solver difference."},
        "fit_diagnostics": fit_reports + [{"experiment": "full", **full_fit.diagnostics}],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("seed  Q1_IRT  Q1_B1  Q2_IRT_transductive  Q2_IRT_strict  Q2_B1  risk_vote_AUC_strict  length_AUC")
    for q1, q2, strict, risk in zip(q1_runs, q2_runs, q2_strict_runs, risk_runs):
        print(f"{q1['seed']}  {q1['auc_irt']:.6f}  {q1['auc_model_mean']:.6f}  {q2['auc_irt_coldstart']:.6f}  {strict['auc_irt_coldstart']:.6f}  {q2['auc_model_mean']:.6f}  {risk['auc_both_bad_vote']:.6f}  {risk['auc_negative_character_length_vote']:.6f}")
    for key in ("Q1", "Q2", "Q2_strict", "Q3", "Q4", "Q4_paired_extension", "both_bad_risk", "V4"):
        print(key, json.dumps({k: v for k, v in report[key].items() if k != "runs"}))
    failures = [row for row in report["fit_diagnostics"] if not row["converged"]]
    print(f"converged_fits={len(report['fit_diagnostics']) - len(failures)}/{len(report['fit_diagnostics'])}")
    if failures:
        raise SystemExit("Some fits failed to converge; inspect the saved diagnostics")


if __name__ == "__main__":
    main()
