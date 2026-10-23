"""Dated senior-women Girona cohort from the FEB's own public widget backend.

Public browser token stays in memory. Only numeric match facts are retained;
calendar round dates are never substituted for actual tipoff dates.
"""
import hashlib,json,re,time,urllib.request,urllib.error
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from .regional import save

CALENDAR='https://baloncestoenvivo.feb.es/calendario.aspx?g=4&t={year}'
API='https://intrafeb.feb.es/LiveStats.API/api/v1/TeamStats/'
JWT=r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'


def selected_games(html):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for tr in soup.select('tr'):
        home=tr.select_one('.equipo.local a');away=tr.select_one('.equipo.visitante a');link=tr.select_one('.resultado a[href]')
        if home is None or away is None or link is None:continue
        names=[home.get_text(' ',strip=True),away.get_text(' ',strip=True)]
        if 'SPAR GIRONA' not in names:continue
        score=re.fullmatch(r'(\d+)-(\d+)',link.get_text(strip=True));game=re.search(r'[?&]p=(\d+)',link['href'])
        if not score or not game:continue
        ids=[re.search(r'[?&]i=(\d+)',x['href'])[1] for x in [home,away]]
        rows.append(dict(id=game[1],home_id=ids[0],away_id=ids[1],home_score=int(score[1]),away_score=int(score[2])))
    return rows


def normalize(payload,expected,year,url,captured):
    h=payload.get('HEADER') or {}
    if str(h.get('CompID'))!='210':raise ValueError('Not senior Liga Femenina Endesa')
    if h.get('status') not in ('3',3,None) or h.get('statusText') not in ('FINISHED',None) or h.get('time')!='FINAL':raise ValueError('Not a confirmed final')
    teams=h.get('TEAM',[])
    if len(teams)!=2 or [str(t.get('id')) for t in teams]!=[expected['home_id'],expected['away_id']]:raise ValueError('FEB/calendar side mismatch')
    scores=[int(t['pts']) for t in teams]
    if scores!=[expected['home_score'],expected['away_score']] or min(scores)<=0 or scores[0]==scores[1]:raise ValueError('Conflicting or invalid final scores')
    when=pd.Timestamp(pd.to_datetime(h['starttime'],format='%d-%m-%Y - %H:%M')).tz_localize('Europe/Madrid').tz_convert('UTC')
    if not year<=when.year<=year+1 or when>=pd.Timestamp(captured):raise ValueError('Wrong season or future result')
    girona=lambda t:t.get('name')=='SPAR GIRONA' and str(t.get('clubCode')) in ('170277','170315')
    identity=lambda t:'ECW_65758' if girona(t) else 'ES_W_'+str(t['clubCode'])
    if not any(girona(t) for t in teams):raise ValueError('Unknown Girona organisation')
    if any(not re.fullmatch(r'\d{6}',str(t.get('clubCode',''))) for t in teams):raise ValueError('Missing stable club identity')
    quarters=(h.get('QUARTERS') or {}).get('QUARTER') or []
    hs=[int(q['scoreA']) for q in quarters];ds=[int(q['scoreB']) for q in quarters]
    if len(hs)<4 or sum(hs)!=scores[0] or sum(ds)!=scores[1]:raise ValueError('Per-period/final score conflict')
    return dict(mac_id='ES_W_FEB_'+expected['id'],lig='ES_W_LFE',sezon=f'{year}-{str(year+1)[-2:]}',
        tarih_utc=when,ev=identity(teams[0]),dep=identity(teams[1]),ev_skor=scores[0],dep_skor=scores[1],
        home_name=teams[0]['name'],away_name=teams[1]['name'],gender='Women',tarafsiz_saha=False,regulation_minutes=40,
        source_home_club_code=teams[0]['clubCode'],source_away_club_code=teams[1]['clubCode'],legacy_status_missing=h.get('status') is None,
        home_quarters=hs,away_quarters=ds,regulation_home=sum(hs[:4]),regulation_away=sum(ds[:4]),overtime=len(hs)>4,
        source_url=url,listing_url=CALENDAR.format(year=year),captured_at_utc=captured,available_at_utc=None,
        date_precision='timestamp',venue_name=h.get('field'),neutral_venue_verified=False)


def collect(years=(2022,2023,2024,2025,2026)):
    rows=[];counts=[];sources=[];rejected=[];captured=pd.Timestamp.now(tz='UTC').isoformat();last=0.
    cache=Path('data/raw/expansion/feb_facts');cache.mkdir(parents=True,exist_ok=True)
    for year in years:
        url=CALENDAR.format(year=year)
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BBTahminResearch/0.4'}),timeout=25) as r:html=r.read().decode('utf8')
        match=re.search(JWT,html)
        if not match:raise ValueError('Published public-widget token unavailable')
        token=match[0];games=selected_games(html);before=len(rows)
        if not games:raise ValueError('No finished Girona fixtures for requested season')
        for game in games:
            endpoint=API+game['id'];path=cache/(game['id']+'.json')
            if path.exists():payload=json.loads(path.read_text())
            else:
                time.sleep(max(0.,1.1-(time.monotonic()-last)))
                with urllib.request.urlopen(urllib.request.Request(endpoint,headers={'Authorization':'Bearer '+token,'User-Agent':'BBTahminResearch/0.4'}),timeout=25) as r:payload=json.load(r)
                last=time.monotonic()
                # Sanitize cached header: no public token, referees, or non-match administrative data.
                header=payload.get('HEADER') or {}
                fields=['CompID','competition','time','starttime','field','status','statusText','TEAM','QUARTERS']
                payload={'HEADER':{k:header.get(k) for k in fields}}
                path.write_text(json.dumps(payload))
            try:rows.append(normalize(payload,game,year,endpoint,captured))
            except ValueError as error:
                rejected.append(dict(game_id=game['id'],season=year,source_url=endpoint,reason=str(error)))
        counts.append(dict(year=year,listed=len(games),accepted=len(rows)-before));sources.append(url)
        save('GIRONA_LFE',rows,dict(source='Federación Española de Baloncesto',sources=sources,captured_at_utc=captured,
            counts=counts,rejected=rejected,coverage='Girona regular-calendar cohort only, not complete Spanish league history. Only matching final widget/calendar scores accepted; rejected stale/conflicting widget rows retained in this report. Actual widget tipoffs and quarter totals checked. Historical publication time and neutral venues unknown. Public session token is not stored.'))
        print('Girona',year,len(rows)-before,flush=True)
    return rows

if __name__=='__main__':collect()
