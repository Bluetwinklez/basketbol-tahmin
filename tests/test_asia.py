import copy,json
import numpy as np
import pandas as pd
import pytest
from bbtahmin.veri.korea import parse as parse_korea
from bbtahmin.veri.japan import parse_topics
from bbtahmin.veri.philippines import parse as parse_pba


def kbl_fixture():
    season=dict(seasonCode=47,seasonName='2025-2026',glkey='S47G01',gamedateStart='20251003',gamedateEnd='20260408')
    game=dict(seasonCode=47,seasonName1='2025-2026',glkey='S47G01',gmkey='S47G01N1',gameNo=1,
        seasonGrade=1,gameCode='01',gameDate='20251003',gameStart='1900',tcodeH='06',tcodeA='16',
        tnameH='KT',tnameA='DB',tnameFH='KT Sonicboom',tnameFA='DB Promy',isEnded=1,playingQuarter='X',
        scoreH=80,scoreA=75,isStarted=1)
    return season,game


def test_kbl_exact_senior_game_identity_and_final_status():
    season,game=kbl_fixture();d=dict(game,seasonGrade=2);live=dict(game,isEnded=0,playingQuarter='3')
    games,fixtures,aliases,excluded=parse_korea([game,d,live],{47:season},'2026-10-23T00:00Z')
    assert len(games)==1 and games[0]['ev']=='KBL_06' and games[0]['tarih_utc']==pd.Timestamp('2025-10-03T10:00Z')
    assert excluded=={'other_competitions':1,'not_final':1}
    changed=dict(game,gmkey='S48G01N1')
    with pytest.raises(ValueError,match='key conflict'):parse_korea([changed],{47:season},'2026-10-23T00:00Z')


def japan_row(gid='1',round_label='第1節'):
    return f'''<li class="list-item" id="{gid}"><div class="game"><span class="team home"><img src="/logo/ls.png"><span class="team-name">滋賀</span></span>
        <span class="home-score">85</span><span class="away-score">80</span><span class="team away"><img src="/logo/nv.png"><span class="team-name">長崎</span></span></div>
        <div class="info-arena"><span>{round_label}</span><span>Hall</span><span>19:05</span></div><div class="info-scorestate">FINAL</div></li>'''


def test_japanese_all_star_rows_excluded_and_date_carried_between_pages():
    title='<div class="champion-box"><span class="title">2025.10.03(金)</span></div>'
    first=parse_topics([title+japan_row()],2025,1,'2026-10-23T00:00Z')
    assert first[0][0]['ev']=='JP_ls' and first[0][0]['tarih_utc']==pd.Timestamp('2025-10-03T10:05Z')
    second=parse_topics([japan_row('2')],2025,1,'2026-10-23T00:00Z',first[3])
    assert len(second[0])==1
    star=parse_topics(['<div class="champion-box"><span class="title">ALL STAR</span></div>'+japan_row('3','All-Star')],2025,1,'2026-10-23T00:00Z')
    assert not star[0] and star[4]==1
    with pytest.raises(ValueError,match='another season'):parse_topics([title+japan_row()],2024,1,'2026-10-23T00:00Z')
    hachioji=parse_topics([title+japan_row().replace('/logo/ls.png','/logo/hb.png').replace('滋賀','八王子')],2025,2,'2026-10-23T00:00Z')
    assert 'Tokyo Hac' in hachioji[2]['JP_hb']['aliases']
    new_title=title.replace('2025.','2026.')
    modern=japan_row().replace('<span>第1節</span>','<span class="setu-none"></span>')
    assert len(parse_topics([new_title+modern],2026,1,'2026-10-23T00:00Z')[0])==1
    all_star=modern.replace('class="game"','class="game game_ajst"')
    assert not parse_topics([new_title+all_star],2026,1,'2026-10-23T00:00Z')[0]


