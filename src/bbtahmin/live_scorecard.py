"""Evaluate immutable forecasts against finals already present in the local ledgers."""

from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .experiment_metrics import losses, validate
from .football.daily import digest as football_digest
from .prospective import verify
from .quality import timestamp


CLASSES = {"basketball": ("home", "away"), "football": ("home", "draw", "away")}
MODEL_NAMES = {"model": "Model", "always_home": "Always home",
               "expanding_rate": "Expanding league rate", "market": "Market"}
SEED = 20261124
REPLICATES = 2000
DEFINITIONS = {
    "cohort": (
        "One game per league and event ID, using the earliest checksum-verified frozen forecast. "
        "A timezone-aware start must be present and strictly later than the freeze. Basketball "
        "finals are joined by forecast checksum and fixture identity across saved settlement checks, "
        "including checks that reference earlier Argentina and prospective forecast records. "
        "Football uses publisher finals from the saved daily report joined to immutable forecasts "
        "by fixture identity and freeze time. Community publisher finals lack official verification. "
        "Football finals with date-only kickoff evidence and matches flagged for fixture review are excluded."
    ),
    "cutoff": (
        "Latest saved settlement check timestamp used, with each sport's cutoff reported separately. "
        "Basketball includes the per-record check timestamps, which can follow the report's start time."
    ),
    "accuracy": "Fraction of games where the highest-probability class occurred. Ties break in class order.",
    "log_loss": "Mean negative natural log of the realized class probability, floored at 1e-15.",
    "brier": (
        "Mean squared error of the home-win probability for basketball, (p_home − y_home)². "
        "Football sums the squared probability errors over home, draw and away before averaging."
    ),
    "confidence_intervals": (
        f"95% Wilson score intervals for accuracy. Log loss and Brier use the 2.5th and 97.5th "
        f"percentiles of {REPLICATES:,} bootstrap samples of games with replacement "
        f"(NumPy default_rng seed {SEED}, reset per cohort). Games are the resampling unit."
    ),
    "always_home": "Assigns probability 1 to home and 0 to every other class.",
    "expanding_rate": (
        "Per-league class counts from eligible ledger finals known strictly before each forecast "
        "was frozen. Add one prior count per class, giving a uniform forecast at cold start. "
        "Basketball uses the earliest saved final capture time. Football uses the saved report's check "
        "time because it has no per-game final observation times. All football forecasts in that "
        "single snapshot therefore receive uniform rates."
    ),
    "market": (
        "Use only complete decimal odds greater than 1 from the frozen prediction. Read decimal_odds "
        "by class, or oran_ev and oran_dep for basketball. Normalize reciprocals to sum to one. "
        "The market row and its companion model row cover the same odds-available games."
    ),
    "calibration": (
        "Group by highest forecast probability in left-closed 10 percentage-point bins, with 100% "
        "included in the last bin. Observed frequency is the fraction whose top pick occurred. "
        "Bins begin at 50% for basketball and 30% for football to cover all 1X2 favourites."
    ),
}


@dataclass(frozen=True)
class Game:
    league: str
    event_id: str
    frozen_at: pd.Timestamp
    known_at: pd.Timestamp
    outcome: int
    probabilities: tuple[float, ...]
    market: tuple[float, ...] | None


def _key(fixture):
    return fixture["league"], fixture["event_id"]


def _retain_earliest(forecasts, fixture, record, item):
    key = _key(fixture)
    candidate = (timestamp(record["recorded_at_utc"]), record["payload_sha256"], item)
    old = forecasts.get(key)
    if old is None or candidate[:2] < old[:2]:
        forecasts[key] = candidate


def _market(prediction, classes):
    odds = prediction.get("decimal_odds")
    if odds is None and len(classes) == 2:
        odds = {"home": prediction.get("oran_ev"), "away": prediction.get("oran_dep")}
    if not isinstance(odds, dict):
        return None
    prices = [odds.get(label) for label in classes]
    if any(type(price) not in (int, float) or not np.isfinite(price) or price <= 1 for price in prices):
        return None
    implied = 1 / np.array(prices, dtype=float)
    return tuple(implied / implied.sum())


