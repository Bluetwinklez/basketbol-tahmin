import json

import numpy as np
import pandas as pd
import pytest

from bbtahmin.experiment_metrics import losses
from bbtahmin.football.daily import digest
from bbtahmin.football_calibration_report import (
    RECALIBRATION_VERDICTS, SKILL_VERDICTS, verdict, walk_forward,
)
from bbtahmin.live_scorecard import Game
from scripts.evaluate_improvement_football import TEMPERATURES, temperature
from scripts.football_calibration_report import run


GRID = (.5, .6, *TEMPERATURES)
P = (.6, .2, .2)


def day(n):
    return pd.Timestamp(2026, 11, n, tz="UTC")


def game(event_id, freeze, settled, outcome):
    return Game("EN1", str(event_id), day(freeze), day(settled), outcome, P, None)


def test_walk_forward_excludes_equal_time_target_and_later_finals():
    history = [game(i, 1, 2, 0) for i in range(30)]
    # Frozen before the target, but first known at or after its freeze.
    unavailable = [game(f"late-{i}", 2, 3 + i % 2, 2) for i in range(50)]
    target = game("target", 3, 4, 2)
    later = game("later", 5, 6, 0)
    games = [later, target, *unavailable, *history]
    scaled, audit = walk_forward(games, GRID, temperature)

    outcomes = [g.outcome for g in [*history, *unavailable, target]]
    all_known_choice = min(GRID, key=lambda t: losses(
        outcomes, temperature([P] * len(outcomes), t)
    )[:, 1].mean())
    assert all_known_choice == 2
    assert audit[1]["prior_n"] == 30
    assert audit[1]["temperature"] == .5
    assert scaled[1] == pytest.approx(temperature(P, .5))
    assert audit[0]["prior_n"] == len(outcomes)
    assert audit[0]["temperature"] == all_known_choice


def test_minimum_counts_only_finals_strictly_before_freeze():
    history = [game(i, 1, 2, 0) for i in range(29)]
    history.append(game("settles-at-freeze", 1, 3, 0))
    target = game("target", 3, 4, 0)
    scaled, audit = walk_forward([target, *history], GRID, temperature)
    assert audit[0]["prior_n"] == 29
    assert audit[0]["temperature"] is None
    assert np.array_equal(scaled[0], P)


@pytest.mark.parametrize(("n", "ci", "expected_skill", "expected_recalibration"), [
    (29, [.1, .2], "inconclusive (n too small)", "inconclusive (n too small)"),
    (30, None, "inconclusive (n too small)", "inconclusive (n too small)"),
    (30, [.0014, .02], "skill_over_baseline", "supports recalibration"),
    (30, [-.01, .02], "no_skill_over_baseline", "does not support recalibration"),
    (30, [0, .02], "no_skill_over_baseline", "does not support recalibration"),
    (30, [-.02, -.01], "no_skill_over_baseline", "does not support recalibration"),
])
def test_verdict_rules(n, ci, expected_skill, expected_recalibration):
    assert verdict(n, ci, labels=SKILL_VERDICTS) == expected_skill
    assert verdict(n, ci, labels=RECALIBRATION_VERDICTS) == expected_recalibration


