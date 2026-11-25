"""Offline calibration evidence from the live scorecard's football cohort."""

from collections import Counter
from dataclasses import replace

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from .experiment_metrics import losses, validate
from .live_scorecard import (
    CLASSES, REPLICATES, SEED, _football_games, _key, _retain_earliest, expanding_rates,
)


MIN_PRIOR = 30
MIN_EVALUATION = 30
MARKETS = {"over_2_5": "Over 2.5 goals", "btts": "BTTS"}
METRICS = ("accuracy", "log_loss", "brier")
INCONCLUSIVE = "inconclusive (n too small)"
SKILL_VERDICTS = ("skill_over_baseline", "no_skill_over_baseline")
RECALIBRATION_VERDICTS = ("supports recalibration", "does not support recalibration")
RELIABILITY_SCOPE = "Reliability bins and logistic slopes are descriptive only for the original frozen forecasts."


def verdict(n, interval, *, labels):
    if n < MIN_EVALUATION or interval is None:
        return INCONCLUSIVE
    positive, nonpositive = labels
    return positive if interval[0] > 0 else nonpositive


def walk_forward(games, temperatures, scale):
    """Scale predictions in freeze order and return the prior count and choice per game."""
    order = sorted(range(len(games)), key=lambda i: (games[i].frozen_at, games[i].league,
                                                     games[i].event_id))
    finals = iter(sorted((games[i] for i in order), key=lambda game: game.known_at))
    result = next(finals, None)
    prior_n = 0
    cumulative_loss = np.zeros(len(temperatures))
    transformed = np.empty((len(games), 3))
    audit = [None] * len(games)
    for i in order:
        game = games[i]
        while result is not None and result.known_at < game.frozen_at:
            actual = [scale(result.probabilities, t)[result.outcome] for t in temperatures]
            cumulative_loss -= np.log(np.clip(actual, 1e-15, 1))
            prior_n += 1
            result = next(finals, None)
        chosen = None
        if prior_n >= MIN_PRIOR:
            best = min(range(len(temperatures)),
                       key=lambda j: (cumulative_loss[j], abs(temperatures[j] - 1)))
            chosen = temperatures[best]
        transformed[i] = (
            game.probabilities if chosen is None or chosen == 1
            else scale(game.probabilities, chosen)
        )
        audit[i] = {"league": game.league, "event_id": game.event_id,
                    "frozen_at_utc": game.frozen_at.isoformat(),
                    "prior_n": prior_n, "temperature": chosen}
    return transformed, audit


def _interval(samples):
    return np.quantile(samples, [.025, .975], axis=0).T.tolist()


def _draws(n):
    return np.random.default_rng(SEED).integers(n, size=(REPLICATES, n))


def _paired(reference, candidate, names=METRICS):
    n = len(reference)
    draws = _draws(n) if n else None

    def summary(values):
        means = values.mean(axis=0).tolist() if n else [None] * len(names)
        intervals = _interval(values[draws].mean(axis=1)) if n else [None] * len(names)
        return {**dict(zip(names, means)), "ci95": dict(zip(names, intervals))}

    delta = candidate - reference
    delta[:, 1:] *= -1  # Positive means better for every metric.
    return {"n": n, "reference": summary(reference), "candidate": summary(candidate),
            "improvement": summary(delta)}


def _bins(probability, occurred):
    labels = np.minimum((probability * 10).astype(int), 9)
    rows = []
    for bin_id in range(10):
        mask = labels == bin_id
        n = int(mask.sum())
        rows.append({"lower": bin_id / 10, "upper": (bin_id + 1) / 10, "n": n,
                     "forecast_mean": float(probability[mask].mean()) if n else None,
                     "observed_frequency": float(occurred[mask].mean()) if n else None})
    return rows


def _logistic_fit(x, y):
    # A finite unpenalized slope requires overlap and variation in the predictor.
    yes, no = x[y], x[~y]
    if not len(yes) or not len(no) or yes.max() <= no.min() or no.max() <= yes.min():
        return None
    if np.ptp(x) < 1e-12:
        return None
    center, spread = x.mean(), x.std()
    design = np.column_stack((np.ones(len(x)), (x - center) / spread))
    signed_design = (1 - 2 * y.astype(int))[:, None] * design

    def objective(beta):
        z = signed_design @ beta
        return np.logaddexp(0, z).mean(), signed_design.T @ expit(z) / len(x)

    fit = minimize(objective, [logit(y.mean()), 0.0], jac=True, method="BFGS",
                   options={"gtol": 1e-9})
    if not fit.success and np.linalg.norm(fit.jac, ord=np.inf) > 1e-7:
        return None
    intercept, slope = fit.x
    return [float(intercept - slope * center / spread), float(slope / spread)]


