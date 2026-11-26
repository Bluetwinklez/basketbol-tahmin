"""Compare the fixed opponent-strength model on the later 2026-27 archive."""
import argparse
import hashlib
import json
from pathlib import Path

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.football.data import load
from bbtahmin.prior_policy import calibrated
from scripts.evaluate_football_draw import LEAGUES
from scripts.evaluate_improvement_football import season_predictions

BASE_VARIANTS = ("baseline", "opponent")
TARGET = "2026-27"
REGISTRY = Path("data/improvement_policy/current.json")


def replay_policy(rows, policy, target):
    selected = [r for r in rows if r["variant"] == policy["variant"]]
    if (not selected
            or int(target[:4]) - int(policy["prior_season"][:4]) != 1
            or any(r["season"] != target or r["day"] <= policy["last_prior_day"] for r in selected)):
        raise ValueError("Frozen policy must precede every target fixture")
    probabilities = calibrated([r["p"] for r in selected], policy["temperature"])
    return [
        dict(row, variant="frozen_policy", p=p.tolist())
        for row, p in zip(selected, probabilities, strict=True)
    ]


def summarize(rows):
    result = {name: {} for name in ("baseline", "opponent", "frozen_policy")}
    for name in result:
        subset = [r for r in rows if r["variant"] == name]
        eligible = [r["data_gate_passed"] and max(r["p"]) >= .65 for r in subset]
        result[name] = metrics([r["y"] for r in subset], [r["p"] for r in subset], eligible)
    for name in ("opponent", "frozen_policy"):
        result[name]["vs_baseline"] = paired(rows, "baseline", name, replicates=2000)
    result["opponent"]["vs_frozen_policy"] = paired(rows, "frozen_policy", "opponent", replicates=2000)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    registry = REGISTRY.read_bytes()
    policies = json.loads(registry)['policies']['football']
    frame = load()
    pooled = []
    leagues = {}
    for league in LEAGUES:
        policy = policies[league]
        fit_variants = tuple(dict.fromkeys((*BASE_VARIANTS, policy["variant"])))
        rows, skipped = season_predictions(frame, league, TARGET, variants=fit_variants)
        compared = [r for r in rows if r["variant"] in BASE_VARIANTS]
        compared.extend(replay_policy(rows, policy, TARGET))
        leagues[league] = {
            "variant": policy["variant"], "temperature": policy["temperature"],
            "results": summarize(compared), "skipped": skipped,
        }
        pooled.extend(compared)
    days = sorted({row["day"] for row in pooled})
    boundary = days[len(days) // 2]
    report = {
        "evidence_kind": "exploratory_retrospective",
        "target_season": TARGET,
        "registry_sha256": hashlib.sha256(registry).hexdigest(),
        "first_target_day": min(row["day"] for row in pooled),
        "last_target_day": max(row["day"] for row in pooled),
        "leagues": leagues,
        "pooled": summarize(pooled),
        "later_starts": boundary,
        "earlier": summarize([r for r in pooled if r["day"] < boundary]),
        "later": summarize([r for r in pooled if r["day"] >= boundary]),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
