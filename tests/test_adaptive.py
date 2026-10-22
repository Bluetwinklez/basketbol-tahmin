import numpy as np
import pandas as pd
import pytest
from bbtahmin import adaptive,competition_model
from bbtahmin.ozellik import build_features


def test_selection_and_first_target_day_ignore_target_and_future_outcomes():
    g=competition_model.load('ECW');first=g.loc[g.sezon=='2025-26','tarih_utc'].min().floor('D')
    original,choices=adaptive.walk_forward('ECW',g)
    altered=g.copy();mask=altered.tarih_utc>=first
    altered.loc[mask,'ev_skor']=150;altered.loc[mask,'dep_skor']=20
    changed,other_choices=adaptive.walk_forward('ECW',altered)
    assert choices[0]==other_choices[0] and choices[0]['monthly_selected']
    ids=g.loc[(g.sezon=='2025-26')&(g.tarih_utc.dt.floor('D')==first),'mac_id']
    a=original.set_index('mac_id').loc[ids];b=changed.set_index('mac_id').loc[ids]
    np.testing.assert_allclose(a[['p','margin_prediction','total_prediction']],b[['p','margin_prediction','total_prediction']])


def test_current_month_outcomes_never_fit_current_month_model():
    g=competition_model.load('ECW');x=build_features(g)
    history=(g.sezon<'2025-26').to_numpy();test=(g.sezon=='2025-26').to_numpy()
    month=g.loc[test,'tarih_utc'].dt.strftime('%Y-%m').min()
    same_month=(g.tarih_utc.dt.strftime('%Y-%m')==month).to_numpy()
    first=adaptive._predictions(x,g,history,test,True)
    mutated=g.copy();mutated.loc[same_month,'ev_skor']=199
    other=adaptive._predictions(x,mutated,history,test,True)
    # Hold features fixed here to isolate estimator fitting from legitimate earlier-day feature updates.
    np.testing.assert_allclose(first[same_month[test]],other[same_month[test]])


def test_runtime_prediction_is_time_causal_and_marks_experiment(monkeypatch):
    a=adaptive.predict('ECW','ECW_66458','ECW_892','2026-10-22T15:30Z')
    g=competition_model.load('ECW');g.loc[g.tarih_utc>=pd.Timestamp('2026-10-22',tz='UTC'),'ev_skor']=999
    monkeypatch.setattr(competition_model,'load',lambda _:g)
    b=adaptive.predict('ECW','ECW_66458','ECW_892','2026-10-22T15:30Z')
    assert a['ev_kazanir']==b['ev_kazanir'] and a['toplam']==b['toplam']
    assert a['experimental'] and a['adaptive_selection']['selection_season']=='2025-26'
    assert not a['adaptive_selection']['monthly_selected']


def test_adaptive_option_requires_explicit_supported_league():
    from bbtahmin.tahmin import run
    with pytest.raises(ValueError,match='explicit'):run('NBA',['A - B'],None,adaptive_form=True)
