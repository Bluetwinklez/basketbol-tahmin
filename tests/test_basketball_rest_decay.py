import numpy as np
import pandas as pd

from scripts.evaluate_basketball_rest_decay import workload


def test_workload_uses_only_completed_earlier_utc_days_within_league():
    games = pd.DataFrame([
        ("first", "E", "2026-02-01T18:00Z", "A", "X", 90., 80.),
        ("recent", "E", "2026-02-07T18:00Z", "X", "A", 90., 80.),
        ("other_league", "U", "2026-02-07T18:00Z", "A", "X", 90., 80.),
        ("same_day", "E", "2026-02-08T09:00Z", "A", "B", 90., 80.),
        ("fixture", "E", "2026-02-08T18:00Z", "A", "C", np.nan, np.nan),
        ("next_day", "E", "2026-02-09T18:00Z", "A", "C", 100., 80.),
    ], columns=["mac_id", "lig", "tarih_utc", "ev", "dep", "ev_skor", "dep_skor"])
    games["tarih_utc"] = pd.to_datetime(games["tarih_utc"], utc=True)
    result = workload(games)
    assert result[4] == 2 ** (-7 / 2) + 2 ** (-1 / 2)
    assert result[5] == 2 ** (-2 / 2) + 2 ** (-1 / 2)
    games.loc[3:, "ev_skor"] = 120.
    games.loc[3:, "dep_skor"] = 110.
    assert workload(games)[4] == result[4]
    shuffled = games.iloc[::-1]
    np.testing.assert_allclose(workload(shuffled)[::-1], workload(games))