def test_pba_conference_from_row_not_url_and_away_score_orientation():
    html='''<table><tr><td data-th="Date">Oct 10, 2025</td><td data-th="Opponent">@ <a href="/team/1744/Phoenix">Phoenix</a></td>
    <td data-th="Result"><a href="/international/boxscore/2025-10-10/a/123">W, 78 - 93</a></td>
    <td data-th="Venue">Arena PBA - Philippine Cup</td></tr></table>'''
    rows,n=parse_pba(html,'431',2026,'2026-10-23T00:00Z')
    assert rows[0]['lig']=='PBA_PHI' and rows[0]['ev']=='PBA_1744' and rows[0]['dep']=='PBA_431'
    assert rows[0]['ev_skor']==78 and rows[0]['dep_skor']==93 and rows[0]['tarafsiz_saha']
    with pytest.raises(ValueError,match='W/L'):parse_pba(html.replace('W,','L,'),'431',2026,'2026-10-23T00:00Z')
    assert not parse_pba(html.replace('PBA - Philippine Cup','Friendly'),'431',2026,'2026-10-23T00:00Z')[0]


def test_non_latin_team_names_do_not_collapse_to_empty_key():
    from bbtahmin.takim_ad import anahtar
    assert anahtar('滋賀') and anahtar('滋賀')!=anahtar('長崎')
    assert anahtar('수원 KT')!=anahtar('원주 KT')
    assert anahtar('Fenerbahçe')==anahtar('Fenerbahce')


def synthetic():
    rows=[]
    for season_index in range(3):
        for i in range(170):
            rows.append(dict(mac_id=f'{season_index}_{i}',lig='KBL',sezon=f'{2021+season_index}-{str(2022+season_index)[-2:]}',
                tarih_utc=pd.Timestamp(f'{2021+season_index}-07-02T12:00Z')+pd.Timedelta(days=i),ev='H' if i%2 else 'A',
                dep='A' if i%2 else 'H',ev_skor=70+i%25,dep_skor=72+(i*3)%23,tarafsiz_saha=False))
    return pd.DataFrame(rows)


def test_older_japanese_history_is_explicit_challenger_not_silent_default(tmp_path,monkeypatch):
    from bbtahmin.asia_model import load
    monkeypatch.chdir(tmp_path)
    path=tmp_path/'data/asia';path.mkdir(parents=True)
    g=synthetic();g=g[g.ev_skor!=g.dep_skor].reset_index(drop=True)
    g['lig']='JP_B1';g.loc[0,'sezon']='2016-17'
    g.to_parquet(path/'JP_B1.parquet')
    default=load('JP_B1');expanded=load('JP_B1',expanded_history=True)
    assert len(expanded)==len(default)+1
    assert default.sezon.min()=='2021-22' and expanded.sezon.min()=='2016-17'


def test_successful_empty_schedule_revokes_old_fixtures_but_history_only_keeps_them(tmp_path,monkeypatch):
    from bbtahmin.veri.asia import save
    monkeypatch.chdir(tmp_path)
    row=dict(mac_id='KBL_1',lig='KBL',sezon='2025-26',tarih_utc=pd.Timestamp('2025-10-01T00:00Z'),
             ev='H',dep='A',ev_skor=80,dep_skor=75)
    f=dict(row,mac_id='KBL_F',status='scheduled')
    save('KBL',[row],{}, {},[f])
    path=tmp_path/'data/asia/KBL_fixtures.parquet'
    save('KBL',[row],{}, {},None)
    assert len(pd.read_parquet(path))==1
    save('KBL',[row],{}, {},[])
    assert pd.read_parquet(path).empty


def test_asian_prior_selection_and_calibration_never_use_target_outcomes():
    from bbtahmin.asia_model import fit_fold
    from bbtahmin.ozellik import build_features
    g=synthetic();x=build_features(g);a=fit_fold(g,x,'2023-24')
    changed=g.copy();mask=changed.sezon=='2023-24';changed.loc[mask,['ev_skor','dep_skor']]=[10,200]
    # Keep earlier feature rows; the target labels must never enter training/calibration/selection.
    b=fit_fold(changed,x,'2023-24')
    assert a[2:]==b[2:]
    for name in a[0]:np.testing.assert_array_equal(a[0][name],b[0][name])
    assert a[3]['selection_window_start_utc'][:4]=='2022'
    assert a[3]['calibration_games']+a[3]['selection_games']==170


