"""Test whether averaging past KBL learner performance improves season selection."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from bbtahmin.asia_model import load, walk_forward
from bbtahmin.experiment_metrics import metrics, paired

LEARNERS = ("score", "logistic", "elo")
REFERENCE = "selected_policy"
VARIANTS = (REFERENCE, *LEARNERS, "ensemble", "three_season_blend", "always_home")
LOOKBACK = 3
RIDGE = 0.03
MIN_PRIOR_GAMES = 50
FIRST_TARGET = "2022-23"


def season_matrix(rows, season):
    block = rows.loc[rows["sezon"].eq(season)]
    raw = block.pivot(index="mac_id", columns="variant", values="p")
    scheduled = block.loc[block["variant"].eq(REFERENCE)].set_index("mac_id")
    reference = scheduled.reindex(raw.index)
    if (not set((*LEARNERS, "ensemble", REFERENCE)) <= set(raw.columns)
            or raw.isna().any().any()
            or not np.isfinite(raw.to_numpy()).all()
            or not raw.ge(0).all().all() or not raw.le(1).all().all()
            or reference["y"].isna().any()):
        raise ValueError(f"Incomplete paired learner predictions for {season}")
    if not block.groupby("mac_id")[["y", "tarih_utc"]].nunique().eq(1).all().all():
        raise ValueError(f"Paired learner outcome or date differs in {season}")
    return raw, reference


def fit_weights(history, target):
    """Fit on three earlier out-of-sample seasons, with equal weight per season."""
    counts = history.loc[history["variant"].eq(REFERENCE)].groupby("sezon").size()
    eligible = sorted(s for s, n in counts.items() if s < target and n >= MIN_PRIOR_GAMES)
    seasons = eligible[-LOOKBACK:]
    if len(seasons) < LOOKBACK or [int(s[:4]) for s in seasons] != list(range(int(target[:4]) - LOOKBACK, int(target[:4]))):
        raise ValueError("Three consecutive earlier out-of-sample seasons are required")

    target_rows = history.loc[history["sezon"].eq(target)]
    prior = history.loc[history["sezon"].isin(seasons)]
    if (target_rows.empty or prior["tarih_utc"].max() >= target_rows["tarih_utc"].min()
            or set(prior["mac_id"]) & set(target_rows["mac_id"])):
        raise ValueError("Earlier evidence must precede the target and use distinct fixtures")

    observed = []
    for season in seasons:
        predictions, games = season_matrix(history, season)
        p = predictions.loc[:, list(LEARNERS)].to_numpy(float)
        observed.append(np.where(games["y"].to_numpy()[:, None] == 1, p, 1 - p))
    equal = np.full(len(LEARNERS), 1 / len(LEARNERS))

    def objective(w):
        assigned = [np.clip(p @ w, 1e-12, 1) for p in observed]
        loss = np.mean([-np.log(q).mean() for q in assigned])
        gradient = np.mean([-(p / q[:, None]).mean(axis=0) for p, q in zip(observed, assigned, strict=True)], axis=0)
        return float(loss + RIDGE * np.sum((w - equal) ** 2) / 2), gradient + RIDGE * (w - equal)

    fitted = minimize(
        objective, equal, jac=True, method="SLSQP",
        bounds=[(0, 1)] * len(equal), constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}],
        options={"ftol": 1e-12},
    )
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise RuntimeError(f"KBL blend optimizer failed: {fitted.message}")
    return seasons, fitted.x / fitted.x.sum()


def build_target(rows, season):
    seasons, weights = fit_weights(rows, season)
    p, games = season_matrix(rows, season)
    probabilities = {name: p[name].to_numpy() for name in (*LEARNERS, "ensemble", REFERENCE)}
    probabilities["three_season_blend"] = p.loc[:, list(LEARNERS)].to_numpy() @ weights
    # Use the strictly prior home-win rate as the probabilities of the home-only rule.
    before = rows.loc[rows["sezon"].isin(seasons) & rows["variant"].eq(REFERENCE), "y"]
    home_rate = float((before.sum() + 1) / (len(before) + 2))
    probabilities["always_home"] = np.full(len(games), max(0.50000001, home_rate))
    result = [
        {"event_id": str(game_id), "day": date.strftime("%Y-%m-%d"), "y": int(y),
         "variant": name, "p": [1 - float(pred), float(pred)]}
        for name, preds in probabilities.items()
        for (game_id, date, y), pred in zip(
            games[["tarih_utc", "y"]].itertuples(name=None), preds, strict=True)
    ]
    return dict(prior_seasons=seasons, prior_home_probability=home_rate,
                weights=dict(zip(LEARNERS, weights.tolist(), strict=True))), result


def summarize(rows):
    report = {}
    for name in VARIANTS:
        part = [r for r in rows if r["variant"] == name]
        y = [r["y"] for r in part]
        p = [r["p"] for r in part]
        report[name] = metrics(y, p, [max(v) >= 0.65 for v in p])
        if name != REFERENCE:
            report[name]["vs_selected"] = paired(rows, REFERENCE, name, replicates=2000)
    equal_loss = report["ensemble"]["all"]["log_loss"]
    for entry in report.values():
        entry["log_loss_delta_vs_equal_blend"] = entry["all"]["log_loss"] - equal_loss
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", required=True, type=Path)
    args = cli.parse_args()
    source = Path("data/asia/KBL.parquet")
    checksum = hashlib.sha256(source.read_bytes()).hexdigest()
    games = load("KBL")
    predictions, folds, skipped = walk_forward("KBL", games)
    reports = {}
    completed = []
    latest = max(games["sezon"])
    for season in sorted(set(games["sezon"])):
        if season < FIRST_TARGET:
            continue
        spec, rows = build_target(predictions, season)
        reports[season] = dict(spec, learner=next(f["selected"] for f in folds if f["season"] == season),
                               results=summarize(rows))
        if season < latest:
            completed.extend(rows)
    if hashlib.sha256(source.read_bytes()).hexdigest() != checksum:
        raise ValueError("Archive changed during evaluation")
    report = {
        "evidence_kind": "exploratory_retrospective",
        "source_sha256": checksum,
        "lookback": LOOKBACK,
        "ridge": RIDGE,
        "confidence_threshold": 0.65,
        "latest_season": latest,
        "skipped_base_folds": skipped,
        "seasons": reports,
        "prior_completed_seasons": summarize(completed),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
