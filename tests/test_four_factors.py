import numpy as np
import pandas as pd

from bbtahmin.four_factors import build_factors,FACTOR_FEATURES,FACTOR_LEAGUES


def fixture():
    games=pd.DataFrame([dict(mac_id=f'm{i}',lig='NBA',sezon='2024-25',ev='A',dep='B',ev_skor=100,dep_skor=90,
        tarih_utc=pd.Timestamp('2024-10-01T20:00Z')+pd.Timedelta(days=i)) for i in range(5)])
    boxes=pd.DataFrame([dict(mac_id=r.mac_id,rol=role,made=40+i,attempted=80,three_made=10,
        three_attempted=25,free_made=15,free_attempted=20,oreb=8,dreb=30,tov=12,sure=2880)
        for i,r in enumerate(games.itertuples()) for role in ('ev','dep')])
    return games,boxes


def test_target_and_future_boxes_cannot_change_pregame_factors():
    games,boxes=fixture();target='m3'
    expected=build_factors(games,boxes).set_index('mac_id').loc[target]
    changed=boxes.copy();changed.loc[changed.mac_id.isin(['m3','m4']),'made']=2
    actual=build_factors(games,changed).set_index('mac_id').loc[target]
    pd.testing.assert_series_equal(expected,actual)
    cutoff=games[games.mac_id==target].tarih_utc.iloc[0].floor('D')
    query=games[games.tarih_utc<cutoff].copy()
    query=pd.concat([query,games[games.mac_id==target].assign(ev_skor=np.nan,dep_skor=np.nan)],ignore_index=True)
    short=build_factors(query,boxes[boxes.mac_id.isin(query.mac_id)]).set_index('mac_id').loc[target]
    pd.testing.assert_series_equal(expected,short)


def test_same_day_boxes_are_withheld_and_experiment_is_disabled():
    games,boxes=fixture();games.loc[1,'tarih_utc']=games.loc[0,'tarih_utc']+pd.Timedelta(hours=1)
    factors=build_factors(games,boxes)
    assert (factors.loc[:1,FACTOR_FEATURES]==0).all().all()
    assert np.isfinite(factors[FACTOR_FEATURES]).all().all()
    assert not FACTOR_LEAGUES