def test_pba_cross_source_duplicates_and_ambiguous_matches():
    from bbtahmin.veri.asia import cross_source_pba
    g=pd.DataFrame([dict(mac_id='PBA_R1',sezon='2025-26',tarih_utc=pd.Timestamp('2026-10-01T00:00Z'),ev='H',dep='A',ev_skor=80,dep_skor=75),
        dict(mac_id='PBA_SM_x',sezon='2025-26',tarih_utc=pd.Timestamp('2026-10-01T00:00Z'),ev='A',dep='H',ev_skor=75,dep_skor=80)])
    result,links=cross_source_pba(g);assert len(result)==1 and links=={'PBA_SM_x':'PBA_R1'}
    other=g.iloc[:1].copy();other['mac_id']='PBA_R2';other['tarih_utc']=pd.Timestamp('2026-10-02T00:00Z')
    with pytest.raises(ValueError,match='Ambiguous'):cross_source_pba(pd.concat([g,other],ignore_index=True))


def test_pba_publisher_references_and_campaign_do_not_use_july_boundary():
    from bbtahmin.veri.pba_current import parse,resolve
    season=dict(id='pba-gov-cup-50',label="PBA 50th Season Governors' Cup",league='PBA')
    team=lambda name:dict(id=name+'-pba-gov-cup-50',name=name,shortName=name,league='PBA',seasonId='pba-gov-cup-50')
    game=dict(id='game',league='PBA',seasonId='pba-gov-cup-50',homeTeam='$2:props:teams:0',awayTeam='$2:props:teams:1',
              startTime='2026-10-21T09:15:00Z',status='FINAL',homeScore=80,awayScore=75)
    data=['$','div',None,dict(seasons=[season],teams=[team('phoenix'),team('rainorshine')],games=[game])]
    html='<script>self.__next_f.push('+json.dumps([1,'2:'+json.dumps(data)+'\n'])+')</script>'
    games,fixtures,teams,box,rejected=parse(html,'2026-10-23T07:00Z')
    assert len(games)==1 and games[0]['sezon']=='2025-26' and games[0]['date_precision']=='day'
    assert games[0]['ev']=='PBA_1744' and games[0]['dep']=='PBA_938'
    with pytest.raises(ValueError,match='Cyclic'):resolve('$1:x',{'1':{'x':'$1:x'}})


def test_pba_refresh_revokes_previously_accepted_invalid_player_rows(tmp_path,monkeypatch):
    from bbtahmin.veri import pba_current as source
    monkeypatch.chdir(tmp_path);root=tmp_path/'data/asia';root.mkdir(parents=True)
    path=root/'PBA_GOV_player_boxes.parquet'
    pd.DataFrame([dict(mac_id='old',team='bad',player_id='revoked')]).to_parquet(path)
    team=lambda name:dict(id=name+'-pba-gov-cup-50',name=name,shortName=name,league='PBA',seasonId='pba-gov-cup-50')
    def player(pid,pts,fgm,ftm):
        return dict(playerId=pid,pts=pts,fgM=fgm,fgA=fgm,ftM=ftm,ftA=ftm,threeM=0,threeA=0,
                    reb=0,ast=0,stl=0,blk=0,to=0,pf=0,min='30:00')
    game=dict(id='game',league='PBA',seasonId='pba-gov-cup-50',homeTeam=team('phoenix'),awayTeam=team('rainorshine'),
        startTime='2026-10-21T09:15:00Z',status='FINAL',homeScore=80,awayScore=75,
        boxScore=dict(home=[player('valid',80,40,0)],away=[player('invalid',75,30,0)]))
    data=dict(seasons=[dict(id='pba-gov-cup-50',label="PBA 50th Season Governors' Cup",league='PBA')],games=[game])
    html='<script>self.__next_f.push('+json.dumps([1,'2:'+json.dumps(data)+'\n'])+')</script>'
    monkeypatch.setattr(source,'fetch',lambda *a,**k:html)
    monkeypatch.setattr(source,'save',lambda *a,**k:None)
    source.collect()
    rows=pd.read_parquet(path)
    assert rows.player_id.tolist()==['valid']
