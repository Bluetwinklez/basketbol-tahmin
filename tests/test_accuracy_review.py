import numpy as np
import pandas as pd
from bbtahmin.ozellik import build_features,select_columns,FEATURES,EXTENDED_FEATURES


def test_extended_features_do_not_change_base_columns(games):
    x=build_features(games)
    assert set(EXTENDED_FEATURES)<=set(x.columns)
    assert np.isfinite(x[EXTENDED_FEATURES].to_numpy(float)).all()
    # Season phase: a team's first game of a season has no in-season history.
    first=x.set_index('mac_id').loc['E_0']
    assert first.early==1. and first.season_margin_diff==0.


def test_select_columns_uses_only_given_rows(games):
    g=games[games.lig=='NBA'].reset_index(drop=True)
    x=build_features(g);margin=(g.ev_skor-g.dep_skor).to_numpy(float)
    train=np.zeros(len(g),bool);validation=np.zeros(len(g),bool)
    # Too few games: always the established base set.
    assert select_columns(x,margin,train,validation)==FEATURES
    rng=np.random.default_rng(0)
    big=pd.concat([x]*10,ignore_index=True);big[EXTENDED_FEATURES]=rng.normal(size=(len(big),len(EXTENDED_FEATURES)))
    target=np.tile(margin,10);train=np.arange(len(big))<len(big)*.7;validation=~train
    chosen=select_columns(big,target,train,validation)
    assert chosen in (FEATURES,FEATURES+EXTENDED_FEATURES)
    # Changing only excluded rows (neither train nor validation) never changes the choice.
    excluded=np.zeros(len(big),bool);excluded[-5:]=True
    t2=target.copy();t2[excluded]+=1000
    assert select_columns(big,t2,train&~excluded,validation&~excluded)==select_columns(big,target,train&~excluded,validation&~excluded)


def test_windows_ledger_paths_resolve(tmp_path,monkeypatch):
    from bbtahmin import app
    monkeypatch.chdir(tmp_path)
    (tmp_path/'data'/'ledger').mkdir(parents=True)
    (tmp_path/'data'/'ledger'/'f.json').write_text('{}',encoding='utf8')
    calls=[]
    import bbtahmin.prospective as prospective
    monkeypatch.setattr(prospective,'verify',lambda payload:calls.append(payload) or {'forecasts':[]})
    app.result_rows({'settlements':[{'record':'data\\ledger\\f.json','games':[]}]})
    assert calls==[{}]


def test_football_default_is_opponent_adjusted():
    from bbtahmin.football.challenger import DEFAULT_VARIANT,fit
    import inspect
    assert DEFAULT_VARIANT=='opponent'
    assert inspect.signature(fit).parameters['variant'].default=='opponent'