def _reliability(probability, occurred, draws):
    x = logit(np.clip(probability, 1e-15, 1 - 1e-15))
    point = _logistic_fit(x, occurred)
    estimates = []
    if point is not None:
        for draw in draws:
            fit = _logistic_fit(x[draw], occurred[draw])
            if fit is not None:
                estimates.append(fit)
    # Report an interval only when at least 95% of replicates have a finite fit.
    intervals = _interval(estimates) if len(estimates) >= .95 * REPLICATES else [None, None]
    names = ("intercept", "slope")
    return {"bins": _bins(probability, occurred),
            "logistic": {**dict(zip(names, point or [None, None])),
                         "ci95": dict(zip(names, intervals)),
                         "valid_bootstrap_fits": len(estimates)}}


def _binary_losses(y, p):
    return np.column_stack(((p >= .5) == y, -np.log(np.clip(np.where(y, p, 1 - p), 1e-15, 1)),
                            (p - y)**2))


def _binary_market(games, probabilities, outcomes):
    # Expanding league counts also use eligible finals without this forecast field.
    binary_games = [
        replace(game, outcome=int(y))
        for game, y in zip(games, outcomes)
    ]
    baseline = expanding_rates(binary_games, 2)[:, 1]
    keep = np.array([p is not None for p in probabilities], dtype=bool)
    p = np.array([p for p in probabilities if p is not None], dtype=float)
    y = np.asarray(outcomes, dtype=bool)[keep]
    comparison = _paired(_binary_losses(y, baseline[keep]), _binary_losses(y, p),
                         ("hit_rate", "log_loss", "brier"))
    comparison["missing_probability"] = int((~keep).sum())
    comparison["baseline_mean_probability"] = float(baseline[keep].mean()) if len(p) else None
    comparison["skill_verdict"] = verdict(
        comparison["n"], comparison["improvement"]["ci95"]["log_loss"], labels=SKILL_VERDICTS,
    )
    return comparison


def _market_probability(prediction, field):
    if field == "over_2_5":
        value = (prediction.get("over") or {}).get("2.5")
    else:
        value = prediction.get("both_teams_score")
    if value is not None and (type(value) not in (int, float) or not 0 <= value <= 1):
        raise ValueError(f"Invalid frozen probability for {field}")
    return value


