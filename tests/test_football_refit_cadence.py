from scripts.evaluate_football_refit_cadence import cutoffs


def test_cadences_use_the_forecast_date_instead_of_match_date():
    assert cutoffs("2026-09-06", 7) == dict(
        daily="2026-08-30", weekly="2026-08-24", monthly="2026-08-01",
    )
    assert cutoffs("2026-09-08", 1) == dict(
        daily="2026-09-07", weekly="2026-09-07", monthly="2026-09-01",
    )