def _game(sport, frozen, start, known, final):
    frozen_at, _, item = frozen
    fixture, prediction = item["fixture"], item["prediction"]
    if not frozen_at < start < known:
        raise ValueError(f"Invalid freeze/start/final timing for {_key(fixture)}")
    home, away = final["actual_home"], final["actual_away"]
    if any(type(score) is not int or score < 0 for score in (home, away)):
        raise ValueError(f"Invalid final scores for {_key(fixture)}")
    if sport == "basketball":
        if min(home, away) == 0 or home == away:
            raise ValueError(f"Invalid basketball final for {_key(fixture)}")
        p_home = prediction["ev_kazanir"]
        probabilities = (p_home, 1 - p_home)
    else:
        probabilities = tuple(prediction["probabilities"][label] for label in CLASSES[sport])
    label = "home" if home > away else "away" if home < away else "draw"
    outcome = CLASSES[sport].index(label)
    return Game(*_key(fixture), frozen_at, known, outcome, probabilities,
                _market(prediction, CLASSES[sport]))


def _basketball_games(records, checks):
    forecasts = {}
    frozen_ids = set()
    for record in records:
        if record["spec"] != "prospective-v1":
            raise ValueError("Unexpected basketball forecast schema")
        verify(record)
        for item in record["forecasts"]:
            _retain_earliest(forecasts, item["fixture"], record, item)
            frozen_ids.add((record["payload_sha256"], item["fixture"]["event_id"]))

    cutoffs = []
    finals = {}
    for check in checks:
        if check["spec"] != "daily-research-v1":
            raise ValueError("Unexpected basketball report schema")
        cutoffs.append(timestamp(check["checked_at_utc"]))
        for batch in check["settlements"]:
            checked_at = timestamp(batch["checked_at_utc"])
            cutoffs.append(checked_at)
            for result in batch["games"]:
                if result["status"] != "final":
                    continue
                key = (batch["forecast_sha256"], result["event_id"])
                if key not in frozen_ids:
                    raise ValueError(f"Basketball final has no matching frozen forecast for {key}")
                known_at = timestamp(result["captured_at"])
                if known_at > checked_at:
                    raise ValueError(f"Final captured after settlement check for {key}")
                old = finals.get(key)
                identity_fields = ("home", "away", "actual_home", "actual_away")
                if old and any(old[1][field] != result[field] for field in identity_fields):
                    raise ValueError(f"Conflicting basketball finals for {key}")
                if old is None or known_at < old[0]:
                    finals[key] = (known_at, result)

    games = []
    for frozen in forecasts.values():
        _, checksum, item = frozen
        fixture = item["fixture"]
        final = finals.get((checksum, fixture["event_id"]))
        if final is None:
            continue
        known_at, result = final
        if any(fixture[side] != result[side] for side in ("home", "away")):
            raise ValueError(f"Result identity mismatch for {_key(fixture)}")
        games.append(_game("basketball", frozen, timestamp(fixture["start_utc"]), known_at, result))
    return games, max(cutoffs, default=None)


def _football_games(records, report):
    forecasts = {}
    for record in records:
        payload = dict(record)
        checksum = payload.pop("payload_sha256")
        if record["spec"] != "football-prospective-v1" or football_digest(payload) != checksum:
            raise ValueError("Invalid frozen football forecast")
        _retain_earliest(forecasts, record["fixture"], record, record)
    if report is None:
        return [], None, {}
    if report["spec"] != "football-daily-v1":
        raise ValueError("Unexpected football report schema")
    checked_at = timestamp(report["checked_at_utc"])
    games = []
    seen = set()
    missing_kickoff = Counter()
    for row in report["forecasts"]:
        if row["status"] != "publisher_final" or row.get("fixture_review"):
            continue
        fixture = row["fixture"]
        key = _key(fixture)
        frozen = forecasts.get(key)
        if (frozen is None or frozen[0] != timestamp(row["recorded_at_utc"])
                or frozen[2]["fixture"] != fixture or key in seen):
            raise ValueError(f"Football final does not match a unique frozen forecast for {key}")
        seen.add(key)
        if not fixture.get("verified_start_utc"):
            missing_kickoff[fixture["league"]] += 1
            continue
        start = timestamp(fixture["verified_start_utc"])
        games.append(_game("football", frozen, start, checked_at, row["result"]))
    return games, checked_at, missing_kickoff


