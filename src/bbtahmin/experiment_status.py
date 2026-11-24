"""Describe frozen paired experiments from the persisted settlement snapshot."""

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import NormalDist

from .experiment_metrics import losses, paired
from .shadow import checked

MINIMUM_GAMES = 1000
CONFIDENCE_LEVEL = 0.95
MARGIN = 0.02
Z = NormalDist().inv_cdf((1 + CONFIDENCE_LEVEL) / 2)


def closing_rule(minimum_games):
    return (
        f"Each league needs at least {minimum_games} settled paired games. Below that "
        "threshold the verdict is insufficient_sample. At or above it, the existing "
        "95% paired day-block bootstrap interval determines the verdict: a lower bound "
        "above zero gives concluded_better; an upper bound below zero gives "
        "concluded_worse. Otherwise an interval entirely within [-0.02, +0.02] gives "
        "concluded_no_difference; any remaining interval gives inconclusive. Directional "
        "verdicts take precedence if both rules apply. An experiment inherits a unanimous "
        "league verdict; any insufficient league makes it insufficient_sample, and "
        "other disagreements are inconclusive."
    )


PRECISION_RULE = (
    "Precision planning uses q = (candidate-only correct + reference-only correct) / n. "
    "The conservative independent-pair normal 95% half-width is z × sqrt(q / n), "
    "using q as an upper bound on the variance of the paired correctness difference. "
    "At the same observed q, n for a half-width of at most 0.02 is "
    "ceil(z² × q / 0.02²). Games still needed is the larger of the league minimum "
    "and that precision target, minus n, floored at zero. With zero settled pairs, "
    "precision is unavailable and games still needed reflects the minimum alone."
)


def _read(path):
    return json.loads(path.read_text(encoding="utf8"))


def _league_status(frozen, rows, minimum_games):
    accuracy_delta = interval = log_loss_delta = None
    candidate_only = reference_only = 0
    fraction = half_width = precision_n = None
    n = 0
    if rows:
        comparison = paired(rows, "reference", "candidate")
        n = comparison["games"]
        accuracy = comparison["changes"]["accuracy"]
        accuracy_delta = accuracy["delta"]
        interval = accuracy["day_block_95_interval"]
        log_loss_delta = comparison["changes"]["log_loss"]["delta"]
        correct = {}
        for variant in ("reference", "candidate"):
            group = sorted(
                (row for row in rows if row["variant"] == variant),
                key=lambda row: row["event_id"],
            )
            correct[variant] = losses(
                [row["y"] for row in group], [row["p"] for row in group]
            )[:, 0].astype(bool)
        candidate_only = int((correct["candidate"] & ~correct["reference"]).sum())
        reference_only = int((correct["reference"] & ~correct["candidate"]).sum())
        fraction = (candidate_only + reference_only) / n
        half_width = Z * math.sqrt(fraction / n)
        precision_n = math.ceil(Z**2 * fraction / MARGIN**2)

    if n < minimum_games:
        verdict = "insufficient_sample"
    elif interval[0] > 0:
        verdict = "concluded_better"
    elif interval[1] < 0:
        verdict = "concluded_worse"
    elif -MARGIN <= interval[0] <= interval[1] <= MARGIN:
        verdict = "concluded_no_difference"
    else:
        verdict = "inconclusive"

    return dict(
        frozen_pairs=frozen, settled_pairs=n, accuracy_delta=accuracy_delta,
        accuracy_day_block_95_interval=interval, log_loss_delta=log_loss_delta,
        verdict=verdict, candidate_only_correct=candidate_only,
        reference_only_correct=reference_only, discordant_fraction=fraction,
        precision_95_half_width=half_width, n_for_target_half_width=precision_n,
        n_still_needed=max(0, minimum_games - n, (precision_n or 0) - n),
    )


def _experiment_status(directory, current, settlement, minimum_games):
    identity = directory.name
    protocol = checked(_read(directory / "protocol.json"))
    if protocol["sha256"] != identity:
        raise ValueError(f"Protocol identity mismatch for {identity}")
    counts = Counter()
    frozen = {}
    for path in sorted((directory / "forecasts").glob("*.json")):
        record = checked(_read(path))
        if record["experiment_id"] != identity:
            raise ValueError(f"Forecast belongs to another experiment: {path}")
        fixture = record["fixture"]
        counts[fixture["league"]] += 1
        frozen[record["sha256"]] = fixture["league"], fixture["event_id"]

    by_league = defaultdict(list)
    for row in settlement.get("rows", []):
        if frozen.get(row["record_sha256"]) != (row["league"], row["event_id"]):
            raise ValueError(f"Settlement does not match a frozen forecast for {identity}")
        by_league[row["league"]].append(row)
    leagues = {
        league: _league_status(counts[league], by_league[league], minimum_games)
        for league in sorted(counts)
    }
    settled = sum(league["settled_pairs"] for league in leagues.values())
    if settled != settlement.get("settled_games", 0):
        raise ValueError(f"Settlement pair count mismatch for {identity}")
    verdicts = {league["verdict"] for league in leagues.values()}
    if not verdicts or "insufficient_sample" in verdicts:
        verdict = "insufficient_sample"
    elif len(verdicts) == 1:
        verdict = verdicts.pop()
    else:
        verdict = "inconclusive"
    return dict(
        experiment_id=identity, short_id=identity[:12],
        status="active" if identity == current else "superseded",
        frozen_pairs=sum(counts.values()), settled_pairs=settled,
        settlement_report_available=bool(settlement), verdict=verdict, leagues=leagues,
    )


def build_report(root, minimum_games=MINIMUM_GAMES):
    """Use active.json first and latest.json as the pointer fallback and settlement source."""
    if type(minimum_games) is not int or minimum_games < 1:
        raise ValueError("Minimum settled games must be a positive integer")
    root = Path(root)
    latest_path = root / "latest.json"
    latest = _read(latest_path) if latest_path.exists() else {}
    active_path = root / "active.json"
    pointer = _read(active_path) if active_path.exists() else latest
    current = pointer.get("experiment_id")
    directories = sorted(p for p in (root / "experiments").iterdir() if p.is_dir())
    if directories and current not in {p.name for p in directories}:
        raise ValueError("Active pointer must identify an existing experiment")
    settlements = {entry["experiment_id"]: entry for entry in latest.get("experiments", [])}
    return dict(
        spec="paired-forward-status-v1", active_experiment_id=current,
        settlement_checked_at_utc=latest.get("checked_at_utc"),
        thresholds=dict(minimum_settled_pairs_per_league=minimum_games,
                        confidence_level=CONFIDENCE_LEVEL, normal_z=Z,
                        target_half_width=MARGIN, no_difference_margin=MARGIN),
        closing_rule=closing_rule(minimum_games), precision_rule=PRECISION_RULE,
        experiments=[
            _experiment_status(p, current, settlements.get(p.name, {}), minimum_games)
            for p in directories
        ],
    )
