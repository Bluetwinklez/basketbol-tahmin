import json
import math

import pandas as pd
import pytest

from bbtahmin.bulletin import compare,list_events
from bbtahmin.veri.iddaa import normalize,load


def payload():
    event=dict(i=1,sid=2,hn='Boston Celtics',an='New York Knicks',ci=7,d=2051222400,mbc=2,
        m=[dict(t=1,st=2,s=1,o=[dict(n='1',odd=1.8,wodd=1.7),dict(n='2',odd=2.1)]),
           dict(t=2,st=114,s=1,sov='220',o=[dict(n='Alt',odd=1.9),dict(n='Üst',odd=1.9)]),
           dict(t=2,st=621,s=1,o=[dict(n='1',odd=1.8),dict(n='0',odd=15),dict(n='2',odd=2)])])
    competitions=[dict(i=7,n='ABD Amerika Basketbol Ligi')]
    markets={'1_2':dict(n='Maç Sonucu (Uzt.Dahil)',st=2),'2_114':dict(n='Toplam Sayı Alt/Üst (Uzt.Dahil) {0}',st=2),
             '2_621':dict(n='1. Yarı Sonucu',st=2)}
    return event,competitions,markets


def test_market_semantics_overtime_and_three_way_separation():
    event,competitions,markets=payload()
    result=normalize([event],competitions,markets,'2034-01-01T00:00Z')['events'][0]
    assert result['model_league']=='NBA' and result['pre_match']
    assert result['moneyline']['home_odds']==1.8
    assert result['moneyline']['home_alternative_price']==1.7
    assert result['moneyline']['includes_overtime']
    assert result['moneyline']['minimum_combination_count']==2
    assert result['totals'][0]['push_possible']
    markets['1_2']['n']='Maç Sonucu'  # do not guess overtime settlement from two outcomes
    assert normalize([event],competitions,markets,'2034-01-01T00:00Z')['events'][0]['moneyline'] is None


def test_suspended_and_invalid_odds_are_not_compared():
    event,c,m=payload();event['m'][0]['s']=0
    assert normalize([event],c,m,'2034-01-01T00:00Z')['events'][0]['moneyline'] is None
    event['m'][0]['s']=1;event['m'][0]['o'][0]['odd']=math.nan
    assert normalize([event],c,m,'2034-01-01T00:00Z')['events'][0]['moneyline'] is None


def test_womens_competition_cannot_use_mens_euroleague_model():
    event,c,m=payload();c[0]['n']='Euroleague Kadınlar'
    assert normalize([event],c,m,'2034-01-01T00:00Z')['events'][0]['model_league'] is None


def test_snapshot_age_and_future_capture(tmp_path):
    event,c,m=payload();snapshot=normalize([event],c,m,'2034-01-01T00:00Z')
    (tmp_path/'data/bulten').mkdir(parents=True)
    path=tmp_path/'data/bulten/latest.json';path.write_text(json.dumps(snapshot))
    assert not load(path,now='2034-01-01T00:10Z')['stale']
    assert load(path,now='2034-01-01T00:16Z')['stale']
    with pytest.raises(ValueError,match='future'):
        load(path,now='2033-12-31T23:59Z')
    assert list_events(tmp_path,'NBA',1,now='2034-01-01T00:10Z')['total_upcoming']==1


def test_integer_total_push_has_zero_profit_and_correct_expected_return():
    prediction=dict(ev_kazanir=.6,toplam=220.,toplam_80=(207.184484344554,232.815515655446))
    event=dict(moneyline=None,totals=[dict(line=220.,under_odds=2.,over_odds=2.)])
    result=compare(prediction,event)['totals'][0]
    assert sum(result[k] for k in ['under','over','push'])==pytest.approx(1)
    assert result['push']>0
    assert result['over_expected_return']==pytest.approx(0)
    event['totals'][0]['line']=220.5
    assert compare(prediction,event)['totals'][0]['push']==0