def expanding_rates(games, class_count):
    """Return predictions aligned with games, using only finals known at freeze time."""
    counts = defaultdict(lambda: np.ones(class_count, dtype=int))
    finals = iter(sorted(games, key=lambda game: game.known_at))
    result = next(finals, None)
    rates = np.empty((len(games), class_count))
    for index in sorted(range(len(games)), key=lambda i: games[i].frozen_at):
        game = games[index]
        while result is not None and result.known_at < game.frozen_at:
            counts[result.league][result.outcome] += 1
            result = next(finals, None)
        league_counts = counts[game.league]
        rates[index] = league_counts / league_counts.sum()
    return rates


def _metrics(outcomes, probabilities, sport):
    names = ("accuracy", "log_loss", "brier")
    n = len(outcomes)
    if not n:
        return {"n": 0, **dict.fromkeys(names), "ci95": dict.fromkeys(names)}
    values = losses(outcomes, probabilities)
    if sport == "basketball":
        values[:, 2] /= 2
    means = values.mean(axis=0)
    accuracy = means[0]
    z = 1.959963984540054
    denominator = 1 + z**2 / n
    center = (accuracy + z**2 / (2 * n)) / denominator
    radius = z * np.sqrt(accuracy * (1 - accuracy) / n + z**2 / (4 * n**2)) / denominator

    rng = np.random.default_rng(SEED)
    samples = np.empty((REPLICATES, 2))
    for index in range(REPLICATES):
        draw = rng.integers(n, size=n)
        samples[index] = values[draw, 1:].mean(axis=0)
    bounds = np.quantile(samples, [.025, .975], axis=0)
    ci = [[float(max(0, center - radius)), float(min(1, center + radius))],
          *bounds.T.tolist()]
    return {"n": n, **dict(zip(names, means.tolist())), "ci95": dict(zip(names, ci))}


def _group(games, rates, sport):
    classes = CLASSES[sport]
    outcomes = np.array([game.outcome for game in games], dtype=int)
    probabilities = np.array([game.probabilities for game in games]).reshape(-1, len(classes))
    outcomes, probabilities = validate(outcomes, probabilities)
    always_home = np.zeros_like(probabilities)
    always_home[:, 0] = 1
    model = _metrics(outcomes, probabilities, sport)
    group = {
        "model": model,
        "always_home": _metrics(outcomes, always_home, sport),
        "expanding_rate": _metrics(outcomes, rates, sport),
    }
    market_indices = [i for i, game in enumerate(games) if game.market is not None]
    market = np.array([games[i].market for i in market_indices]).reshape(-1, len(classes))
    group["market"] = {
        "status": "available" if market_indices else "no market data",
        "metrics": _metrics(outcomes[market_indices], market, sport),
        "model_same_games": (
            model if games and len(market_indices) == len(games)
            else _metrics(outcomes[market_indices], probabilities[market_indices], sport)
        ),
    }
    picks = probabilities.argmax(axis=1)
    confidence = probabilities.max(axis=1)
    bins = []
    for decile in range(5 if sport == "basketball" else 3, 10):
        lo, hi = decile / 10, (decile + 1) / 10
        mask = (confidence >= lo) & ((confidence < hi) if hi < 1 else (confidence <= hi))
        n = int(mask.sum())
        bins.append({
            "lower": lo, "upper": hi, "n": n,
            "forecast_mean": float(confidence[mask].mean()) if n else None,
            "observed_frequency": float((picks[mask] == outcomes[mask]).mean()) if n else None,
        })
    group["calibration"] = bins
    if sport == "football":
        group["class_frequencies"] = {
            label: {
                "top_pick_n": int((picks == i).sum()),
                "top_pick_rate": float((picks == i).mean()) if games else None,
                "actual_n": int((outcomes == i).sum()),
                "actual_rate": float((outcomes == i).mean()) if games else None,
            } for i, label in enumerate(classes)
        }
    return group


def _sport_summary(games, cutoff, sport, additional_leagues=()):
    games = sorted(games, key=lambda game: (game.league, game.event_id))
    rates = expanding_rates(games, len(CLASSES[sport]))
    leagues = defaultdict(list)
    for i, game in enumerate(games):
        leagues[game.league].append(i)
    return {
        "cutoff_utc": cutoff.isoformat() if cutoff is not None else None,
        "class_order": list(CLASSES[sport]),
        "total": _group(games, rates, sport),
        "leagues": {
            league: _group([games[i] for i in leagues[league]], rates[leagues[league]], sport)
            for league in sorted(set(leagues).union(additional_leagues))
        },
    }


