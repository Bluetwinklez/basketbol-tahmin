import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bbtahmin.experiment_status import MINIMUM_GAMES, build_report
from bbtahmin.shadow import evaluate, freeze, register


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf8")


def _record_experiment(root, version, candidate_correct, pending_league=False):
    directory, identity = register(root, {"version": version})
    results = []
    cutoff = "2026-10-26T13:00:00+00:00"
    games = [("KBL", correct) for correct in candidate_correct]
    if pending_league:
        games.append(("ABA", True))
    for index, (league, correct) in enumerate(games):
        fixture = dict(
            event_id=str(index), league=league, home="a", away="b",
            start_utc="2026-10-27T12:00Z", captured_at="2026-10-26T12:00Z",
            source_url="https://example.org/game", status="scheduled",
        )
        reference = dict(
            league=league, home="a", away="b", class_labels=["home", "away"],
            probabilities=[0.3, 0.7], expected_home=80, expected_away=80,
            information_cutoff_utc=cutoff, eligible=True,
        )
        candidate = dict(reference, probabilities=[0.8, 0.2] if correct else [0.4, 0.6])
        freeze(directory, identity, fixture, dict(reference=reference, candidate=candidate), {}, now=cutoff)
        if league == "KBL":
            results.append(dict(fixture, status="final", captured_at="2026-10-27T15:00Z",
                                home_score=90, away_score=80))
    return dict(experiment_id=identity, **evaluate(directory, results, now="2026-10-27T16:00Z"))


@pytest.fixture
def history(tmp_path_factory):
    # Keep both the experiment identity and forecast hash within Windows path limits.
    root = tmp_path_factory.mktemp("xs")
    old = _record_experiment(root, "old", [True], pending_league=True)
    new = _record_experiment(root, "new", [True, False])
    _write_json(root / "active.json", {"experiment_id": new["experiment_id"]})
    _write_json(root / "latest.json", dict(
        experiment_id=old["experiment_id"], checked_at_utc=new["checked_at_utc"],
        experiments=[old, new],
    ))
    return root, old["experiment_id"], new["experiment_id"]


def test_status_keeps_identities_and_leagues_separate(history):
    root, old_id, new_id = history
    report = build_report(root)
    assert report["thresholds"]["minimum_settled_pairs_per_league"] == MINIMUM_GAMES == 1000
    experiments = {row["experiment_id"]: row for row in report["experiments"]}
    old, new = experiments[old_id], experiments[new_id]
    assert (old["status"], new["status"]) == ("superseded", "active")
    assert (old["settled_pairs"], new["settled_pairs"]) == (1, 2)
    assert new["verdict"] == "insufficient_sample"
    assert old["leagues"]["ABA"]["settled_pairs"] == 0
    assert old["leagues"]["ABA"]["precision_95_half_width"] is None
    assert old["leagues"]["ABA"]["n_still_needed"] == 1000
    league = new["leagues"]["KBL"]
    assert (league["candidate_only_correct"], league["reference_only_correct"]) == (1, 0)
    assert league["discordant_fraction"] == 0.5
    assert league["precision_95_half_width"] == pytest.approx(1.959963984540054 * math.sqrt(0.5 / 2))
    assert league["n_for_target_half_width"] == 4802
    assert league["n_still_needed"] == 4800

    report = build_report(root, minimum_games=2)
    experiments = {row["experiment_id"]: row for row in report["experiments"]}
    assert experiments[old_id]["verdict"] == "insufficient_sample"
    new = experiments[new_id]
    assert new["verdict"] == "concluded_better"
    assert new["leagues"]["KBL"]["accuracy_delta"] == 0.5
    assert new["leagues"]["KBL"]["accuracy_day_block_95_interval"] == [0.5, 0.5]
    assert new["leagues"]["KBL"]["log_loss_delta"] < 0

    (root / "active.json").unlink()
    assert build_report(root)["active_experiment_id"] == old_id


def test_script_writes_reports_outside_shadow(history, tmp_path):
    root, _, _ = history
    output = tmp_path / "reports"
    script = Path(__file__).resolve().parents[1] / "scripts" / "experiment_status.py"
    command = [sys.executable, "-X", "utf8", str(script), "--root", str(root), "--output"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    def snapshot():
        return {p.relative_to(root): (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                for p in root.rglob("*")}

    before = snapshot()
    protected_output = next((root / "experiments").iterdir()) / "reports"
    rejected = subprocess.run([*command, str(protected_output)], capture_output=True, env=env)
    assert rejected.returncode != 0
    assert b"Report output must be outside" in rejected.stderr
    subprocess.run([*command, str(output)], check=True, env=env)
    first = {p.name: p.read_bytes() for p in output.iterdir()}
    assert set(first) == {"status.json", "status.md"}
    assert len(json.loads(first["status.json"])["experiments"]) == 2
    assert "insufficient_sample" in first["status.md"].decode("utf8")
    subprocess.run([*command, str(output)], check=True, env=env)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == first
    assert snapshot() == before
