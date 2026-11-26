"""Compare the fixed opponent-strength model on the later 2026-27 archive."""
import argparse
import json
from pathlib import Path

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.football.data import load
from scripts.evaluate_football_draw import LEAGUES
from scripts.evaluate_improvement_football import season_predictions

VARIANTS = ("baseline", "opponent")


def summarize(rows):
    report = paired(rows, *VARIANTS, replicates=2000)
    for variant in VARIANTS:
        subset = [row for row in rows if row["variant"] == variant]
        report[variant] = metrics([r["y"] for r in subset], [r["p"] for r in subset])["all"]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    frame = load()
    pooled = []
    leagues = {}
    for league in LEAGUES:
        rows, skipped = season_predictions(frame, league, "2026-27", variants=VARIANTS)
        leagues[league] = dict(summarize(rows), skipped=skipped)
        pooled.extend(rows)
    report = {
        "evidence_kind": "exploratory_retrospective",
        "target_season": "2026-27",
        "first_target_day": min(row["day"] for row in pooled),
        "last_target_day": max(row["day"] for row in pooled),
        "leagues": leagues,
        "pooled": summarize(pooled),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
