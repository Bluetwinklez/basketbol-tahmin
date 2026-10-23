import copy,json
import numpy as np
import pandas as pd
import pytest
from bbtahmin.player_context import injuries_asof,rotation
from bbtahmin.veri.regional import parse_bg
from bbtahmin.veri.slovenia import parse as parse_si,validate_competition
from bbtahmin.live_feed import parse,parse_espn


def test_injury_dates_propagate_but_default_parser_schema_stays_compatible():
    from bbtahmin.veri.sakatlik import ayristir
    text='10/23/2026 07:00(ET) ATL@ORL AtlantaHawks A,B Out Injury\nOrlandoMagic C,D Questionable Illness'
    old=ayristir(text);new=ayristir(text,include_dates=True)
    assert 'game_date' not in old and set(new.game_date)=={'2026-10-23'}


def test_injury_capture_time_fixture_date_and_publication_all_required():
    r=dict(published_at_utc='2026-10-22T15:00:00Z',captured_at_utc='2026-10-22T16:00:00Z',
        records=[dict(mac='ATL@ORL',game_date='2026-10-23',takim='ATL',oyuncu='A,B',durum='Out')])
    assert not injuries_asof([r],'ATL','ORL','2026-10-23T23:00:00Z','2026-10-22T15:30:00Z')['known']
    assert injuries_asof([r],'ATL','ORL','2026-10-23T23:00:00Z','2026-10-22T17:00:00Z')['known']
    assert not injuries_asof([r],'ATL','ORL','2026-10-24T23:00:00Z','2026-10-22T17:00:00Z')['known']
    assert not injuries_asof([r],'ATL','ORL','2026-10-23T23:00:00Z','2026-10-25T17:00:00Z')['known']


def test_lagged_rotation_never_reads_target_appearances_or_forces_240_minutes():
    rows=[dict(mac_id='g',takim='H',oyuncu_id=1,tarih_utc=pd.Timestamp('2026-10-21T12:00:00Z'),dakika=20.,pm=3.),
          dict(mac_id='q',takim='H',oyuncu_id=2,tarih_utc=pd.Timestamp('2026-10-22T01:00:00Z'),dakika=40.,pm=30.)]
    h=pd.DataFrame(rows);a=rotation(h,'H','2026-10-22T20:00:00Z')
    assert len(a['players'])==1 and a['players'][0]['expected_minutes']==pytest.approx(20)
    h.loc[1,'dakika']=1;h.loc[1,'pm']=-100
    assert a==rotation(h,'H','2026-10-22T20:00:00Z')
    assert not rotation(h,'UNKNOWN','2026-10-22T20:00:00Z')['known']


def test_bulgarian_namespace_home_away_and_friendly_exclusion():
    row='''<div class="tr"><div class="home"><div class="td_name">Монтана 2003</div><div class="td_score">80</div></div>
    <div class="away"><div class="td_name">B</div><div class="td_score">70</div></div><span class="date">01-11-2025 <span>18:00</span></span>
    <div class="champ">А група Жени | Редовен сезон</div><a href="game-123">Info</a></div>'''
    html='<select id="champ_id"><option>А група Жени</option></select><div class="tbl_games">'+row+'</div>'
    rows,n=parse_bg(html,2025,'https://example.org','2026-10-22T21:00:00Z')
    assert len(rows)==1 and rows[0]['ev']=='ECW_813' and rows[0]['ev_skor']==80
    rows,n=parse_bg(html.replace('А група Жени |','Контролни срещи |'),2025,'https://example.org','2026-10-22T21:00:00Z')
    assert not rows and n==1


def competition():return dict(id=1,name='1. Ž SKL',gender='FEMALE',category='ABSOLUTE',rank='FIRST',type='LEAGUE',season=dict(id=26,name='2025/2026'))


def test_slovenia_senior_gender_season_and_no_admin_metadata():
    c=competition();r=dict(id=10,competitions=[dict(competitionId=1,seasonId=26)],status='FINISHED',
        firstTeamName='Cinkarna Celje',secondTeamName='Triglav',firstTeamScore=90,secondTeamScore=60,
        dateTime='2025-11-01T18:00:00Z',referee1=dict(person=dict(email='not-retained')))
    rows=parse_si([r],c,2025,'https://example.org','2026-10-22T21:00:00Z')
    assert rows[0]['ev']=='ECW_58477' and 'referee1' not in rows[0]
    for key,value in [('gender','MALE'),('category','U18'),('name','Cup')]:
        changed=copy.deepcopy(c);changed[key]=value
        with pytest.raises(ValueError):validate_competition(changed,2025)
    r['status']='IN_PROGRESS';assert not parse_si([r],c,2025,'https://example.org','2026-10-22T21:00:00Z')


def test_nba_live_naive_source_time_is_not_falsely_certified_fresh():
    p=dict(meta=dict(time='2026-10-22 21:00:00'),scoreboard=dict(games=[dict(gameId='g',gameStatus=2,period=2,
        gameClock='PT05M30.00S',gameTimeUTC='2026-10-22T20:00:00Z',homeTeam=dict(teamTricode='BKN',score=40),awayTeam=dict(teamTricode='PHX',score=35))]))
    rows=parse(p,'2026-10-22T21:00:10Z')
    assert rows[0]['home']=='BRK' and rows[0]['remaining_seconds']==330 and not rows[0]['source_freshness_verified']
    p['scoreboard']['games'][0]['gameClock']='PT99M00S'
    with pytest.raises(ValueError):parse(p,'2026-10-22T21:00:10Z')


def test_espn_only_live_states_and_no_source_freshness_guess():
    p=dict(leagues=[dict(abbreviation='NBA')],events=[dict(id='e',date='2026-10-22T20:00:00Z',competitions=[dict(
        status=dict(type=dict(state='in'),period=3,displayClock='04:25'),competitors=[
        dict(homeAway='home',score='70',team=dict(abbreviation='BKN')),dict(homeAway='away',score='68',team=dict(abbreviation='PHX'))])])])
    rows=parse_espn(p,'2026-10-22T21:00:00Z');assert rows[0]['home']=='BRK' and rows[0]['remaining_seconds']==265
    assert not rows[0]['source_freshness_verified'] and not rows[0]['used_for_prediction']
    p['events'][0]['competitions'][0]['status']['type']['state']='post';assert not parse_espn(p,'2026-10-22T21:00:00Z')


def test_hierarchical_map_rejects_men_and_future_score_mutations():
    from bbtahmin.hierarchical import fit_predict,observations
    g=pd.DataFrame([dict(mac_id=str(i),lig='ECW',sezon='2025-26',ev='H',dep='A',
        tarih_utc=pd.Timestamp('2025-01-01T12:00:00Z')+pd.Timedelta(days=i),ev_skor=80+i%8,dep_skor=75+i%7,tarafsiz_saha=False) for i in range(180)])
    q=g.tail(1).copy();a=fit_predict(g,q,'2025-06-15T00:00:00Z',{})
    changed=g.copy();changed.loc[changed.tarih_utc>=pd.Timestamp('2025-06-15T00:00:00Z'),['ev_skor','dep_skor']]=[10,200]
    np.testing.assert_allclose(a,fit_predict(changed,q,'2025-06-15T00:00:00Z',{}))
    with pytest.raises(ValueError,match='senior-women'):observations(g.assign(lig='FEC'))