def build_scorecard(basketball_records, basketball_checks, football_records, football_report):
    """Combine parsed ledger snapshots into a JSON-serializable evaluation."""
    basketball, basketball_cutoff = _basketball_games(basketball_records, basketball_checks)
    football, football_cutoff, missing_kickoff = _football_games(football_records, football_report)
    cutoff = max((value for value in (basketball_cutoff, football_cutoff) if value is not None),
                 default=None)
    sports = {
        "basketball": _sport_summary(basketball, basketball_cutoff, "basketball"),
        "football": _sport_summary(football, football_cutoff, "football", missing_kickoff),
    }
    sports["football"]["publisher_finals_excluded_no_verified_kickoff"] = sum(missing_kickoff.values())
    sports["football"]["kickoff_exclusions_by_league"] = dict(sorted(missing_kickoff.items()))
    return {
        "spec": "live-scorecard-v1",
        "data_cutoff_utc": cutoff.isoformat() if cutoff is not None else None,
        "definitions": dict(DEFINITIONS),
        "sports": sports,
    }


def _display(value, percent=False):
    if value is None:
        return "—"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def markdown(report):
    """Render the same scorecard as readable Markdown tables."""
    lines = ["# Live forecast scorecard", "",
             f"Data cutoff (UTC) **{report['data_cutoff_utc'] or 'unavailable'}**.", "",
             "## Definitions", ""]
    lines.extend(f"- **{key.replace('_', ' ').capitalize()}**. {value}"
                 for key, value in report["definitions"].items())
    for sport, summary in report["sports"].items():
        groups = [("Total", summary["total"]), *summary["leagues"].items()]
        lines += ["", f"## {sport.capitalize()}", "",
                  f"Ledger cutoff (UTC) **{summary['cutoff_utc'] or 'unavailable'}**.",
                  f"Class order is {', '.join(summary['class_order'])}."]
        if sport == "football":
            count = summary["publisher_finals_excluded_no_verified_kickoff"]
            lines.append(f"Excluded {count} publisher finals without a verified kickoff timestamp.")
            if count:
                breakdown = ", ".join(f"{league} {n}"
                                      for league, n in summary["kickoff_exclusions_by_league"].items())
                lines.append(f"Kickoff exclusions by league ({breakdown}).")
        lines += ["", "| League | Forecast | n | Accuracy (95% CI) | Log loss (95% CI) | Brier (95% CI) |",
                  "|---|---|---:|---:|---:|---:|"]

        def metric_row(league, label, metrics):
            cells = []
            for name in ("accuracy", "log_loss", "brier"):
                value = _display(metrics[name], name == "accuracy")
                bounds = metrics["ci95"][name]
                if bounds is not None:
                    low, high = (_display(x, name == "accuracy") for x in bounds)
                    value += f" [{low}, {high}]"
                cells.append(value)
            return f"| {league} | {label} | {metrics['n']} | {' | '.join(cells)} |"

        for league, group in groups:
            for name in ("model", "always_home", "expanding_rate"):
                lines.append(metric_row(league, MODEL_NAMES[name], group[name]))
            market = group["market"]
            if market["status"] == "available":
                lines.append(metric_row(league, MODEL_NAMES["market"], market["metrics"]))
                lines.append(metric_row(league, "Model on market games", market["model_same_games"]))
            else:
                lines.append(f"| {league} | Market (no market data) | 0 | — | — | — |")
        lines += ["", "### Model calibration", "",
                  "| League | Favourite probability | n | Forecast mean | Observed frequency |",
                  "|---|---|---:|---:|---:|"]
        for league, group in groups:
            for bin_ in group["calibration"]:
                lines.append(
                    f"| {league} | {bin_['lower']:.0%}–{bin_['upper']:.0%} | {bin_['n']} | "
                    f"{_display(bin_['forecast_mean'], True)} | {_display(bin_['observed_frequency'], True)} |"
                )
        if sport == "football":
            lines += ["", "### Model top picks and actual outcomes", "",
                      "| League | Class | Top pick n | Top pick rate | Actual n | Actual rate |",
                      "|---|---|---:|---:|---:|---:|"]
            for league, group in groups:
                for label, counts in group["class_frequencies"].items():
                    lines.append(
                        f"| {league} | {label} | {counts['top_pick_n']} | "
                        f"{_display(counts['top_pick_rate'], True)} | {counts['actual_n']} | "
                        f"{_display(counts['actual_rate'], True)} |"
                    )
    return "\n".join(lines) + "\n"
