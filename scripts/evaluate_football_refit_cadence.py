"""Compare dated opponent-model fits at matched forecast lead times."""
import argparse
from datetime import date, timedelta
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.football.challenger import fit
from bbtahmin.football.data import load
from bbtahmin.prospective import prediction_fingerprint
from scripts.evaluate_football_draw import LEAGUES


SEASONS = ("2025-26", "2026-27")
LEADS = (1, 7)
VARIANTS = ("daily", "weekly", "monthly")


def cutoffs(match_day, lead_days):
    """All fits exclude results from their cutoff date onward."""
    forecast_day = date.fromisoformat(match_day) - timedelta(days=lead_days)
    monday = forecast_day - timedelta(days=forecast_day.weekday())
    return dict(zip(VARIANTS, (forecast_day.isoformat(), monday.isoformat(),
                              forecast_day.replace(day=1).isoformat()), strict=True))


def replay(frame, league):
    @lru_cache(maxsize=64)
    def model(cutoff):
        return fit(frame, league, cutoff, "opponent")

    target = frame[(frame["league"] == league) & frame["season"].isin(SEASONS) & (frame["status"] == "final")]
    if target["event_id"].duplicated().any():
        raise ValueError("Target fixtures must be distinct")
    cohorts = {(season, lead): [] for season in SEASONS for lead in LEADS}
    for game in target.sort_values(["date", "event_id"]).itertuples():
        outcome = 0 if game.home_goals > game.away_goals else 2 if game.home_goals < game.away_goals else 1
        for lead in LEADS:
            for name, cutoff in cutoffs(game.date, lead).items():
                predicted = model(cutoff).predict(game.home, game.away)
                if predicted["training_cutoff_exclusive"] != cutoff:
                    raise ValueError("Unexpected model training cutoff")
                probabilities = [predicted["probabilities"][key] for key in ("home", "draw", "away")]
                cohorts[game.season, lead].append(dict(
                    event_id=game.event_id, day=game.date, league=league, variant=name, y=outcome, p=probabilities,
                    selected=not predicted["issues"] and max(probabilities) >= .65, cutoff=cutoff,
                ))
    return cohorts


def summarize(rows):
    result = {}
    for name in VARIANTS:
        part = [r for r in rows if r["variant"] == name]
        result[name] = metrics([r["y"] for r in part], [r["p"] for r in part], [r["selected"] for r in part])
        result[name]["fit_dates"] = len({(r["league"], r["cutoff"]) for r in part})
        if name != "daily":
            result[name]["vs_daily"] = paired(rows, "daily", name, replicates=2000)
    return result


def periods(rows):
    days = sorted({row["day"] for row in rows})
    if len(days) < 2:
        raise ValueError("Two distinct evaluation periods are required")
    boundary = days[len(days) // 2]
    return dict(second_period_start=boundary, all=summarize(rows),
                earlier=summarize([row for row in rows if row["day"] < boundary]),
                later=summarize([row for row in rows if row["day"] >= boundary]))


def evaluate():
    root = Path("data/football")
    paths = sorted(root.rglob("*.json.gz")) + [root / "fixture_reviews.json"]
    hashes = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    frame = load()
    pooled = {(season, lead): [] for season in SEASONS for lead in LEADS}
    leagues = {}
    for league in LEAGUES:
        cohorts = replay(frame, league)
        leagues[league] = {f"{s}/{lead}d": periods(rows) for (s, lead), rows in cohorts.items()}
        for key, rows in cohorts.items():
            pooled[key].extend(rows)
    if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest for path, digest in hashes.items()):
        raise ValueError("Archives changed during evaluation")
    return {
        "evidence_kind": "exploratory_retrospective",
        "input_sha256": hashes, "prediction_code_sha256": prediction_fingerprint(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "leagues": leagues, "pooled": {f"{s}/{lead}d": periods(rows) for (s, lead), rows in pooled.items()},
        "note": "Fixed one- and seven-day leads shared by all variants. Archive replay does not recreate "
                "actual publication timestamps or prove that the schedule was known at forecast time.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(evaluate(), indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
