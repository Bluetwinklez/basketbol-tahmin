import json

import numpy as np
import pandas as pd

from bbtahmin.model import regression
from bbtahmin.tahmin import aktif_kodlar
from bbtahmin.tahmin import en_iyi_model, parametreler


def test_history_window_selection_never_reads_test_targets():
    rng = np.random.default_rng(42)
    seasons = np.repeat([f'{y}-{str(y+1)[-2:]}' for y in range(2000, 2014)], 30)
    x = pd.DataFrame({'signal': rng.normal(size=len(seasons))})
    target = 4*x.signal.to_numpy() + rng.normal(size=len(seasons))
    train, val, test = seasons < '2012-13', seasons == '2012-13', seasons == '2013-14'
    p1, details1 = regression(x, target, train, val, test, ['signal'], seasons=seasons, objective='log_loss')
    altered = target.copy()
    altered[test] = rng.normal(1000, 100, test.sum())
    p2, details2 = regression(x, altered, train, val, test, ['signal'], seasons=seasons, objective='log_loss')
    np.testing.assert_array_equal(p1, p2)
    assert details1 == details2
    assert details1['history_window'] in [None,3,5,10]
    assert len(details1['validation_losses']) == 12


def test_historical_model_selection_excludes_target_and_future_seasons(tmp_path):
    path = tmp_path/'toplam.csv'
    pd.DataFrame([
        dict(lig='NBA',sezon='2020-21',model='skor',n=100,log_loss=.6),
        dict(lig='NBA',sezon='2020-21',model='logistic',n=100,log_loss=.7),
        dict(lig='NBA',sezon='2021-22',model='logistic',n=10000,log_loss=.1),
    ]).to_csv(path.with_name('metrikler.csv'),index=False)
    assert en_iyi_model('NBA',path,sezon='2021-22') == 'skor'
    assert en_iyi_model('NBA',path,sezon='2020-21') == 'mov_elo'


def test_historical_parameters_cannot_use_future_folds(tmp_path):
    path = tmp_path/'parametreler.json'
    path.write_text(json.dumps([
        dict(lig='NBA',sezon='2020-21',model='mov',k=10),
        dict(lig='NBA',sezon='2020-21',model='ewma',alpha=.1),
        dict(lig='NBA',sezon='2022-23',model='mov',k=30),
    ]))
    mov, alpha = parametreler('NBA',path,sezon='2021-22')
    assert mov['k'] == 10 and alpha == .1


def test_future_games_cannot_activate_a_team():
    g = pd.DataFrame([
        dict(lig='NBA',tarih_utc=pd.Timestamp('2024-10-01',tz='UTC'),ev='BOS',dep='NYK'),
        dict(lig='NBA',tarih_utc=pd.Timestamp('2024-10-10',tz='UTC'),ev='FUTURE',dep='NYK'),
    ])
    assert aktif_kodlar(g,'NBA',pd.Timestamp('2024-10-05',tz='UTC')) == {'BOS','NYK'}
