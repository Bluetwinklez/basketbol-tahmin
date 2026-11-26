"""Compare flat and recency-weighted seven-day basketball workload."""
import argparse
from collections import defaultdict, deque
import hashlib
from itertools import groupby
import json
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

from bbtahmin.asia_model import fit_fold
from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.ozellik import build_features
from bbtahmin.prospective import prediction_fingerprint
from bbtahmin.shadow_models import FORFEIT_GAMES
from scripts.evaluate_basketball_logit_blend import LEAGUES, SEASONS
from scripts.evaluate_improvement_basketball import load


HALF_LIFE_DAYS = 2.0
LOOKBACK_DAYS = 7
CONFIDENCE = 0.65


def workload(games):
    """One score-free workload difference per fixture, using earlier UTC days."""
    history = defaultdict(deque)
    values = {}
    ordered = games.assign(day=games["tarih_utc"].dt.floor("D")).sort_values(["day", "mac_id"])
    for day, group in groupby(ordered.itertuples(index=False), key=lambda game: game.day):
        batch = list(group)
        for game in batch:
            loads = []
            for team in (game.ev, game.dep):
                dates = history[game.lig, team]
                while dates and (day - dates[0]).days > LOOKBACK_DAYS:
                    dates.popleft()
                loads.append(sum(2 ** (-(day - past).days / HALF_LIFE_DAYS) for past in dates))
            values[game.mac_id] = loads[0] - loads[1]
        for game in batch:
            if np.isfinite(game.ev_skor) and np.isfinite(game.dep_skor):
                history[game.lig, game.ev].append(day)
                history[game.lig, game.dep].append(day)
    return games["mac_id"].map(values).to_numpy(float)


def summarize(rows):
    result = paired(rows, "reference", "candidate", replicates=2000)
    days = sorted({row["day"] for row in rows})
    boundary = days[len(days) // 2]
    result["second_period_start"] = boundary
    result["variants"] = {}
    for variant in ("reference", "candidate"):
        observations = [row for row in rows if row["variant"] == variant]
        result["variants"][variant] = {}
        for period, group in (
            ("all", observations),
            ("early", [row for row in observations if row["day"] < boundary]),
            ("late", [row for row in observations if row["day"] >= boundary]),
        ):
            p = [row["p"] for row in group]
            summary = metrics([row["y"] for row in group], p, [max(q) >= CONFIDENCE for q in p])
            result["variants"][variant][period] = {key: summary[key] for key in ("all", "selected", "coverage")}
    return result


def evaluate():
    leagues = {}
    pooled = {season: [] for season in SEASONS}
    for league in LEAGUES:
        games, hashes = load(league)
        valid = ~games["mac_id"].isin(FORFEIT_GAMES)
        games = games.loc[valid].reset_index(drop=True)
        reference = build_features(games)
        candidate = reference.assign(load7_diff=workload(games))
        seasons = {}
        for season in SEASONS:
            fixtures = games.loc[games["sezon"].eq(season)]
            if fixtures.empty:
                raise ValueError(f"Missing {league} fixtures in {season}")
            prior = games.loc[games["sezon"].lt(season), "tarih_utc"]
            if prior.empty or prior.max() >= fixtures["tarih_utc"].min():
                raise ValueError(f"Training seasons overlap target dates in {league} {season}")
            rows = []
            learners = {}
            for variant, features in (("reference", reference), ("candidate", candidate)):
                probs, _, _, policy = fit_fold(games, features, season)
                learners[variant] = policy
                rows.extend(
                    dict(event_id=f"{league}:{game.mac_id}", day=game.tarih_utc.strftime("%Y-%m-%d"),
                         variant=variant, y=int(game.ev_skor > game.dep_skor), p=[1 - float(p), float(p)])
                    for game, p in zip(fixtures.itertuples(), probs[policy["selected"]], strict=True)
                )
            seasons[season] = dict(learners=learners, **summarize(rows))
            pooled[season].extend(rows)
        if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
            raise ValueError(f"{league} archive changed during evaluation")
        leagues[league] = dict(seasons=seasons, input_sha256=hashes, excluded_forfeits=int((~valid).sum()))
    return {
        "evidence_kind": "exploratory_retrospective",
        "prediction_code_sha256": prediction_fingerprint(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "workload_half_life_days": HALF_LIFE_DAYS,
        "lookback_days": LOOKBACK_DAYS,
        "leagues": leagues,
        "seasons": {season: summarize(rows) for season, rows in pooled.items()},
        "completed": summarize([r for season in SEASONS[:-1] for r in pooled[season]]),
        "note": "Same common learner policy, not every production model. Observed competition load only. "
                "Historical result publication times are unverified. No promotion from a retrospective.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        report = evaluate()
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