def build_report(records, snapshot, temperatures, scale):
    """Reuse scorecard verification and join, then score the untouched forecasts."""
    records = list(records)
    games, cutoff, missing_kickoff = _football_games(records, snapshot)
    games.sort(key=lambda game: (game.frozen_at, game.league, game.event_id))
    rows = snapshot["forecasts"] if snapshot is not None else []
    review = [row for row in rows if row.get("fixture_review") or row["status"] == "fixture_review_required"]
    other = Counter(row["status"] for row in rows
                    if row["status"] not in ("publisher_final", "fixture_review_required")
                    and not row.get("fixture_review"))
    exclusions = {
        "total_snapshot_rows_excluded": len(rows) - len(games),
        "publisher_finals_without_verified_kickoff": sum(missing_kickoff.values()),
        "missing_kickoff_by_league": dict(sorted(missing_kickoff.items())),
        "fixture_review": len(review),
        "other_nonfinal_by_status": dict(sorted(other.items())),
    }

    y, p = validate([game.outcome for game in games],
                    np.array([game.probabilities for game in games]).reshape(-1, 3))
    draws = _draws(len(games)) if games else ()
    reliability = {
        label: _reliability(p[:, i], y == i, draws)
        for i, label in enumerate(CLASSES["football"])
    }
    top_pick = _bins(p.max(axis=1), p.argmax(axis=1) == y)
    scaled, choices = walk_forward(games, temperatures, scale)
    fitted_n = sum(row["temperature"] is not None for row in choices)
    comparison = _paired(losses(y, p), losses(y, scaled))
    comparison.update(
        walk_forward_ran=fitted_n > 0,
        fitted_n=fitted_n,
        fallback_n=len(y) - fitted_n,
        choices=choices,
        recalibration_verdict=verdict(
            fitted_n, comparison["improvement"]["ci95"]["log_loss"], labels=RECALIBRATION_VERDICTS,
        ),
    )
    if not fitted_n:
        comparison["walk_forward_limitation"] = (
            f"Walk-forward temperature fitting could not run at all. {fitted_n} of {len(y)} games "
            f"had at least {MIN_PRIOR} earlier finals known before freeze because the football ledger "
            "has no per-game result times. No temperature was applied, and no calibration "
            "conclusion is possible yet. " + RELIABILITY_SCOPE
        )

    # Recover extra fields from the same frozen record chosen by the scorecard.
    forecasts = {}
    for record in records:
        _retain_earliest(forecasts, record["fixture"], record, record)
    finals = {_key(row["fixture"]): row for row in rows
              if row["status"] == "publisher_final" and not row.get("fixture_review")}
    exclusions["frozen_fixtures_absent_from_snapshot"] = len(
        forecasts.keys() - {_key(row["fixture"]) for row in rows}
    )
    keys = [(game.league, game.event_id) for game in games]
    predictions = [forecasts[key][2]["prediction"] for key in keys]
    results = [finals[key]["result"] for key in keys]
    scores = [(final["actual_home"], final["actual_away"]) for final in results]
    market_outcomes = {"over_2_5": [home + away > 2.5 for home, away in scores],
                       "btts": [min(home, away) > 0 for home, away in scores]}
    markets = {field: _binary_market(games, [_market_probability(p, field) for p in predictions],
                                     market_outcomes[field]) for field in MARKETS}
    return {
        "spec": "football-calibration-report-v1",
        "cutoff_utc": cutoff.isoformat() if cutoff is not None else None,
        "n": len(games), "exclusions": exclusions,
        "protocol": {"minimum_prior_games": MIN_PRIOR, "minimum_evaluation_games": MIN_EVALUATION,
                     "temperature_grid": list(temperatures), "bootstrap_seed": SEED,
                     "bootstrap_replicates": REPLICATES,
                     "availability": "Scorecard known_at, the saved daily report check time. "
                                     "Require known_at < frozen_at.",
                     "binary_baseline": "A constant-rate prediction for each game, set before freeze "
                                        "from the per-league expanding rate with one prior count per outcome.",
                     "improvement_sign": "Positive favors the candidate.",
                     "verdict_rule": (
                         f"A verdict requires at least {MIN_EVALUATION} comparable games, counting only "
                         "games with a fitted temperature toward the 1X2 minimum. A smaller sample or "
                         f"an unavailable interval yields `{INCONCLUSIVE}`. A strictly positive lower "
                         "95% bound on mean log-loss improvement yields "
                         f"`{SKILL_VERDICTS[0]}` for goal markets and `{RECALIBRATION_VERDICTS[0]}` for 1X2. "
                         f"A lower bound at or below zero yields `{SKILL_VERDICTS[1]}` for goal markets "
                         f"and `{RECALIBRATION_VERDICTS[1]}` for 1X2."
                     ),
                     "multiple_comparisons": (
                         f"The three verdicts use the same {len(games)}-game cohort without any "
                         "adjustment for multiple comparisons, so a borderline confidence interval "
                         "(for example, a lower bound within 0.005 of zero) is weak evidence at most."
                     )},
        "one_x_two": {"reliability": reliability, "top_pick_bins": top_pick,
                      "reliability_scope": RELIABILITY_SCOPE,
                      "temperature": comparison},
        "markets": markets,
    }


def _format(value, percent=False):
    if value is None:
        return "—"
    return f"{value:.1%}" if percent else f"{value:.4f}"


def _estimate(value, ci, percent=False):
    result = _format(value, percent)
    if ci is not None:
        result += f" [{_format(ci[0], percent)}, {_format(ci[1], percent)}]"
    return result


def _comparison_table(comparison, names, labels):
    lines = [f"| Forecast | n | {labels[2]} (95% CI) | Log loss (95% CI) | Brier (95% CI) |",
             "|---|---:|---:|---:|---:|"]
    for key, label in zip(("reference", "candidate", "improvement"),
                          (*labels[:2], "Paired improvement")):
        summary = comparison[key]
        cells = [_estimate(summary[name], summary["ci95"][name], i == 0)
                 for i, name in enumerate(names)]
        lines.append(f"| {label} | {comparison['n']} | {' | '.join(cells)} |")
    return lines


def _bin_table(bins):
    lines = ["| Probability bin | n | Mean forecast | Observed frequency |",
             "|---|---:|---:|---:|"]
    for row in bins:
        lines.append(f"| {row['lower']:.0%}–{row['upper']:.0%} | {row['n']} | "
                     f"{_format(row['forecast_mean'], True)} | "
                     f"{_format(row['observed_frequency'], True)} |")
    return lines


