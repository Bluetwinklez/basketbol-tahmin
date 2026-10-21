import pandas as pd
import pytest
from bbtahmin.ozellik import features_for_match,build_features
from leakage_check import assert_no_leakage,leaky_features

@pytest.mark.parametrize('league',['E','U','NBA'])
@pytest.mark.parametrize('position',[2,5,9,14,20])
def test_future_deletion_invariance(games,league,position):
    match=games[games.lig==league].iloc[position].to_dict()
    assert_no_leakage(features_for_match,games,match)
    original=features_for_match(games,match)
    vector=build_features(games).set_index('mac_id').loc[match['mac_id']]
    pd.testing.assert_series_equal(original,vector,check_exact=True)

@pytest.mark.parametrize('league',['E','U','NBA'])
@pytest.mark.parametrize('position',[5,14])
def test_negative_control_detects_leakage(games,league,position):
    match=games[games.lig==league].iloc[position].to_dict()
    with pytest.raises(AssertionError):
        assert_no_leakage(leaky_features,games,match)

def test_same_day_results_withheld(games):
    altered=games.copy()
    altered.loc[altered.mac_id=='E_4','tarih_utc']=altered.loc[altered.mac_id=='E_5','tarih_utc'].iloc[0]
    first=build_features(altered).set_index('mac_id').loc['E_5']
    altered.loc[altered.mac_id=='E_4','ev_skor']=200
    second=build_features(altered).set_index('mac_id').loc['E_5']
    pd.testing.assert_series_equal(first,second,check_exact=True)

def test_timezone_equivalent_query(games):
    match=games[games.lig=='E'].iloc[6].to_dict()
    original=features_for_match(games,match)
    match['tarih_utc']=match['tarih_utc'].tz_convert('Europe/Istanbul')
    pd.testing.assert_series_equal(original,features_for_match(games,match),check_exact=True)
