"""Explicit invocation must fail: verifies the leakage detector's sensitivity."""
from leakage_check import assert_no_leakage,leaky_features
def test_deliberately_leaky_feature(games):
    match=games[games.lig=='E'].iloc[5].to_dict()
    assert_no_leakage(leaky_features,games,match)
