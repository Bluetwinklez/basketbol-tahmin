import numpy as np
import pandas as pd

from scripts.evaluate_basketball_home_advantage import choose, win_probability


def test_direct_home_adjustment_keeps_neutral_predictions_equal():
    frame = pd.DataFrame({"elo_diff": [12, 12], "home": [1, 0]})
    reference = win_probability(frame, 50)
    candidate = win_probability(frame, 75)
    assert candidate[0] > reference[0]
    assert candidate[1] == reference[1]


def test_home_advantage_uses_only_earlier_season_labels():
    periods = []
    for year in range(2023, 2026):
        periods.append(pd.DataFrame({
            "sezon": [f"{year}-{(year + 1) % 100:02}"] * 120,
            "day": [pd.Timestamp(f"{year}-10-01", tz="UTC")] * 120,
            "elo_diff": [-65] * 120, "home": [1] * 120, "y": [1] * 120,
        }))
    data = pd.concat(periods, ignore_index=True)
    chosen = choose(data, "2025-26")
    data.loc[data["sezon"].eq("2025-26"), "y"] = 0
    assert choose(data, "2025-26") == chosen
    assert chosen[0] == 100
    np.testing.assert_allclose(chosen[2][50]["season_log_loss_deltas"], [0, 0])
