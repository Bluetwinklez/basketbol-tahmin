import copy
import json
import pandas as pd
import pytest
from bbtahmin.veri.finland import competition, parse
from bbtahmin.veri.spain import normalize


def test_finnish_senior_identity_and_series_totals_are_not_games():
    with pytest.raises(ValueError):
        competition([dict(name='Naisten Korisliiga', gender='FEMALE', age_group_code='U18')])
    game=dict(game_public_id='g', status='CONFIRMED', time='2025-10-01T15:00:00Z',
              score_a=80, score_b=70, team_a_name_fi='HBA-Märsky', team_b_name_fi='ToPo')
    series=dict(game, game_public_id='series', time=None, score_a=3, score_b=0)
    future=dict(game, game_public_id='future', time='2026-11-01T15:00:00Z')
    payload=dict(competition_public_id='c', season_public_id='s', count=3, games=[game,series,future])
    rows, excluded=parse(payload,'c','s',2025,'https://example.org','2026-10-23T00:00:00Z')
    assert len(rows)==1 and excluded==2 and rows[0]['ev']=='ECW_66458'
    assert rows[0]['ev_skor']==80 and rows[0]['tarih_utc']==pd.Timestamp(game['time'])
    payload['count']=4
    with pytest.raises(ValueError,match='incomplete'):parse(payload,'c','s',2025,'https://example.org','2026-10-23T00:00:00Z')


def feb_game():
    expected=dict(id='1',home_id='h',away_id='a',home_score=80,away_score=60)
    header=dict(CompID='210',time='FINAL',starttime='05-10-2022 - 18:30',status=None,statusText=None,
                TEAM=[dict(id='h',name='SPAR GIRONA',clubCode='170277',pts='80'),dict(id='a',name='Away',clubCode='123456',pts='60')],
                QUARTERS=dict(QUARTER=[dict(scoreA='20',scoreB='15') for _ in range(4)]))
    return dict(HEADER=header),expected


def test_feb_actual_tipoff_legacy_final_and_club_alias():
    payload, expected=feb_game()
    row=normalize(payload,expected,2022,'https://example.org','2026-10-23T00:00:00Z')
    assert row['ev']=='ECW_65758' and row['tarih_utc']==pd.Timestamp('2022-10-05T16:30:00Z')
    assert row['legacy_status_missing'] and row['regulation_home']==80
    payload['HEADER']['TEAM'][0]['clubCode']='170315'
    assert normalize(payload,expected,2022,'https://example.org','2026-10-23T00:00:00Z')['ev']=='ECW_65758'


@pytest.mark.parametrize('change',['team','score','period','clock','competition','club'])
def test_feb_conflicting_evidence_is_rejected(change):
    payload, expected=feb_game();h=payload['HEADER']
    if change=='team':h['TEAM'].reverse()
    elif change=='score':expected['home_score']=81
    elif change=='period':h['QUARTERS']['QUARTER'][0]['scoreA']='21'
    elif change=='clock':h['time']='05:00'
    elif change=='competition':h['CompID']='U18'
    elif change=='club':h['TEAM'][0]['clubCode']='999999'
    with pytest.raises(ValueError):normalize(payload,expected,2022,'https://example.org','2026-10-23T00:00:00Z')


def test_new_forecast_provenance_includes_side_datasets(tmp_path,monkeypatch):
    from bbtahmin.prospective import dataset_hashes
    monkeypatch.chdir(tmp_path)
    p=tmp_path/'data/domestic/new.parquet';p.parent.mkdir(parents=True);p.write_bytes(b'a')
    first=dataset_hashes();p.write_bytes(b'b');second=dataset_hashes()
    assert 'data/domestic/new.parquet' in first and first!=second
