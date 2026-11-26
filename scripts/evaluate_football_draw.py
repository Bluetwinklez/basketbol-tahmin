"""Evaluate a prior-only draw-odds correction on historical football seasons."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from bbtahmin.experiment_metrics import losses, metrics, paired, validate
from bbtahmin.football.data import ROOT, load
from scripts.evaluate_improvement_football import season_predictions, temperature, TEMPERATURES

LEAGUES = ("EN1", "EN2", "DE1", "ES1", "IT1", "FR1", "NL1", "PT1", "TR1")
DRAW_MULTIPLIERS = (0.8, 0.9, 1.0, 1.1, 1.25, 1.4)


def draw_adjust(probabilities, multiplier):
    adjusted = np.asarray(probabilities, dtype=float).copy()
    if not np.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("Draw multiplier must be finite and positive")
    adjusted[:, 1] *= multiplier
    return adjusted / adjusted.sum(axis=1, keepdims=True)


def cohort(rows):
    if len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate fixture in draw calibration cohort")
    y, p = validate([row["y"] for row in rows], [row["p"] for row in rows])
    if p.shape[1] != 3:
        raise ValueError("Draw calibration requires home, draw and away probabilities")
    return y, p


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
    check_probs = {
        "baseline": p_check,
        "temperature": temperature(p_check, fitted_temperature),
        "draw_only": draw_adjust(p_check, fitted_multiplier),
    }
    validation = {name: metrics(y_check, p)["all"] for name, p in check_probs.items()}
    draw, raw, scaled = (validation[name] for name in ("draw_only", "baseline", "temperature"))
    use_draw = all(
        draw["accuracy"] >= ref["accuracy"]
        and draw["log_loss"] <= ref["log_loss"] - 0.002
        and draw["brier"] <= ref["brier"]
        for ref in (raw, scaled)
    )

    probabilities = {
        "baseline": p_target,
        "temperature": temperature(p_target, fitted_temperature),
        "draw_only": draw_adjust(p_target, fitted_multiplier),
        "gated_draw": draw_adjust(p_target, fitted_multiplier) if use_draw else p_target,
    }
    scored = [
        {"event_id": row["event_id"], "day": row["day"], "y": row["y"],
         "variant": name, "p": p.tolist(), "data_gate_passed": row["data_gate_passed"]}
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
        "validation": validation,
        "target": summarize(scored),
    }, scored


def summarize(rows):
    result = {}
    for name in ("baseline", "temperature", "draw_only", "gated_draw"):
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
        if name != "baseline":
            summary["vs_baseline"] = paired(rows, "baseline", name)
        if name == "draw_only":
            summary["vs_temperature"] = paired(rows, "temperature", name)
        result[name] = summary
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    input_hashes = {
        path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted([*ROOT.glob("*_20*.json.gz"), *(ROOT / "licensed_overlays").glob("*.json.gz")])
    }
    frame = load()
    results = {}
    pooled = []
    for league in LEAGUES:
        prior, prior_skipped = season_predictions(frame, league, "2024-25", variants=("baseline",))
        target, target_skipped = season_predictions(frame, league, "2025-26", variants=("baseline",))
        result, scored = evaluate(prior, target)
        result.update(prior_skipped=prior_skipped, target_skipped=target_skipped)
        results[league] = result
        pooled.extend(scored)
    report = {
        "evidence_kind": "exploratory_retrospective",
        "development_season": "2024-25",
        "target_season": "2025-26",
        "draw_multipliers": DRAW_MULTIPLIERS,
        "temperatures": TEMPERATURES,
        "input_sha256": input_hashes,
        "leagues": results,
        "pooled": summarize(pooled),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
