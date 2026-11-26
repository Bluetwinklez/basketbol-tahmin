import numpy as np
import pytest
from scripts.evaluate_football_opponent_followup import replay_policy

from scripts.evaluate_football_draw import adjust_close_draw, draw_adjust, evaluate, fit_close_draw


def games(year, labels):
    return [
        {"event_id": f"{year}-{i}", "day": f"{year}-01-{i // 4 + 1:02d}",
         "y": label, "p": [0.36, 0.32, 0.32], "data_gate_passed": True,
         "expected_total_goals": 2.0 + (i % 4) / 2}
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
    assert a["context_coefficients"] == b["context_coefficients"]
    assert a["selected_goal_context"] is b["selected_goal_context"]
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


def test_goal_context_distinguishes_matches_with_the_same_balance():
    probabilities = np.tile([0.35, 0.30, 0.35], (200, 1))
    totals = np.tile([1.7, 3.8], 100)
    y = np.tile([1, 0], 100)
    candidate = adjust_close_draw(probabilities, fit_close_draw(y, probabilities, totals), totals)
    assert candidate[0, 1] > candidate[1, 1]
    np.testing.assert_allclose(candidate.sum(axis=1), 1)
    np.testing.assert_allclose(candidate[:, 0] / candidate[:, 2], 1)

def test_replay_uses_frozen_variant_and_temperature():
    policy = {"variant": "opponent_dc", "temperature": 0.75, "prior_season": "2025-26",
              "last_prior_day": "2026-05-17"}
    base = {"event_id": "match", "season": "2026-27", "day": "2026-08-07",
            "variant": "baseline", "p": [0.25, 0.25, 0.5]}
    selected = dict(base, variant="opponent_dc", p=[0.5, 0.25, 0.25])
    row, = replay_policy([base, selected], policy, "2026-27")
    assert row["variant"] == "frozen_policy"
    assert row["p"][0] > 0.5
    assert selected["p"] == [0.5, 0.25, 0.25]
    with pytest.raises(ValueError, match="precede"):
        replay_policy([base, selected], dict(policy, last_prior_day=base["day"]), "2026-27")
