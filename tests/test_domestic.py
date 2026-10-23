import io

import pandas as pd
import pytest
from openpyxl import Workbook

from bbtahmin.veri.turkey import historical, team_dates, fixtures
from bbtahmin.veri.ukraine import parse_export


def export(rows, title='SuperLeague'):
    book = Workbook(); sheet = book.active
    sheet.append([title, '2026-2027'])
    sheet.append(['id','weekday','date','time','home team','away team','arena','score'])
    for row in rows: sheet.append(row)
    output = io.BytesIO(); book.save(output)
    return output.getvalue()


def test_ukraine_same_number_reverse_games_and_dst_are_distinct():
    rows = [[26,None,'23/10/2026','18:00:00','A','B','Arena','91-82'],
            [26,None,'24/10/2026','18:00:00','B','A','Arena','82-91']]
    finals, _ = parse_export(export(rows),2026,{'A':'UKR_1','B':'UKR_2'},'2026-10-25T00:01Z','official')
    assert len(finals)==2 and finals[0]['mac_id']!=finals[1]['mac_id']
    assert finals[0]['tarih_utc']==pd.Timestamp('2026-10-23T15:00Z')
    assert not parse_export(export(rows[:1]),2026,{'A':'UKR_1','B':'UKR_2'},'2026-10-23T20:00Z','official')[0]
    with pytest.raises(ValueError,match='Duplicate'):
        parse_export(export(rows[:1]*2),2026,{'A':'UKR_1','B':'UKR_2'},'2026-10-25T00:01Z','official')
    with pytest.raises(ValueError,match='Wrong FBU'):
        parse_export(export(rows,'Women'),2026,{'A':'UKR_1','B':'UKR_2'},'2026-10-25T00:01Z','official')


def test_ukraine_live_score_in_schedule_never_becomes_final():
    rows=[[26,None,'24/10/2026','18:00:00','A','B','Arena','12-9']]
    finals, games=parse_export(export(rows),2026,{'A':'UKR_1','B':'UKR_2'},'2026-10-23T00:01Z','official',scheduled=True)
    assert not finals and games[0]['status']=='unverified'


def test_turkey_regular_season_requires_crosschecked_team_date():
    html="""<title>2025-26</title><table class="gday"><tr><td>A</td><td><a onclick="go('game/7')">80 - 88</a></td><td>B</td></tr></table>"""
    teams={'a':('TR_BSL_1','A'),'b':('TR_BSL_2','B')}
    assert not historical(html,2025,teams,'2026-10-23T00:00Z','public')
    page="""<title>2025-26</title><table><tr><td>NS 01</td><td>27.09.2025</td><td><a onclick="go('game/7')">80 - 88</a></td><td>leader</td></tr></table>"""
    dates=team_dates(page,2025)
    rows=historical(html,2025,teams,'2026-10-23T00:00Z','public',dates)
    assert len(rows)==1 and rows[0]['date_precision']=='day' and rows[0]['ev_skor']==80
    with pytest.raises(ValueError,match='season'):
        team_dates(page.replace('2025-26','2024-25'),2025)


def test_turkey_unknown_provider_team_is_not_guessed():
    payload={'data':[dict(league={'id':393,'sportId':23},homeTeam={'id':12998},awayTeam={'id':10822})]}
    with pytest.raises(ValueError,match='Unverified'):
        fixtures(payload,2026,'2026-10-23T00:00Z')


@pytest.mark.parametrize('code',['UKR','TR_BSL'])
def test_domestic_predictions_use_separate_regional_route(code,monkeypatch):
    from bbtahmin import regional_model
    from bbtahmin.tahmin import _tahmin_et
    from bbtahmin.daily import LEAGUES
    monkeypatch.setattr(regional_model,'predict',lambda *args:dict(route=args))
    assert _tahmin_et(code,[(code+'_1',code+'_2')],'2026-10-24T15:00Z')[0]['route'][0]==code
    assert code in LEAGUES


def test_turkey_current_source_failure_preserves_archive_and_is_visible(tmp_path,monkeypatch):
    from bbtahmin.veri import turkey
    import json
    monkeypatch.chdir(tmp_path)
    root=tmp_path/'data/competitions';root.mkdir(parents=True)
    row=dict(mac_id='TR_BSL_T7',lig='TR_BSL',sezon='2025-26',tarih_utc=pd.Timestamp('2026-01-01T00:00Z'),
             ev='TR_BSL_1',dep='TR_BSL_2',ev_skor=80,dep_skor=75)
    pd.DataFrame([row]).to_parquet(root/'TR_BSL.parquet')
    fixture=root/'TR_BSL_fixtures.parquet';fixture.write_bytes(b'previous fixture snapshot')
    def unavailable(*args,**kwargs): raise ValueError('Missing beIN fixture data')
    monkeypatch.setattr(turkey,'fetch',unavailable)
    result=turkey.collect(first=2026,last=2026)
    assert result.mac_id.tolist()==['TR_BSL_T7']
    assert fixture.read_bytes()==b'previous fixture snapshot'
    report=json.loads((tmp_path/'docs/kanit/competitions/TR_BSL_collection.json').read_text())
    assert report['errors'][0]['retained_previous_snapshot']
