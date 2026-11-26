"""Replay Elo with a Davidson draw term against opponent-adjusted football."""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np

from bbtahmin.football.challenger import fit
from bbtahmin.football.data import load
from bbtahmin.prospective import prediction_fingerprint
from scripts.evaluate_football_draw import LEAGUES
from scripts.evaluate_football_refit_cadence import SEASONS, cutoffs
from scripts.evaluate_football_promoted_prior import compare


START_YEAR = "2018-07-01"
HOME_ADVANTAGE = 60.
UPDATE_RATE = 30.
PRIOR_GAMES = 50
PRIOR_DRAWS = 14


class DavidsonElo:
    def __init__(self):
        self.rating = defaultdict(float)
        self.games = PRIOR_GAMES
        self.draws = PRIOR_DRAWS

    def predict(self, home, away):
        d = (self.rating.get(home, 0.) - self.rating.get(away, 0.) + HOME_ADVANTAGE) / 800
        draw_weight = 2 * self.draws / (self.games - self.draws)
        p = np.array([10**d, draw_weight, 10**(-d)])
        return p / p.sum()

    def observe_day(self, games):
        changes = defaultdict(float)
        for g in games:
            p = self.predict(g.home, g.away)
            actual = 1. if g.home_goals > g.away_goals else 0. if g.home_goals < g.away_goals else .5
            step = UPDATE_RATE * (actual - p[0] - .5 * p[1])
            changes[g.home] += step
            changes[g.away] -= step
        for g in games:
            self.draws += g.home_goals == g.away_goals
            self.games += 1
        for team, change in changes.items():
            self.rating[team] += change


def replay(frame, league):
    @lru_cache(maxsize=10)
    def model(cutoff):
        return fit(frame, league, cutoff, "opponent")

    games = frame[(frame["league"] == league) & (frame["status"] == "final") & (frame["date"] >= START_YEAR)]
    if games["event_id"].duplicated().any():
        raise ValueError("Distinct match identities required")
    games = games.sort_values(["date", "event_id"])
    days = iter(games.groupby("date", sort=False))
    next_day = next(days, None)
    rating = DavidsonElo()
    rows = {s: [] for s in SEASONS}
    candidate = {s: [] for s in SEASONS}
    for game in games.loc[games["season"].isin(SEASONS)].itertuples():
        cutoff = cutoffs(game.date, 7)["weekly"]
        while next_day is not None and next_day[0] < cutoff:
            rating.observe_day(list(next_day[1].itertuples()))
            next_day = next(days, None)
        predicted = model(cutoff).predict(game.home, game.away)
        rows[game.season].append(dict(
            event_id=game.event_id, day=game.date,
            y=0 if game.home_goals > game.away_goals else 2 if game.home_goals < game.away_goals else 1,
            p=[predicted["probabilities"][key] for key in ("home", "draw", "away")],
            eligible=not predicted["issues"],
        ))
        candidate[game.season].append(rating.predict(game.home, game.away))
    return rows, candidate


def evaluate():
    root = Path("data/football")
    paths = sorted(root.rglob("*.json.gz")) + [root / "fixture_reviews.json"]
    hashes = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    frame = load()
    pooled = {s: [] for s in SEASONS}
    alternatives = {s: [] for s in SEASONS}
    leagues = {}
    for league in LEAGUES:
        rows, candidate = replay(frame, league)
        leagues[league] = {s: compare(rows[s], candidate[s]) for s in SEASONS}
        for s in SEASONS:
            pooled[s].extend(rows[s])
            alternatives[s].extend(candidate[s])
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
        raise ValueError("Archives changed during evaluation")
    periods = {}
    for s, rows in pooled.items():
        days = sorted({r["day"] for r in rows})
        boundary = days[len(days) // 2]
        earlier = [(r, p) for r, p in zip(rows, alternatives[s], strict=True) if r["day"] < boundary]
        later = [(r, p) for r, p in zip(rows, alternatives[s], strict=True) if r["day"] >= boundary]
        periods[s] = dict(all=compare(rows, alternatives[s]),
                          earlier=compare(*zip(*earlier)), later=compare(*zip(*later)),
                          second_period_start=boundary)
    return dict(evidence_kind="exploratory_retrospective", leagues=leagues, pooled=periods,
                input_sha256=hashes, prediction_code_sha256=prediction_fingerprint(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                note="Fixed Elo parameters, expanding observed draw rate, seven-day lead and matching weekly cutoffs.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(evaluate(), indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
