import numpy as np
import pandas as pd
import pytest

from bbtahmin.elo import expected
from scripts.evaluate_basketball_carryover import DEFAULT, GRID, choose, scored_fixtures


def test_new_teams_start_at_neutral_rating_and_same_day_results_do_not_leak():
    games = pd.DataFrame([
        ("prior", "2025-10-01", "2025-26", "A", "B", 98, 80, False),
        ("debut", "2026-10-01", "2026-27", "C", "D", 99, 82, False),
        ("same-day", "2026-10-01", "2026-27", "C", "A", 75, 96, False),
    ], columns=["mac_id", "tarih_utc", "sezon", "ev", "dep", "ev_skor", "dep_skor", "tarafsiz_saha"])
    games["lig"] = "KBL"
    games["tarih_utc"] = pd.to_datetime(games["tarih_utc"], utc=True)
    before = scored_fixtures(games).set_index("mac_id")
    games.loc[games["mac_id"].eq("debut"), ["ev_skor", "dep_skor"]] = [80, 120]
    after = scored_fixtures(games).set_index("mac_id")
    np.testing.assert_allclose(before.loc["debut", list(GRID)].astype(float), expected(1500, 1500, 50))
    np.testing.assert_allclose(before.loc["same-day", list(GRID)].astype(float),
                               after.loc["same-day", list(GRID)].astype(float))
    assert bool(before.loc["debut", "returning_or_new"])


def test_choose_uses_only_three_earlier_seasons():
    rows = []
    for year in range(2022, 2026):
        for _ in range(20):
            rows.append({
                "sezon": f"{year}-{(year + 1) % 100:02}", "early": True,
                "day": pd.Timestamp(f"{year}-10-01", tz="UTC"), "y": 1,
                **{shrink: .60 if shrink == .05 else .55 for shrink in GRID},
            })
    frame = pd.DataFrame(rows)
    selected, prior, evidence = choose(frame, "2025-26")
    target = frame["sezon"].eq("2025-26")
    frame.loc[target, "y"] = 0
    assert choose(frame, "2025-26") == (selected, prior, evidence)
    assert selected == .05
    assert evidence[DEFAULT]["mean_log_loss_delta"] == 0
    frame.loc[~target, "day"] = pd.Timestamp("2026-01-01", tz="UTC")
    with pytest.raises(ValueError, match="finish before"):
        choose(frame, "2025-26")