def test_local_ledgers_are_deterministic_and_use_frozen_market_fields(tmp_path):
    ledger = tmp_path / "data/football_ledger"
    forecasts = ledger / "forecasts"
    forecasts.mkdir(parents=True)
    rows = []
    for i in range(4):
        fixture = {"league": "EN1", "event_id": str(i), "home": "H", "away": "A"}
        if i != 2:
            fixture["verified_start_utc"] = day(2).isoformat()
        prediction = {"probabilities": dict(zip(("home", "draw", "away"), P))}
        if i != 1:
            prediction.update(over={"2.5": .8}, both_teams_score=.8)
        record = {"spec": "football-prospective-v1", "recorded_at_utc": day(1).isoformat(),
                  "fixture": fixture, "prediction": prediction}
        record["payload_sha256"] = digest(record)
        (forecasts / f"{i}.json").write_text(json.dumps(record), encoding="utf-8")
        rows.append({"status": "publisher_final", "fixture_review": i == 3,
                     "fixture": fixture, "recorded_at_utc": record["recorded_at_utc"],
                     "prediction": {"over": {"2.5": .01}, "both_teams_score": .01},
                     "result": {"actual_home": 2, "actual_away": 1}})

    (ledger / "latest.json").write_text(json.dumps({
        "spec": "football-daily-v1", "checked_at_utc": day(3).isoformat(), "forecasts": rows,
    }), encoding="utf-8")
    output = tmp_path / "out"
    report = run(tmp_path, output)
    files = [output / name for name in ("report.json", "report.md")]
    original = [path.read_bytes() for path in files]
    assert report == run(tmp_path, output)
    assert original == [path.read_bytes() for path in files]

    import hashlib
    assert report["input_sha256"]["data/football_ledger/latest.json"] == hashlib.sha256(
        (ledger / "latest.json").read_bytes()).hexdigest()
    assert len(report["input_sha256"]) == 5
    assert report["n"] == 2
    assert report["exclusions"]["publisher_finals_without_verified_kickoff"] == 1
    assert report["exclusions"]["fixture_review"] == 1
    scaling = report["one_x_two"]["temperature"]
    assert scaling["recalibration_verdict"] == "inconclusive (n too small)"
    assert scaling["walk_forward_ran"] is False
    assert scaling["fitted_n"] == 0
    assert scaling["fallback_n"] == 2
    assert all(choice["temperature"] is None for choice in scaling["choices"])
    assert scaling["improvement"]["ci95"]["log_loss"] == [0, 0]
    limitation = scaling["walk_forward_limitation"]
    assert "0 of 2 games had at least 30 earlier finals known before freeze" in limitation
    assert "no per-game result times" in limitation
    assert "No temperature was applied, and no calibration conclusion is possible yet." in limitation
    assert report["one_x_two"]["reliability_scope"] in limitation
    rendered = (output / "report.md").read_text(encoding="utf-8")
    assert f"## 1X2 walk-forward temperature\n\n{limitation}" in rendered
    assert report["protocol"]["multiple_comparisons"] in rendered
    for market in report["markets"].values():
        assert market["skill_verdict"] == "inconclusive (n too small)"
        assert market["n"] == market["missing_probability"] == 1
        assert market["baseline_mean_probability"] == .5
        assert market["candidate"]["hit_rate"] == 1
        assert market["candidate"]["log_loss"] == pytest.approx(-np.log(.8))
        assert market["candidate"]["brier"] == pytest.approx(.04)
        assert market["probability_coverage"] == .5
        assert market["reliability"]["ece"] == pytest.approx(.2)
        assert market["reliability"]["bins"][8]["n"] == 1
    assert "Ten-bin ECE" in rendered
    assert "Descriptive ten-bin" in rendered


@pytest.mark.parametrize(("probabilities", "outcomes", "expected_ece", "expected_coverage"), [
    ([0., .5, 1., None], [False, True, True, False], 1/6, .75),
    ([.2, .2, .2, .8], [False, False, True, True], .15, 1.),
    ([None], [True], None, 0.),
    ([], [], None, None),
])
def test_binary_calibration_uses_only_available_frozen_probabilities(
    probabilities, outcomes, expected_ece, expected_coverage,
):
    from bbtahmin.football_calibration_report import _binary_market
    games = [game(i, 1, 2, 0) for i in range(len(probabilities))]
    report = _binary_market(games, probabilities, outcomes)
    bins = report["reliability"]["bins"]
    assert sum(row["n"] for row in bins) == report["n"]
    assert report["eligible_games"] == len(games)
    assert report["probability_coverage"] == expected_coverage
    if expected_ece is None:
        assert report["reliability"]["ece"] is None
    else:
        assert report["reliability"]["ece"] == pytest.approx(expected_ece)
    if probabilities and probabilities[0] == 0.:
        assert [bins[i]["n"] for i in (0, 5, 9)] == [1, 1, 1]
        assert bins[5]["forecast_mean"] == .5
        assert bins[5]["observed_frequency"] == 1.
    assert all(row["forecast_mean"] is None and row["observed_frequency"] is None
               for row in bins if not row["n"])
