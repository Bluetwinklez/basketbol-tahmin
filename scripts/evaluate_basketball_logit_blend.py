"""Evaluate a regularized basketball winner model across multiple leagues."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from bbtahmin.asia_model import walk_forward
from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.shadow_models import FORFEIT_GAMES
from scripts.evaluate_improvement_basketball import load
from scripts.evaluate_kbl_learner_stability import LEARNERS, REFERENCE, build_target, season_matrix

LEAGUES = ("KBL", "E", "ABA", "TR_BSL")
SEASONS = ("2023-24", "2024-25", "2025-26", "2026-27")
CANDIDATE = "regularized_logit"
PENALTY = 0.025


def design(probabilities):
    p = probabilities.loc[:, list(LEARNERS)].to_numpy(float)
    return np.column_stack([np.ones(len(p)), logit(np.clip(p, 1e-6, 1 - 1e-6))])


def learn(rows, prior_seasons):
    blocks = []
    for season in prior_seasons:
        p, games = season_matrix(rows, season)
        x = design(p)
        y = games["y"].to_numpy(float)
        blocks.append((x, y))
    center = np.array([0.0, *([1 / len(LEARNERS)] * len(LEARNERS))])

    def objective(coef):
        regularizer = coef - center
        losses = []
        gradients = []
        for x, y in blocks:
            z = x @ coef
            losses.append(np.mean(np.logaddexp(0, z) - y * z))
            gradients.append(x.T @ (expit(z) - y) / len(y))
        return (
            float(np.mean(losses) + PENALTY * (regularizer @ regularizer) / 2),
            np.mean(gradients, axis=0) + PENALTY * regularizer,
        )

    fitted = minimize(
        objective, center, jac=True, method="L-BFGS-B",
        bounds=[(-1, 1), *([(0, 2)] * len(LEARNERS))],
    )
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise RuntimeError(f"Basketball logit blend failed: {fitted.message}")
    return fitted.x


def build(rows, season, league):
    spec, compared = build_target(rows, season)
    coefficients = learn(rows, spec["prior_seasons"])
    p, games = season_matrix(rows, season)
    predicted = expit(design(p) @ coefficients)
    variants = {REFERENCE, "ensemble", "three_season_blend", "always_home"}
    kept = [r for r in compared if r["variant"] in variants]
    reference = [r for r in kept if r["variant"] == REFERENCE]
    if [r["event_id"] for r in reference] != games.index.astype(str).tolist():
        raise ValueError("Reference fixture order differs from candidate")
    kept.extend(dict(r, variant=CANDIDATE, p=[1 - float(q), float(q)])
                for r, q in zip(reference, predicted, strict=True))
    for row in kept:
        row["event_id"] = f"{league}:{row['event_id']}"
    return dict(spec, coefficients=coefficients.tolist()), kept


def summarize(rows):
    result = {}
    for name in (REFERENCE, "ensemble", "three_season_blend", "always_home", CANDIDATE):
        part = [r for r in rows if r["variant"] == name]
        probabilities = [r["p"] for r in part]
        summary = metrics([r["y"] for r in part], probabilities, [max(p) >= .65 for p in probabilities])
        if name != REFERENCE:
            summary["vs_selected"] = paired(rows, REFERENCE, name, replicates=2000)
        result[name] = summary
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    leagues = {}
    pooled = {season: [] for season in SEASONS}
    for league in LEAGUES:
        games, hashes = load(league)
        keep = ~games["mac_id"].isin(FORFEIT_GAMES)
        predictions, _, skipped = walk_forward(league, games.loc[keep].reset_index(drop=True))
        seasons = {}
        for season in SEASONS:
            spec, rows = build(predictions, season, league)
            seasons[season] = dict(spec, results=summarize(rows))
            pooled[season].extend(rows)
        if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
            raise ValueError(f"{league} archive changed during evaluation")
        leagues[league] = dict(seasons=seasons, input_sha256=hashes, excluded_forfeits=int((~keep).sum()), skipped_base_folds=skipped)
    report = {
        "evidence_kind": "exploratory_retrospective",
        "penalty": PENALTY,
        "leagues": leagues,
        "seasons": {season: summarize(rows) for season, rows in pooled.items()},
        "completed_seasons": summarize([r for season in SEASONS[:-1] for r in pooled[season]]),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
