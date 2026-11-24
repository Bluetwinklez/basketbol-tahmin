"""Write a read-only experiment status report from local shadow records."""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from bbtahmin.experiment_status import MINIMUM_GAMES, build_report


def _number(value):
    return "—" if value is None else f"{value:.6f}"


def render_markdown(report):
    thresholds = report["thresholds"]
    lines = [
        "# Paired forward experiment status",
        "",
        "Lifecycle follows `active.json`, with `latest.json` as the pointer fallback. "
        "Settled pairs come from the latest saved settlement snapshot. "
        "Metrics are candidate minus reference and stay within their experiment and league.",
        "",
        report["closing_rule"],
        "",
        report["precision_rule"],
        "",
        f"Confidence level **{thresholds['confidence_level']:.0%}**, "
        f"normal z **{thresholds['normal_z']:.17g}**, "
        f"target half-width **{thresholds['target_half_width']}**, "
        f"no-difference margin **±{thresholds['no_difference_margin']}**.",
        "",
        f"Settlement snapshot UTC **{report['settlement_checked_at_utc'] or 'unavailable'}**.",
        "",
        "| ID | Status | Frozen | Settled | Verdict | League evidence |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for experiment in report["experiments"]:
        details = []
        if not experiment["settlement_report_available"]:
            details.append("Settlement snapshot unavailable for this identity.")
        for code, league in experiment["leagues"].items():
            interval = league["accuracy_day_block_95_interval"]
            ci = f"[{_number(interval[0])}, {_number(interval[1])}]" if interval else "—"
            precision_n = league["n_for_target_half_width"]
            precision_target = "—" if precision_n is None else str(precision_n)
            details.append(
                f"**{code}** · n {league['settled_pairs']}/{league['frozen_pairs']} · "
                f"Δ accuracy {_number(league['accuracy_delta'])} (95% CI {ci}) · "
                f"Δ log loss {_number(league['log_loss_delta'])} · `{league['verdict']}` · "
                f"discordant C/R {league['candidate_only_correct']}/{league['reference_only_correct']} "
                f"(q {_number(league['discordant_fraction'])}) · "
                f"95% planning half-width {_number(league['precision_95_half_width'])} · "
                f"precision n {precision_target} · still needed {league['n_still_needed']}"
            )
        evidence = "<br>".join(details) or "—"
        lines.append(
            f"| `{experiment['short_id']}` | {experiment['status']} | "
            f"{experiment['frozen_pairs']} | {experiment['settled_pairs']} | "
            f"`{experiment['verdict']}` | {evidence} |"
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO / "data" / "improvement_shadow")
    parser.add_argument("--output", type=Path, default=REPO / "docs" / "kanit" / "experiment_status")
    parser.add_argument("--minimum-games", type=int, default=MINIMUM_GAMES)
    args = parser.parse_args()

    json_path = args.output / "status.json"
    md_path = args.output / "status.md"
    protected = (args.root.resolve(), (REPO / "data" / "improvement_shadow").resolve())
    if any(path.resolve().is_relative_to(root)
           for path in (args.output, json_path, md_path) for root in protected):
        parser.error("Report output must be outside the shadow data directory")
    report = build_report(args.root, args.minimum_games)
    args.output.mkdir(parents=True, exist_ok=True)
    json_path.write_bytes((json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf8"))
    md_path.write_bytes(render_markdown(report).encode("utf8"))


if __name__ == "__main__":
    main()
