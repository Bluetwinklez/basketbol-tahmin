import numpy as np
import pytest

from scripts.evaluate_football_draw import adjust_close_draw, draw_adjust, evaluate, fit_close_draw


def games(year, labels):
    return [
        {"event_id": f"{year}-{i}", "day": f"{year}-01-{i // 4 + 1:02d}",
         "y": label, "p": [0.36, 0.32, 0.32], "data_gate_passed": True}
        for i, label in enumerate(labels)
    ]


def test_draw_adjust_preserves_home_away_odds_and_input():
    p = np.array([[0.5, 0.3, 0.2]])
    adjusted = draw_adjust(p, 1.25)
    np.testing.assert_allclose(adjusted.sum(axis=1), [1])
    assert adjusted[0, 0] / adjusted[0, 2] == pytest.approx(2.5)
    assert adjusted[0, 1] > p[0, 1]
    np.testing.assert_allclose(p, [[0.5, 0.3, 0.2]])


def test_target_results_cannot_change_selected_policy():
    prior = games(2024, [1] * 80)
    a, _ = evaluate(prior, games(2025, [0] * 12))
    b, _ = evaluate(prior, games(2025, [1] * 12))
    assert a["selected_draw"] is b["selected_draw"] is True
    assert a["draw_multiplier"] == b["draw_multiplier"]
    assert a["close_coefficients"] == b["close_coefficients"]
    assert a["selected_close"] is b["selected_close"]
    assert a["target"]["gated_draw"]["all"]["accuracy"] == 0
    assert b["target"]["gated_draw"]["all"]["accuracy"] == 1


def test_reject_reused_fixtures_and_overlapping_dates():
    prior = games(2024, [1] * 80)
    duplicate = games(2025, [1] * 12)
    duplicate[0]["event_id"] = prior[0]["event_id"]
    with pytest.raises(ValueError, match="reused"):
        evaluate(prior, duplicate)
    with pytest.raises(ValueError, match="strictly ordered"):
        evaluate(prior, games(2024, [1] * 12))


def test_close_draw_learns_different_adjustments_for_balanced_games():
    p = np.tile([[0.35, 0.30, 0.35], [0.55, 0.30, 0.15]], (100, 1))
    y = np.tile([1, 0], 100)
    adjusted = adjust_close_draw(p, fit_close_draw(y, p))
    assert adjusted[0, 1] > adjusted[1, 1]
    np.testing.assert_allclose(adjusted.sum(axis=1), 1)
    np.testing.assert_allclose(adjusted[:, 0] / adjusted[:, 2], p[:, 0] / p[:, 2])
