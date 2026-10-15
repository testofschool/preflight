"""Bounded two-parameter logistic fit with an analytic likelihood gradient."""

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit


@dataclass(frozen=True)
class FitSettings:
    # Sum negative log-likelihood plus this coefficient times squared parameters.
    l2_ability: float = 1.0
    l2_difficulty: float = 0.1
    l2_discrimination: float = 1.0
    min_discrimination: float = 0.3
    max_discrimination: float = 4.0
    max_iterations: int = 3000
    gradient_tolerance: float = 1e-6


@dataclass
class ItemFit:
    ability: np.ndarray
    difficulty: np.ndarray
    discrimination: np.ndarray
    diagnostics: dict

    def probabilities(self) -> np.ndarray:
        return expit(self.discrimination[:, None] * (self.ability[None, :] - self.difficulty[:, None]))


def fit_items(
    matrix: np.ndarray,
    settings: FitSettings | None = None,
    seed: int = 0,
    original_item_ids: np.ndarray | None = None,
    full_item_count: int | None = None,
) -> ItemFit:
    config = settings or FitSettings()
    n_items, n_models = matrix.shape
    item_ids, model_ids = np.where(np.isfinite(matrix))
    responses = matrix[item_ids, model_ids]
    if responses.size == 0:
        raise ValueError("IRT requires at least one observed cell")
    random = np.random.default_rng(seed)
    initial_ability = random.normal(0, 0.1, n_models)
    initial_difficulty = random.normal(0, 0.1, full_item_count or n_items)
    if original_item_ids is not None:
        initial_difficulty = initial_difficulty[original_item_ids]
    initial = np.concatenate((initial_ability, initial_difficulty, np.ones(n_items)))

    def objective(parameters: np.ndarray) -> tuple[float, np.ndarray]:
        ability = parameters[:n_models]
        difficulty = parameters[n_models : n_models + n_items]
        discrimination = parameters[n_models + n_items :]
        distance = ability[model_ids] - difficulty[item_ids]
        logit = discrimination[item_ids] * distance
        residual = expit(logit) - responses
        loss = np.sum(np.logaddexp(0.0, logit) - responses * logit)
        loss += config.l2_ability * np.dot(ability, ability)
        loss += config.l2_difficulty * np.dot(difficulty, difficulty)
        loss += config.l2_discrimination * np.dot(discrimination - 1, discrimination - 1)
        ability_gradient = np.bincount(model_ids, weights=residual * discrimination[item_ids], minlength=n_models)
        difficulty_gradient = np.bincount(item_ids, weights=-residual * discrimination[item_ids], minlength=n_items)
        discrimination_gradient = np.bincount(item_ids, weights=residual * distance, minlength=n_items)
        ability_gradient += 2 * config.l2_ability * ability
        difficulty_gradient += 2 * config.l2_difficulty * difficulty
        discrimination_gradient += 2 * config.l2_discrimination * (discrimination - 1)
        return float(loss), np.concatenate((ability_gradient, difficulty_gradient, discrimination_gradient))

    solution = minimize(
        objective,
        initial,
        jac=True,
        method="L-BFGS-B",
        bounds=[(None, None)] * (n_models + n_items)
        + [(config.min_discrimination, config.max_discrimination)] * n_items,
        options={"maxiter": config.max_iterations, "gtol": config.gradient_tolerance, "ftol": 1e-11},
    )
    projected_gradient = solution.jac.copy()
    a_start = n_models + n_items
    active_low = solution.x[a_start:] <= config.min_discrimination + 1e-9
    active_high = solution.x[a_start:] >= config.max_discrimination - 1e-9
    constrained_gradient = projected_gradient[a_start:]
    constrained_gradient[(active_low & (constrained_gradient > 0)) | (active_high & (constrained_gradient < 0))] = 0
    diagnostics = {
        "converged": bool(solution.success),
        "message": str(solution.message),
        "iterations": int(solution.nit),
        "objective": float(solution.fun),
        "max_absolute_gradient": float(np.max(np.abs(solution.jac))),
        "max_absolute_projected_gradient": float(np.max(np.abs(projected_gradient))),
        "gradient_note": "Raw gradients can be nonzero at active discrimination bounds; projected gradient accounts for the bounds",
        "observed_cells": int(responses.size),
        "settings": asdict(config),
        "cell_weights": "one per observed cell; cell means are fractional responses",
        "initialization": "default_rng(seed): ability N(0,.1), full prompt difficulty N(0,.1) then subset, discrimination one",
        "seed": seed,
        "solver_method_difference": "L-BFGS-B direct bounds on discrimination, analytic gradient; reference clips unbounded discrimination inside objective",
    }
    if not np.isfinite(solution.x).all():
        raise RuntimeError("IRT optimization produced non-finite parameters")
    return ItemFit(
        solution.x[:n_models],
        solution.x[n_models : n_models + n_items],
        solution.x[n_models + n_items :],
        diagnostics,
    )
