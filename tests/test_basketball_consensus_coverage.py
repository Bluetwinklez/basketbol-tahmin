import pandas as pd

from scripts.evaluate_basketball_consensus_coverage import select, summarize


def test_consensus_replaces_only_same_day_slots_independently_of_outcome():
    games = pd.DataFrame({
        "mac_id": ["high", "agreed", "tomorrow"],
        "tarih_utc": pd.to_datetime(["2026-11-01T18:00Z", "2026-11-01T20:00Z", "2026-11-02T18:00Z"]),
        "ev_skor": [75, 90, 90],
        "dep_skor": [90, 75, 75],
    })
    probabilities = {"score": [0.8, 0.64, 0.61], "logistic": [0.3, 0.65, 0.8], "elo": [0.75, 0.66, 0.8]}
    chosen = select(games, probabilities, "score")
    assert chosen.loc[chosen["reference"], "mac_id"].tolist() == ["high"]
    assert chosen.loc[chosen["candidate"], "mac_id"].tolist() == ["agreed"]
    summary = summarize(chosen)
    assert (summary["selected"], summary["replaced"], summary["reference_correct"], summary["candidate_correct"]) == (1, 1, 0, 1)
    games[["ev_skor", "dep_skor"]] = games[["dep_skor", "ev_skor"]].to_numpy()
    rescored = select(games, probabilities, "score")
    assert rescored["candidate"].equals(chosen["candidate"])
    assert rescored["correct"].tolist() != chosen["correct"].tolist()
