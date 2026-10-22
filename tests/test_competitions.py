import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from bbtahmin import competition_model as model
from bbtahmin.takim_ad import coz
from bbtahmin.veri.competitions import fiba_games,normalize_fiba


def row():
    return dict(gameId=1,teamA=dict(organisationId=10,teamId=99,officialName='A'),
        teamB=dict(organisationId=20,teamId=98,officialName='B'),
        competition=dict(gender='Women',officialName='EuroCup Women',season=2024),
        gameDateTimeUTC='2024-01-01T12:00:00Z',teamAScore=80,teamBScore=70,isLive=False,liveGameStatus=999)


def page(rows):
    return '<script>self.__next_f.push('+json.dumps([1,json.dumps(dict(games=rows))])+')</script>'


@pytest.mark.parametrize('field,value',[('gender','Men'),('officialName','EuroCup'),('season',2025)])
def test_fiba_refuses_wrong_competition_gender_or_season(field,value):
    r=row();r['competition'][field]=value
    with pytest.raises(ValueError,match='Wrong competition'):fiba_games(page([r]),'ECW',2024)


def test_fiba_soft404_is_not_a_dataset():
    with pytest.raises(ValueError,match='No structured'):fiba_games('<html>Not found</html>','ECW',2024)


def test_fiba_stable_identity_and_nonfinal_exclusion():
    rows=[row()]
    for change in [dict(gameId=2,isLive=True),dict(gameId=3,liveGameStatus=1),
                   dict(gameId=4,gameDateTimeUTC='2099-01-01T12:00:00'),
                   dict(gameId=5,teamBScore=80),dict(gameId=6,teamBScore=0)]:
        r=row();r.update(change);rows.append(r)
    parsed=fiba_games(page(rows),'ECW',2024)
    games,fixtures,teams=normalize_fiba(parsed,'ECW',2024)
    assert len(games)==1 and len(fixtures)==6
    assert games[0]['ev']=='ECW_10' and set(teams)=={'ECW_10','ECW_20'}
    r=row();r['teamA']['teamId']=12345
    assert normalize_fiba([r],'ECW',2024)[0][0]['ev']=='ECW_10'


def test_female_brno_teams_remain_distinct():
    catalog=json.loads(Path('data/competitions/ECW_teams.json').read_text())
    assert coz('ECW','BK Zabiny Brno',catalog)=='ECW_892'
    assert coz('ECW','KP Brno',catalog)=='ECW_891'
    with pytest.raises(ValueError):coz('ECW','Brno',catalog)


def test_walk_forward_first_day_never_reads_that_day_or_future_scores():
    g=model.load('ECW');seasons=sorted(g.sezon.unique());test=g.sezon==seasons[2]
    first=g.loc[test,'tarih_utc'].min().floor('D')
    original=model.walk_forward('ECW',g)
    changed=g.copy();mask=changed.tarih_utc>=first
    changed.loc[mask,'ev_skor']=150;changed.loc[mask,'dep_skor']=20
    other=model.walk_forward('ECW',changed)
    ids=set(g.loc[test & (g.tarih_utc.dt.floor('D')==first),'mac_id'])
    a=original[original.mac_id.isin(ids)].set_index('mac_id')
    b=other[other.mac_id.isin(ids)].set_index('mac_id')
    assert len(a)>0
    np.testing.assert_allclose(a[['p','margin_prediction','total_prediction']],b.loc[a.index,['p','margin_prediction','total_prediction']])
    with pytest.raises(ValueError,match='mixing'):model.walk_forward('FEC',g)


def test_predict_excludes_same_day_outcomes_and_marks_cold_start(monkeypatch):
    g=model.load('ECW');when='2026-10-22T15:30:00Z'
    a=model.predict('ECW','ECW_66458','ECW_892',when)
    changed=g.copy();changed.loc[changed.tarih_utc>=pd.Timestamp('2026-10-22',tz='UTC'),'ev_skor']=999
    monkeypatch.setattr(model,'load',lambda _:changed)
    b=model.predict('ECW','ECW_66458','ECW_892',when)
    assert a['toplam']==b['toplam'] and a['ev_kazanir']==b['ev_kazanir']
    assert 'ECW_66458' in a['az_veri'] and a['experimental']
    with pytest.raises(ValueError,match='Timezone'):model.predict('ECW','ECW_66458','ECW_892','2026-10-22')


def test_ledger_accepts_future_score_model_with_unknown_overtime(tmp_path):
    from bbtahmin.defter import kaydet
    p=dict(tarih_utc='2099-01-01T12:00:00Z',lig='ECW',ev='ECW_10',dep='ECW_20',
        model=model.SPEC,ev_kazanir=.6,ev_skor=80.,dep_skor=75.,fark=5.,toplam=155.,
        toplam_80=[130.,180.],uzatma=None)
    path=tmp_path/'ledger.csv'
    assert kaydet([p],path)==1
    assert pd.isna(pd.read_csv(path).uzatma.iloc[0])
