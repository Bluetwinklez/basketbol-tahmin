"""Replay league-specific home advantage using fixed or independently updated Elo ratings."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from bbtahmin.elo import expected
from bbtahmin.experiment_metrics import losses, metrics, paired
from bbtahmin.ozellik import build_features
from bbtahmin.shadow_models import FORFEIT_GAMES
from scripts.evaluate_basketball_carryover import TARGETS
from scripts.evaluate_basketball_logit_blend import LEAGUES
from scripts.evaluate_improvement_basketball import load

REFERENCE = 50
GRID = (0, 25, REFERENCE, 75, 100)
MIN_COURT_GAMES = 100


def win_probability(frame, advantage):
    column = f"elo_p_{advantage}"
    if column in frame:
        return frame[column].to_numpy(float)
    return expected(frame["elo_diff"].to_numpy(float), 0, advantage * frame["home"].to_numpy(float))


def scores(frame, advantage):
    p = win_probability(frame, advantage)
    return losses(frame["y"].to_numpy(int), np.column_stack((1 - p, p))).mean(axis=0)


def choose(frame, target):
    year = int(target[:4])
    prior = [f"{y}-{(y + 1) % 100:02}" for y in (year - 2, year - 1)]
    previous = frame.loc[frame["sezon"].isin(prior)]
    target_rows = frame.loc[frame["sezon"].eq(target)]
    if target_rows.empty or previous.empty or previous["day"].max() >= target_rows["day"].min():
        raise ValueError("Home-advantage selection requires strictly earlier seasons")
    cohorts = [previous.loc[previous["sezon"].eq(s) & previous["home"].eq(1)] for s in prior]
    if min(map(len, cohorts)) < MIN_COURT_GAMES:
        raise ValueError("Need at least 100 non-neutral fixtures in each prior season")
    ref = np.array([scores(cohort, REFERENCE) for cohort in cohorts])
    options = {}
    for advantage in GRID:
        delta = np.array([scores(cohort, advantage) for cohort in cohorts]) - ref
        mean = delta.mean(axis=0)
        options[advantage] = {
            "accuracy_delta": float(mean[0]), "log_loss_delta": float(mean[1]),
            "brier_delta": float(mean[2]), "season_log_loss_deltas": delta[:, 1].tolist(),
        }
    eligible = [
        a for a, result in options.items()
        if result["accuracy_delta"] >= .0025 and result["log_loss_delta"] <= -.001
        and result["brier_delta"] <= 0 and max(result["season_log_loss_deltas"]) <= .003
    ]
    choice = min(eligible, key=lambda a: (-options[a]["accuracy_delta"],
                                        options[a]["log_loss_delta"], abs(a - REFERENCE))) if eligible else REFERENCE
    return choice, prior, options


def create_rows(frame, league, advantage):
    return [
        {"event_id": f"{league}:{game.mac_id}", "day": game.day.strftime("%Y-%m-%d"),
         "variant": name, "y": int(game.y), "p": [1 - float(prob), float(prob)],
         "neutral": game.home == 0}
        for name, value in (("reference", REFERENCE), ("candidate", advantage))
        for game, prob in zip(frame.itertuples(), win_probability(frame, value), strict=True)
    ]


def summarize(rows):
    report = {}
    for name, group in (
        ("all", rows), ("home_court", [r for r in rows if not r["neutral"]]),
        ("neutral", [r for r in rows if r["neutral"]]),
    ):
        if not group:
            report[name] = None
            continue
        result = paired(group, "reference", "candidate", replicates=2000)
        for variant in ("reference", "candidate"):
            part = [r for r in group if r["variant"] == variant]
            p = [r["p"] for r in part]
            stats = metrics([r["y"] for r in part], p, [max(v) >= .65 for v in p])
            result[variant] = {key: stats[key] for key in ("all", "selected", "coverage")}
        report[name] = result
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--update-ratings", action="store_true",
                        help="Run an independent Elo rating trajectory for each advantage")
    args = parser.parse_args()
    leagues = {}
    pooled = {season: [] for season in TARGETS}
    for league in LEAGUES:
        games, hashes = load(league)
        valid = ~games["mac_id"].isin(FORFEIT_GAMES)
        games = games.loc[valid].reset_index(drop=True)
        frame = build_features(games, advantage=REFERENCE)[["mac_id", "elo_diff", "home"]]
        if args.update_ratings:
            for advantage in GRID:
                series = build_features(games, advantage=advantage).set_index("mac_id")["elo_p"]
                frame[f"elo_p_{advantage}"] = frame["mac_id"].map(series)
        frame = frame.merge(games[["mac_id", "tarih_utc", "sezon", "ev_skor", "dep_skor"]],
                            on="mac_id", validate="one_to_one")
        frame["day"] = frame["tarih_utc"].dt.floor("D")
        frame["y"] = (frame["ev_skor"] > frame["dep_skor"]).astype(int)
        seasons = {}
        for season in TARGETS:
            value, prior, options = choose(frame, season)
            rows = create_rows(frame.loc[frame["sezon"].eq(season)], league, value)
            seasons[season] = {"advantage": value, "prior": prior, "prior_options": options,
                               "results": summarize(rows)}
            pooled[season].extend(rows)
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
            raise ValueError(f"{league} archive changed during evaluation")
        leagues[league] = {"seasons": seasons, "input_sha256": hashes,
                           "excluded_forfeits": int((~valid).sum())}
    report = {
        "evidence_kind": "exploratory_retrospective", "reference_points": REFERENCE, "candidate_points": GRID,
        "rating_updates": "candidate_specific" if args.update_ratings else "fixed_reference",
        "leagues": leagues, "seasons": {season: summarize(rows) for season, rows in pooled.items()},
        "completed": summarize([row for season in TARGETS[:-1] for row in pooled[season]]),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