def markdown(report):
    """Render the report with comparison, reliability and exclusion details."""
    exclusions = report["exclusions"]
    other = exclusions["other_nonfinal_by_status"]
    nonfinal = ", ".join(f"{count} {status}" for status, count in other.items())
    kickoff = ", ".join(f"{league} {count}"
                        for league, count in exclusions["missing_kickoff_by_league"].items())
    one_x_two = report["one_x_two"]
    comparison = one_x_two["temperature"]
    protocol = report["protocol"]
    lines = [
        "# Football live calibration report", "",
        f"Ledger cutoff (UTC) **{report['cutoff_utc'] or 'unavailable'}**.",
        f"Scored **{report['n']}** checksum-verified frozen forecasts joined to community publisher "
        "finals under the live scorecard rules.", "",
        f"Excluded **{exclusions['total_snapshot_rows_excluded']}** snapshot rows. "
        f"{exclusions['publisher_finals_without_verified_kickoff']} publisher finals lacked a verified "
        f"kickoff and {exclusions['fixture_review']} rows required fixture review. "
        f"Other nonfinal rows **{sum(other.values())}**" + (f" ({nonfinal})." if other else "."),
        f"Frozen fixtures absent from the snapshot **{exclusions['frozen_fixtures_absent_from_snapshot']}**.",
    ]
    if kickoff:
        lines.append(f"Missing verified kickoffs by league ({kickoff}).")
    lines += ["", "## 1X2 walk-forward temperature", ""]
    if comparison["walk_forward_ran"]:
        lines += [f"Temperature fitting was available for **{comparison['fitted_n']}** games. "
                  f"**{comparison['fallback_n']}** games used the original forecasts under the minimum-prior rule.", ""]
    else:
        lines += [comparison["walk_forward_limitation"], ""]
    lines += [
        f"**Verdict — {comparison['recalibration_verdict']}**", "",
        "The grid is " + ", ".join(f"{t:g}" for t in protocol["temperature_grid"]) + ".",
        f"Each fit minimizes multiclass log loss using at least {protocol['minimum_prior_games']} "
        "eligible finals recorded strictly "
        "before the forecast freeze. Ties prefer the temperature closest to 1, then the lower temperature.",
        "The scorecard uses the saved daily report check time for when each final became known. "
        "Kickoff and match date do not establish when scores were available.", "",
    ]
    candidate_label = "Walk-forward" if comparison["walk_forward_ran"] else "Unscaled fallback"
    lines += _comparison_table(comparison, METRICS, ("Unscaled", candidate_label, "Accuracy"))
    lines += [
        "", "## 1X2 reliability", "",
        one_x_two["reliability_scope"],
        "Each class is fitted against the other two using an unpenalized logistic intercept and slope "
        "on the class forecast log-odds. Perfect calibration corresponds to intercept 0 and slope 1. "
        "A slope above 1 indicates too little spread on the log-odds scale.",
        "Bins include the lower edge and exclude the upper edge, with 100% in the final bin. "
        "Logistic intervals require finite fits on at least 95% of bootstrap draws.", "",
        "### Top pick", "",
    ]
    lines += _bin_table(one_x_two["top_pick_bins"])
    for label, reliability in one_x_two["reliability"].items():
        fit = reliability["logistic"]
        lines += ["", f"### {label.capitalize()} vs rest", "",
                  f"Intercept **{_estimate(fit['intercept'], fit['ci95']['intercept'])}**. "
                  f"Slope **{_estimate(fit['slope'], fit['ci95']['slope'])}**. "
                  f"Finite bootstrap fits **{fit['valid_bootstrap_fits']:,}**.", ""]
        lines += _bin_table(reliability["bins"])
    lines += [
        "", "## Goal markets", "",
        "These verdicts measure the frozen model's skill against a constant-rate baseline known before "
        "each game. Both forecasts are scored on games with the frozen probability and both final scores. "
        "The baseline uses the expanding league event rate from scorecard-eligible finals known strictly "
        "before freeze, with one prior count for each outcome (50% at cold start). "
        "The hit-rate threshold is 50%, with ties predicting yes. Binary Brier uses the squared "
        "error of the yes probability.", "",
    ]
    for field, label in MARKETS.items():
        market = report["markets"][field]
        lines += [f"### {label}", "", f"**Verdict — {market['skill_verdict']}**", "",
                  f"Missing frozen market probabilities **{market['missing_probability']}**. "
                  f"Mean baseline probability **{_format(market['baseline_mean_probability'], True)}**.", ""]
        lines += _comparison_table(market, ("hit_rate", "log_loss", "brier"),
                                   ("Pre-freeze rate", "Frozen forecast", "Hit rate"))
        lines.append("")
    lines += [
        "## Confidence intervals and verdicts", "",
        f"Percentile intervals use {REPLICATES:,} game resamples with replacement and seed {SEED}. "
        "Paired intervals resample each forecast and its comparator together, conditional on the "
        "chronological predictions already made. Positive improvement favors the candidate. "
        "Multiclass Brier sums squared errors across home, draw and away.", "",
        protocol["verdict_rule"], "",
        protocol["multiple_comparisons"], "",
    ]
    return "\n".join(lines)
