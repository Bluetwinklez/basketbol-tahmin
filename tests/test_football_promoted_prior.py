import itertools

import numpy as np
import pandas as pd

from scripts.evaluate_football_promoted_prior import predict, promoted_candidates


def test_promoted_prior_uses_only_previous_division_membership():
    clubs = [f"incumbent-{i}" for i in range(20)]
    upper = [dict(home=home, away=away, league="EN1", season="2025-26", date="2026-05-20", status="final")
             for home, away in itertools.permutations(clubs, 2)]
    lower = [dict(home=name, away="opponent", league="EN2", season="2025-26", date="2026-05-20", status="final",
                  home_goals=2, away_goals=1)
             for name in ("promoted", clubs[0]) for _ in range(40)]
    future = [dict(row, home="future-team", date="2026-07-01") for row in lower]
    assert promoted_candidates(pd.DataFrame(upper + lower + future), 2026) == {
        "promoted": 40 / 56, "opponent": -80 / 96,
    }


def test_promoted_prior_changes_only_the_unfaded_side():
    rows = [
        dict(expected_home=1.4, expected_away=1.1, home_weight=1, away_weight=0, home_form=.6, away_form=0),
        dict(expected_home=1.4, expected_away=1.1, home_weight=0, away_weight=0, home_form=.6, away_form=0),
    ]
    reference = predict(rows, 1, 1)
    candidate = predict(rows, .8, 1.2)
    transfer = predict(rows, .8, 1.2, .3, .4)
    assert candidate[0, 0] < reference[0, 0]
    assert transfer[0, 0] > candidate[0, 0]
    np.testing.assert_allclose(candidate[1], reference[1], atol=1e-13)
    np.testing.assert_allclose(transfer[1], reference[1], atol=1e-13)
    np.testing.assert_allclose(candidate.sum(axis=1), 1, atol=1e-13)
