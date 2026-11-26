"""Test opponent-strength recency with season-ahead selection."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.football.challenger import OpponentGoalModel
from bbtahmin.football.data import load
from bbtahmin.football.model import GoalModel
from bbtahmin.prospective import prediction_fingerprint
from scripts.evaluate_football_draw import LEAGUES
from scripts.evaluate_football_refit_cadence import cutoffs


SEASONS = ("2024-25", "2025-26", "2026-27")
HALF_LIVES = (90, 180, 360)
REFERENCE = 180
LEAD_DAYS = 7


class ResearchRecency(GoalModel):
    def __init__(self, history, league, cutoff):
        super().__init__(history, league, cutoff, half_life=self.research_half_life)


class ResearchOpponent(OpponentGoalModel, ResearchRecency):
    """Use the production opponent fit with an alternate GoalModel recency."""

    def __init__(self, history, league, cutoff, half_life):
        self.research_half_life = half_life
        super().__init__(history, league, cutoff, low_score=False)


def replay(frame, league):
    @lru_cache(maxsize=36)
    def model(cutoff, half_life):
        return ResearchOpponent(frame, league, cutoff, half_life)

    target = frame[(frame["league"] == league) & frame["season"].isin(SEASONS) & (frame["status"] == "final")]
    if target["event_id"].duplicated().any():
        raise ValueError("Duplicate replay fixture")
    result = {season: [] for season in SEASONS}
    for g in target.sort_values(["date", "event_id"]).itertuples():
        cutoff = cutoffs(g.date, LEAD_DAYS)["weekly"]
        y = 0 if g.home_goals > g.away_goals else 2 if g.home_goals < g.away_goals else 1
        for half_life in HALF_LIVES:
            prediction = model(cutoff, half_life).predict(g.home, g.away)
            p = [prediction["probabilities"][label] for label in ("home", "draw", "away")]
            result[g.season].append(dict(event_id=g.event_id, day=g.date, y=y, p=p, variant=str(half_life),
                                         selected=not prediction["issues"] and max(p) >= .65))
    return result


def stats(rows, variant):
    kept = [row for row in rows if row["variant"] == str(variant)]
    return metrics([r["y"] for r in kept], [r["p"] for r in kept], [r["selected"] for r in kept])


def split_days(rows):
    days = sorted({r["day"] for r in rows})
    if len(days) < 2:
        raise ValueError("Need two chronological periods")
    boundary = days[len(days) // 2]
    return [r for r in rows if r["day"] < boundary], [r for r in rows if r["day"] >= boundary]


def choose(prior, target):
    if max(r["day"] for r in prior) >= min(r["day"] for r in target):
        raise ValueError("Selection must use a strictly earlier season")
    calibration, validation = split_days(prior)
    scores = {h: stats(calibration, h)["all"] for h in HALF_LIVES}
    selected = min(scores, key=lambda h: (scores[h]["log_loss"], abs(h - REFERENCE)))
    reference = stats(validation, REFERENCE)["all"]
    candidate = stats(validation, selected)["all"]
    passed = (candidate["accuracy"] >= reference["accuracy"] + .01
              and candidate["log_loss"] <= reference["log_loss"] - .005
              and candidate["brier"] <= reference["brier"])
    return dict(calibration_choice=selected, kept=selected if passed else REFERENCE,
                validation_reference=reference, validation_candidate=candidate, passed=passed)


def summarize(rows):
    report = {}
    for variant in (*HALF_LIVES, "prior_selected"):
        result = stats(rows, variant)
        if variant != REFERENCE:
            result["vs_180"] = paired(rows, str(REFERENCE), str(variant), replicates=2000)
        report[str(variant)] = result
    return report


def evaluate():
    root = Path("data/football")
    paths = sorted(root.rglob("*.json.gz")) + [root / "fixture_reviews.json"]
    hashes = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    frame = load()
    leagues = {}
    pooled = {season: [] for season in SEASONS[1:]}
    for league in LEAGUES:
        seasons = replay(frame, league)
        summaries = {}
        for prior, target in zip(SEASONS[:-1], SEASONS[1:], strict=True):
            policy = choose(seasons[prior], seasons[target])
            rows = seasons[target] + [dict(r, variant="prior_selected") for r in seasons[target]
                                       if r["variant"] == str(policy["kept"])]
            summaries[target] = dict(selection=policy, results=summarize(rows))
            pooled[target].extend(rows)
        leagues[league] = summaries
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
        raise ValueError("Archives changed during evaluation")
    report = {}
    for season, rows in pooled.items():
        early, late = split_days(rows)
        report[season] = dict(all=summarize(rows), earlier=summarize(early), later=summarize(late))
    return {
        "evidence_kind": "exploratory_retrospective", "lead_days": LEAD_DAYS,
        "half_lives": HALF_LIVES, "input_sha256": hashes,
        "prediction_code_sha256": prediction_fingerprint(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "leagues": leagues, "pooled": report,
        "note": "Matched weekly model cutoffs at a fixed seven-day lead. The archived calendar does "
                "not establish point-in-time availability or actual pregame publication.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(evaluate(), indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
