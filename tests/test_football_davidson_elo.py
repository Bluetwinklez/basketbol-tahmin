from types import SimpleNamespace

import numpy as np

from scripts.evaluate_football_davidson_elo import DavidsonElo


def test_same_day_results_update_after_the_whole_day():
    first = DavidsonElo()
    second = DavidsonElo()
    games = [
        SimpleNamespace(home="a", away="b", home_goals=0, away_goals=4),
        SimpleNamespace(home="a", away="c", home_goals=1, away_goals=1),
    ]
    prior = first.predict("a", "c")
    first.observe_day(games)
    second.observe_day(games[::-1])
    np.testing.assert_allclose(first.predict("a", "c"), second.predict("a", "c"))
    assert first.predict("a", "c")[0] < prior[0]
    assert abs(first.predict("a", "c").sum() - 1) < 1e-12
