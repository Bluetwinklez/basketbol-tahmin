"""Evaluate a prior-only draw-odds correction on historical football seasons."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from bbtahmin.experiment_metrics import losses, metrics, paired, validate
from bbtahmin.football.data import ROOT, load
from scripts.evaluate_improvement_football import season_predictions, temperature, TEMPERATURES

LEAGUES = ("EN1", "EN2", "DE1", "ES1", "IT1", "FR1", "NL1", "PT1", "TR1")
DRAW_MULTIPLIERS = (0.8, 0.9, 1.0, 1.1, 1.25, 1.4)
BALANCED_GAP = 0.15
LOW_GOAL_TOTAL = 2.5
CLOSE_RIDGE = 0.01
VARIANTS = ("baseline", "temperature", "draw_only", "close_draw", "gated_draw", "gated_close", "goal_context", "gated_goal_context")


def draw_adjust(probabilities, multiplier):
    adjusted = np.asarray(probabilities, dtype=float).copy()
    if not np.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("Draw multiplier must be finite and positive")
    adjusted[:, 1] *= multiplier
    return adjusted / adjusted.sum(axis=1, keepdims=True)


def win_gap(probabilities):
    return np.abs(probabilities[:, 0] - probabilities[:, 2])


def close_design(probabilities, totals=None):
    gap = win_gap(probabilities)
    columns = [np.ones(len(gap)), 0.5 - gap]
    if totals is not None:
        totals = np.asarray(totals, dtype=float)
        if totals.shape != gap.shape or not np.isfinite(totals).all() or (totals <= 0).any():
            raise ValueError("Each fixture requires a finite positive expected goal total")
        columns.append(np.log(totals / LOW_GOAL_TOTAL))
    return np.column_stack(columns)


def fit_close_draw(y, probabilities, totals=None):
    """Fit a regularized draw log-odds offset, preserving home/away odds."""
    design = close_design(probabilities, totals)
    offset = logit(np.clip(probabilities[:, 1], 1e-12, 1 - 1e-12))
    is_draw = (y == 1).astype(float)

    def objective(coef):
        logits = offset + design @ coef
        value = np.mean(np.logaddexp(0, logits) - is_draw * logits)
        value += 0.5 * CLOSE_RIDGE * (coef @ coef)
        gradient = design.T @ (expit(logits) - is_draw) / len(y) + CLOSE_RIDGE * coef
        return value, gradient

    fitted = minimize(objective, np.zeros(design.shape[1]), jac=True, method="BFGS")
    if not fitted.success or not np.isfinite(fitted.x).all():
        raise RuntimeError(f"Draw calibration did not converge: {fitted.message}")
    return fitted.x


def adjust_close_draw(probabilities, coefficients, totals=None):
    adjusted = probabilities.copy()
    adjusted[:, 1] *= np.exp(close_design(probabilities, totals) @ coefficients)
    return adjusted / adjusted.sum(axis=1, keepdims=True)


def passes_gate(candidate, references):
    return all(
        candidate["accuracy"] >= reference["accuracy"]
        and candidate["log_loss"] <= reference["log_loss"] - 0.002
        and candidate["brier"] <= reference["brier"]
        for reference in references
    )


def cohort(rows):
    if len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate fixture in draw calibration cohort")
    y, p = validate([row["y"] for row in rows], [row["p"] for row in rows])
    if p.shape[1] != 3:
        raise ValueError("Draw calibration requires home, draw and away probabilities")
    return y, p


def goal_totals(rows):
    return np.asarray([row["expected_total_goals"] for row in rows], dtype=float)


def evaluate(prior, target):
    if not prior or not target or max(r["day"] for r in prior) >= min(r["day"] for r in target):
        raise ValueError("Nonempty, strictly ordered development and target periods required")
    if {r["event_id"] for r in prior} & {r["event_id"] for r in target}:
        raise ValueError("Fixture reused across development and target")
    cohort(prior)
    y_target, p_target = cohort(target)
    days = sorted({r["day"] for r in prior})
    boundary = days[len(days) // 2]
    fit = [r for r in prior if r["day"] < boundary]
    check = [r for r in prior if r["day"] >= boundary]
    if min(len(fit), len(check)) < 30:
        raise ValueError("Need at least 30 fixtures in each development half")

    y_fit, p_fit = cohort(fit)
    y_check, p_check = cohort(check)
    fitted_temperature = min(
        TEMPERATURES,
        key=lambda t: (losses(y_fit, temperature(p_fit, t))[:, 1].mean(), abs(t - 1)),
    )
    fitted_multiplier = min(
        DRAW_MULTIPLIERS,
        key=lambda m: (losses(y_fit, draw_adjust(p_fit, m))[:, 1].mean(), abs(m - 1)),
    )
    close_coefficients = fit_close_draw(y_fit, p_fit)
    context_coefficients = fit_close_draw(y_fit, p_fit, goal_totals(fit))
    check_probs = {
        "baseline": p_check,
        "temperature": temperature(p_check, fitted_temperature),
        "draw_only": draw_adjust(p_check, fitted_multiplier),
        "close_draw": adjust_close_draw(p_check, close_coefficients),
        "goal_context": adjust_close_draw(p_check, context_coefficients, goal_totals(check)),
    }
    validation_groups = {
        name: context_groups(y_check, probs, win_gap(p_check) <= BALANCED_GAP, goal_totals(check))
        for name, probs in check_probs.items()
    }
    validation = {name: metrics(y_check, p)["all"] for name, p in check_probs.items()}
    draw, raw, scaled = (validation[name] for name in ("draw_only", "baseline", "temperature"))
    use_draw = passes_gate(draw, (raw, scaled))
    use_close = passes_gate(validation["close_draw"], (raw, scaled, draw))
    use_context = passes_gate(validation["goal_context"], (raw, scaled, draw, validation["close_draw"]))
    target_totals = goal_totals(target)
    context_target = adjust_close_draw(p_target, context_coefficients, target_totals)
    close_target = adjust_close_draw(p_target, close_coefficients)

    probabilities = {
        "baseline": p_target,
        "temperature": temperature(p_target, fitted_temperature),
        "draw_only": draw_adjust(p_target, fitted_multiplier),
        "close_draw": close_target,
        "goal_context": context_target,
        "gated_goal_context": context_target if use_context else p_target,
        "gated_close": close_target if use_close else p_target,
        "gated_draw": draw_adjust(p_target, fitted_multiplier) if use_draw else p_target,
    }
    scored = [
        {"event_id": row["event_id"], "day": row["day"], "y": row["y"],
         "variant": name, "p": p.tolist(), "data_gate_passed": row["data_gate_passed"],
         "expected_total_goals": row["expected_total_goals"]}
        for name, values in probabilities.items()
        for row, p in zip(target, values, strict=True)
    ]
    return {
        "fit_games": len(fit),
        "check_games": len(check),
        "check_starts": boundary,
        "temperature": fitted_temperature,
        "draw_multiplier": fitted_multiplier,
        "selected_draw": use_draw,
        "close_coefficients": close_coefficients.tolist(),
        "selected_close": use_close,
        "context_coefficients": context_coefficients.tolist(),
        "selected_goal_context": use_context,
        "validation": validation,
        "validation_context_groups": validation_groups,
        "target": summarize(scored),
    }, scored


def context_groups(y, probabilities, balanced, totals):
    low = totals < LOW_GOAL_TOTAL
    report = {}
    for balance_name, balance_mask in (("balanced", balanced), ("other", ~balanced)):
        for goal_name, goal_mask in (("low", low), ("higher", ~low)):
            keep = balance_mask & goal_mask
            sample_y, sample_p = y[keep], probabilities[keep]
            stats = metrics(sample_y, sample_p)["all"]
            if stats["games"]:
                stats["mean_draw_probability"] = float(sample_p[:, 1].mean())
                stats["observed_draw_rate"] = float((sample_y == 1).mean())
                stats["draw_brier"] = float(np.mean((sample_p[:, 1] - (sample_y == 1)) ** 2))
            report[f"{balance_name}_{goal_name}"] = stats
    return report


def summarize(rows):
    result = {}
    balanced_ids = {
        row["event_id"] for row in rows
        if row["variant"] == "baseline" and abs(row["p"][0] - row["p"][2]) <= BALANCED_GAP
    }
    for name in VARIANTS:
        items = [r for r in rows if r["variant"] == name]
        y, p = cohort(items)
        selected = [r["data_gate_passed"] and max(r["p"]) >= 0.65 for r in items]
        summary = metrics(y, p, selected)
        confusion = summary["confusion_actual_by_predicted"]
        summary["draw_counts"] = {
            "actual": sum(confusion[1]),
            "predicted": sum(r[1] for r in confusion),
            "correct": confusion[1][1],
        }
        balanced = np.array([row["event_id"] in balanced_ids for row in items])
        summary["by_baseline_gap"] = {
            group: metrics(y[keep], p[keep])["all"]
            for group, keep in (("balanced", balanced), ("other", ~balanced))
        }
        summary["context_groups"] = context_groups(y, p, balanced, goal_totals(items))
        if name != "baseline":
            summary["vs_baseline"] = paired(rows, "baseline", name)
        if name in ("draw_only", "close_draw"):
            summary["vs_temperature"] = paired(rows, "temperature", name)
        if name == "close_draw":
            summary["vs_global_draw"] = paired(rows, "draw_only", name)
        if name == "goal_context":
            summary["vs_close_draw"] = paired(rows, "close_draw", name)
        result[name] = summary
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--development", default="2024-25")
    parser.add_argument("--target", default="2025-26")
    args = parser.parse_args()
    input_hashes = {
        path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted([*ROOT.glob("*_20*.json.gz"), *(ROOT / "licensed_overlays").glob("*.json.gz")])
    }
    frame = load()
    results = {}
    pooled = []
    for league in LEAGUES:
        prior, prior_skipped = season_predictions(frame, league, args.development, variants=("baseline",))
        target, target_skipped = season_predictions(frame, league, args.target, variants=("baseline",))
        result, scored = evaluate(prior, target)
        result.update(prior_skipped=prior_skipped, target_skipped=target_skipped)
        results[league] = result
        pooled.extend(scored)
    report = {
        "evidence_kind": "exploratory_retrospective",
        "development_season": args.development,
        "target_season": args.target,
        "draw_multipliers": DRAW_MULTIPLIERS,
        "temperatures": TEMPERATURES,
        "close_ridge": CLOSE_RIDGE,
        "balanced_win_gap": BALANCED_GAP,
        "low_goal_total": LOW_GOAL_TOTAL,
        "input_sha256": input_hashes,
        "leagues": results,
        "pooled": summarize(pooled),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
