import hashlib
import json
import math

import pytest

from bbtahmin.football.daily import digest
from bbtahmin.prospective import canonical
from scripts.live_scorecard import run


def utc(day, hour=12):
    return f"2026-10-{day:02}T{hour:02}:00:00+00:00"


def save(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def basketball_game(root, event, day, probability, score=None, capture=None,
                    frozen=None, league="E", odds=None):
    fixture = dict(event_id=event, league=league, home="H", away="A", start_utc=utc(day))
    prediction = {"ev_kazanir": probability}
    if odds:
        prediction.update(oran_ev=odds[0], oran_dep=odds[1])
    record = dict(spec="prospective-v1", recorded_at_utc=frozen or utc(day, 8),
                  forecasts=[dict(fixture=fixture, prediction=prediction)])
    record["payload_sha256"] = hashlib.sha256(canonical(record)).hexdigest()
    path = f"data/basketball_ledger/forecasts/{event}.json"
    save(root / path, record)
    row = dict(event_id=event, home="H", away="A", status="pending")
    if score is not None:
        row.update(status="final", actual_home=score[0], actual_away=score[1],
                   captured_at=capture or utc(day, 15))
    return dict(record=path, forecast_sha256=record["payload_sha256"],
                checked_at_utc=utc(23), games=[row])


def basketball_checks(root, batches):
    save(root / "data/basketball_ledger/check_1.json",
         dict(spec="daily-research-v1", checked_at_utc=utc(23, 11), settlements=batches))


def football_game(root, event, day, probabilities, score, verified=True, league="EN1"):
    fixture = dict(event_id=event, league=league, home="H", away="A")
    if verified:
        fixture["verified_start_utc"] = utc(day)
    prediction = dict(probabilities=dict(zip(("home", "draw", "away"), probabilities)))
    record = dict(spec="football-prospective-v1", recorded_at_utc=utc(day - 1),
                  fixture=fixture, prediction=prediction)
    record["payload_sha256"] = digest(record)
    save(root / f"data/football_ledger/forecasts/{event}.json", record)
    return dict(fixture=fixture, recorded_at_utc=record["recorded_at_utc"],
                status="publisher_final", result=dict(actual_home=score[0], actual_away=score[1]),
                prediction={"probabilities": {"home": 1, "draw": 0, "away": 0}})


def football_report(root, rows):
    save(root / "data/football_ledger/latest.json",
         dict(spec="football-daily-v1", checked_at_utc=utc(24), forecasts=rows))


def test_model_metrics_and_paired_market(tmp_path):
    first = basketball_game(tmp_path, "a", 1, .75, (80, 75), odds=(2, 4))
    second = basketball_game(tmp_path, "b", 2, .50, (76, 81))
    basketball_checks(tmp_path, [first, second, first])
    output = tmp_path / "out"
    report = run(tmp_path, output)
    group = report["sports"]["basketball"]["total"]
    model = group["model"]
    assert model["n"] == 2
    assert model["accuracy"] == .5
    assert model["log_loss"] == pytest.approx(-(math.log(.75) + math.log(.50)) / 2)
    assert model["brier"] == .15625
    assert model["ci95"]["accuracy"] == pytest.approx([.09453, .90547], abs=1e-5)
    assert model["ci95"]["log_loss"] == pytest.approx([-math.log(.75), -math.log(.50)])
    assert model["ci95"]["brier"] == [.0625, .25]
    assert group["always_home"]["accuracy"] == .5
    assert group["always_home"]["log_loss"] == pytest.approx(-math.log(1e-15) / 2)
    assert group["market"]["metrics"]["n"] == group["market"]["model_same_games"]["n"] == 1
    assert group["market"]["metrics"]["log_loss"] == pytest.approx(-math.log(2 / 3))
    assert group["market"]["model_same_games"]["log_loss"] == pytest.approx(-math.log(.75))
    assert report == json.loads((output / "scorecard.json").read_text(encoding="utf-8"))
    assert "Model on market games" in (output / "scorecard.md").read_text(encoding="utf-8")


def test_expanding_rates_respect_capture_freeze_and_league(tmp_path):
    early = basketball_game(tmp_path, "a", 1, .70, (90, 80))
    delayed = basketball_game(tmp_path, "b", 2, .70, (80, 90), capture=utc(4, 8))
    target = basketball_game(tmp_path, "c", 4, .70, (90, 80))
    other_league = basketball_game(tmp_path, "d", 5, .70, (90, 80), league="KBL")
    basketball_checks(tmp_path, [target, delayed, other_league, early])
    summary = run(tmp_path, tmp_path / "out")["sports"]["basketball"]
    # Outcomes see actual-class rates of 1/2, 1/3, 2/3 and 1/2. The delayed
    # away final was captured exactly at the target freeze and is unavailable.
    assert summary["total"]["expanding_rate"]["log_loss"] == pytest.approx(
        -sum(math.log(p) for p in (.5, 1 / 3, 2 / 3, .5)) / 4
    )
    assert summary["leagues"]["KBL"]["expanding_rate"]["log_loss"] == pytest.approx(math.log(2))


def test_pending_and_calibration_boundaries(tmp_path):
    batches = [
        basketball_game(tmp_path, "a", 1, .50, (90, 80)),
        basketball_game(tmp_path, "b", 2, .60, (80, 90)),
        basketball_game(tmp_path, "c", 3, 1.0, (90, 80)),
        basketball_game(tmp_path, "pending", 4, .70),
    ]
    basketball_checks(tmp_path, batches)
    group = run(tmp_path, tmp_path / "out")["sports"]["basketball"]["total"]
    assert group["model"]["n"] == sum(row["n"] for row in group["calibration"]) == 3
    assert [row["n"] for row in group["calibration"]] == [1, 1, 0, 0, 1]
    assert group["calibration"][1]["observed_frequency"] == 0
    assert group["calibration"][-1]["forecast_mean"] == 1
    assert group["market"]["status"] == "no market data"


def test_football_multiclass_and_date_only_exclusion(tmp_path):
    first = football_game(tmp_path, "a", 2, (.35, .40, .25), (0, 0))
    second = football_game(tmp_path, "b", 3, (.30, .20, .50), (1, 0))
    legacy = football_game(tmp_path, "legacy", 4, (.7, .2, .1), (1, 0), verified=False, league="TR1")
    football_report(tmp_path, [first, second, legacy])
    summary = run(tmp_path, tmp_path / "out")["sports"]["football"]
    group = summary["total"]
    assert summary["publisher_finals_excluded_no_verified_kickoff"] == 1
    assert summary["kickoff_exclusions_by_league"] == {"TR1": 1}
    assert summary["leagues"]["TR1"]["model"]["n"] == 0
    assert group["model"]["n"] == sum(row["n"] for row in group["calibration"]) == 2
    assert group["model"]["accuracy"] == .5
    assert group["model"]["log_loss"] == pytest.approx(-(math.log(.40) + math.log(.30)) / 2)
    assert group["model"]["brier"] == pytest.approx((.35**2 + .60**2 + .25**2 + .70**2 + .20**2 + .50**2) / 2)
    assert group["expanding_rate"]["log_loss"] == pytest.approx(math.log(3))
    frequencies = group["class_frequencies"]
    assert [frequencies[label]["top_pick_n"] for label in ("home", "draw", "away")] == [0, 1, 1]
    assert [frequencies[label]["actual_n"] for label in ("home", "draw", "away")] == [1, 1, 0]


def test_basketball_final_requires_matching_forecast_checksum(tmp_path):
    batch = basketball_game(tmp_path, "a", 1, .75, (80, 75))
    batch["forecast_sha256"] = "0" * 64
    basketball_checks(tmp_path, [batch])
    with pytest.raises(ValueError, match="no matching frozen forecast"):
        run(tmp_path, tmp_path / "out")


def test_empty_input(tmp_path):
    report = run(tmp_path, tmp_path / "out")
    assert report["data_cutoff_utc"] is None
    for sport in report["sports"].values():
        assert sport["leagues"] == {}
        assert sport["total"]["model"] == {
            "n": 0, "accuracy": None, "log_loss": None, "brier": None,
            "ci95": {"accuracy": None, "log_loss": None, "brier": None},
        }
