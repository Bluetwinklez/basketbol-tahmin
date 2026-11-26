import pandas as pd

from bbtahmin.football.challenger import fit
from scripts.evaluate_football_opponent_half_life import ResearchOpponent


def test_reference_recency_reuses_production_fit_and_ignores_future_results():
    dates = pd.date_range("2025-01-01", periods=140, freq="3D")
    history = pd.DataFrame({
        "league": "EN1", "status": "final", "date": dates.strftime("%Y-%m-%d"),
        "home": ["a", "b", "c", "d"] * 35, "away": ["c", "d", "b", "a"] * 35,
        "home_goals": [1, 2, 3, 2] * 25 + [3, 2, 0, 1] * 10, "away_goals": [1, 2, 1, 0] * 35,
    })
    cutoff = "2026-01-01"
    reference = fit(history, "EN1", cutoff, "opponent").predict("a", "b")
    standard = ResearchOpponent(history, "EN1", cutoff, 180).predict("a", "b")
    assert standard == reference
    faster = ResearchOpponent(history, "EN1", cutoff, 90).predict("a", "b")
    assert faster["probabilities"] != standard["probabilities"]
    history.loc[history["date"] >= cutoff, "home_goals"] = 9
    assert ResearchOpponent(history, "EN1", cutoff, 90).predict("a", "b") == faster
