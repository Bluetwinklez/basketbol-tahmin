"""Measure whether Elo should retain more or less prior-season team strength."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.ozellik import build_features
from bbtahmin.shadow_models import FORFEIT_GAMES
from scripts.evaluate_basketball_logit_blend import LEAGUES
from scripts.evaluate_improvement_basketball import load

DEFAULT = 0.25
GRID = (0.05, 0.20, DEFAULT, 0.35, 0.50, 0.70)
TARGETS = ("2023-24", "2024-25", "2025-26", "2026-27")
EARLY_DAYS = 45
MIN_PRIOR_EARLY = 20


def scored_fixtures(games):
    data = games[["mac_id", "tarih_utc", "sezon", "ev", "dep"]].copy()
    data["day"] = data["tarih_utc"].dt.floor("D")
    first = data.groupby("sezon")["day"].transform("min")
    data["early"] = (data["day"] - first).dt.days < EARLY_DAYS
    participants = {
        int(season[:4]): set(block["ev"]) | set(block["dep"])
        for season, block in data.groupby("sezon")
    }
    data["returning_or_new"] = [
        not {home, away} <= participants.get(int(season[:4]) - 1, set())
        for season, home, away in zip(data["sezon"], data["ev"], data["dep"], strict=True)
    ]
    data["y"] = (games["ev_skor"] > games["dep_skor"]).astype(int)
    for shrinkage in GRID:
        features = build_features(games, shrink=shrinkage)
        if not features["mac_id"].equals(data["mac_id"]):
            raise ValueError("Feature order differs from fixture order")
        data[shrinkage] = features["elo_p"]
    return data


def score(frame, shrinkage):
    p = frame[shrinkage].to_numpy(float)
    return metrics(frame["y"].to_numpy(int), np.column_stack((1 - p, p)))["all"]


def choose(frame, target):
    target_year = int(target[:4])
    prior = [f"{year}-{(year + 1) % 100:02}" for year in range(target_year - 3, target_year)]
    before = frame.loc[frame["sezon"].isin(prior)]
    fixtures = frame.loc[frame["sezon"].eq(target)]
    if fixtures.empty or before.empty or before["day"].max() >= fixtures["day"].min():
        raise ValueError("Previous seasons must finish before the target")
    fitting = [before.loc[before["sezon"].eq(season) & before["early"]] for season in prior]
    if min(map(len, fitting)) < MIN_PRIOR_EARLY:
        raise ValueError("Three previous seasons with 20 early games each required")
    reference = [score(part, DEFAULT) for part in fitting]
    options = {}
    for shrinkage in GRID:
        stats = [score(part, shrinkage) for part in fitting]
        improvement = [a["log_loss"] - b["log_loss"] for a, b in zip(stats, reference, strict=True)]
        options[shrinkage] = {
            "mean_log_loss_delta": float(np.mean(improvement)),
            "mean_accuracy_delta": float(np.mean([
                a["accuracy"] - b["accuracy"] for a, b in zip(stats, reference, strict=True)
            ])),
            "seasons_with_lower_log_loss": sum(value < 0 for value in improvement),
        }
    eligible = [
        value for value, stats in options.items()
        if stats["mean_log_loss_delta"] <= -0.002 and stats["mean_accuracy_delta"] >= 0
        and stats["seasons_with_lower_log_loss"] >= 2
    ]
    selected = min(eligible, key=lambda v: (options[v]["mean_log_loss_delta"], abs(v - DEFAULT))) if eligible else DEFAULT
    return selected, prior, options


def paired_rows(frame, league, selected):
    rows = []
    for _, game in frame.iterrows():
        for name, shrinkage in (("reference", DEFAULT), ("prior_selected", selected)):
            p = float(game[shrinkage])
            rows.append(dict(
                event_id=f"{league}:{game['mac_id']}", day=game["day"].strftime("%Y-%m-%d"),
                y=int(game["y"]), variant=name, p=[1 - p, p],
                early=bool(game["early"]), returning_or_new=bool(game["returning_or_new"]),
            ))
    return rows


def summarize(rows):
    result = {}
    cohorts = {
        "all": rows,
        "first_45_days": [r for r in rows if r["early"]],
        "later": [r for r in rows if not r["early"]],
        "first_45_days_new_or_returning": [r for r in rows if r["early"] and r["returning_or_new"]],
    }
    for name, group in cohorts.items():
        if not group:
            result[name] = None
            continue
        summary = paired(group, "reference", "prior_selected", replicates=2000)
        for variant in ("reference", "prior_selected"):
            part = [r for r in group if r["variant"] == variant]
            p = [r["p"] for r in part]
            stats = metrics([r["y"] for r in part], p, [max(prob) >= .65 for prob in p])
            summary[variant] = {k: stats[k] for k in ("all", "selected", "coverage")}
        result[name] = summary
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    leagues = {}
    pooled = {target: [] for target in TARGETS}
    for league in LEAGUES:
        games, hashes = load(league)
        valid = ~games["mac_id"].isin(FORFEIT_GAMES)
        data = scored_fixtures(games.loc[valid].reset_index(drop=True))
        seasons = {}
        for target in TARGETS:
            selected, prior, options = choose(data, target)
            rows = paired_rows(data.loc[data["sezon"].eq(target)], league, selected)
            seasons[target] = dict(shrinkage=selected, prior=prior, prior_options=options, results=summarize(rows))
            pooled[target].extend(rows)
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
            raise ValueError(f"{league} archive changed during evaluation")
        leagues[league] = dict(seasons=seasons, input_sha256=hashes, excluded_forfeits=int((~valid).sum()))
    report = {
        "evidence_kind": "exploratory_retrospective", "shrinkage_grid": GRID,
        "baseline_shrinkage": DEFAULT, "early_days": EARLY_DAYS, "leagues": leagues,
        "seasons": {season: summarize(rows) for season, rows in pooled.items()},
        "completed": summarize([r for season in TARGETS[:-1] for r in pooled[season]]),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
