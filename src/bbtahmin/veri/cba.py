"""Dated CBA results from public RealGM team schedules; separate archive.

No third-party model code is executed. Dates have day precision; same-day games
are withheld. RealGM's result cell lists HOME score first even on away schedules.
"""
import hashlib
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

BASE='https://basketball.realgm.com'
PREFIX='/international/league/40/Chinese-CBA'
ROOT=Path('data/raw/cba/realgm')


def fetch(path):
    cache=ROOT/(hashlib.sha256(path.encode()).hexdigest()+'.html')
    if not cache.exists():
        with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'User-Agent':'bbtahmin/0.2 research'}),timeout=25) as r:
            raw=r.read(3_000_001)
        if len(raw)>3_000_000:raise ValueError('CBA response too large')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(raw)
    return cache.read_text('utf8')


def parse_schedule(html,team_id,end_year):
    soup=BeautifulSoup(html,'html.parser');rows=[]
    for tr in soup.select('table tr'):
        cells={c.get('data-th'):c for c in tr.select('td[data-th]')}
        if not {'Date','Opponent','Result'}<=cells.keys():continue
        link=cells['Result'].find('a',href=re.compile('/international/boxscore/'))
        if link is None:continue
        match=re.fullmatch(r'([WL]),\s*(\d+)\s*-\s*(\d+)',link.get_text(' ',strip=True))
        opponent=cells['Opponent'].find('a',href=re.compile('/team/'))
        if match is None or opponent is None:continue
        opponent_id=re.search(r'/team/(\d+)/',opponent['href']).group(1)
        away=cells['Opponent'].get_text(' ',strip=True).startswith('@')
        home_id,away_id=(opponent_id,str(team_id)) if away else (str(team_id),opponent_id)
        hs,as_=int(match[2]),int(match[3])
        if hs<=0 or as_<=0 or hs==as_:continue
        # Cross-check the W/L marker to catch reversed score conventions.
        if ((hs>as_) if not away else (as_>hs)) != (match[1]=='W'):
            raise ValueError('Result order disagrees with team win/loss marker')
        date=pd.Timestamp(cells['Date'].get_text(' ',strip=True),tz='UTC')
        if not end_year-1<=date.year<=end_year:raise ValueError('Unexpected schedule season')
        rows.append(dict(mac_id='CBA_R'+link['href'].rsplit('/',1)[-1],lig='CBA',
            sezon=f'{end_year-1}-{str(end_year)[-2:]}',tarih_utc=date.tz_convert('UTC'),
            ev='CBA_'+home_id,dep='CBA_'+away_id,ev_skor=hs,dep_skor=as_,
            regulation_minutes=40 if end_year>=2026 else 48,tarafsiz_saha=False,
            boxscore_path=link['href'],source_url=BASE+link['href'],date_precision='day'))
    return rows


def collect(first=2022,last=2027):
    seed=fetch(PREFIX+'/team/287/Beijing-Shougang/schedule/2026')
    soup=BeautifulSoup(seed,'html.parser')
    teams={}
    for option in soup.select('option[value]'):
        m=re.fullmatch(PREFIX+r'/team/(\d+)/([^/]+)/schedule/2026',option['value'])
        if m:teams[m[1]]=dict(name=option.get_text(strip=True),slug=m[2])
    if len(teams)<18:raise ValueError('CBA team catalog incomplete')
    tasks=[(team,year) for year in range(first,last+1) for team in teams]
    errors=[];all_rows=[]
    def one(task):
        team,year=task;path=PREFIX+f'/team/{team}/{teams[team]["slug"]}/schedule/{year}'
        try:return parse_schedule(fetch(path),team,year),None
        except Exception as e:return [],dict(team=team,year=year,error=f'{type(e).__name__}: {e}')
    with ThreadPoolExecutor(max_workers=2) as pool:
        for rows,error in pool.map(one,tasks):
            all_rows.extend(rows)
            if error:errors.append(error)
    g=pd.DataFrame(all_rows)
    if g.empty:raise ValueError('No dated CBA results collected')
    fields=['ev','dep','ev_skor','dep_skor','tarih_utc','sezon']
    for _,part in g.groupby('mac_id'):
        if len(part[fields].drop_duplicates())!=1:raise ValueError('Conflicting CBA result copies')
    g=g.drop_duplicates('mac_id').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    now=pd.Timestamp.now(tz='UTC');g=g[g.tarih_utc<now.floor('D')]
    destination=Path('data/cba_games.parquet')
    if destination.exists():
        old=pd.read_parquet(destination)
        combined=pd.concat([old,g],ignore_index=True)
        for _,part in combined.groupby('mac_id'):
            if len(part[fields].drop_duplicates())!=1:raise ValueError('CBA refresh conflicts with persisted result')
        g=combined.drop_duplicates('mac_id').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    temporary=destination.with_suffix('.part');g.to_parquet(temporary,index=False);temporary.replace(destination)
    catalog={'CBA_'+k:dict(v,aliases=[]) for k,v in teams.items()}
    aliases={'372':['Jilin','Jilin N.T.','Jilin Northeast Tigers'],
             '742':['Xinjiang','Xinjiang F.T.','Xinjiang Flying Tigers'],
             '287':['Beijing','Beijing D.','Beijing Ducks'],
             '93':['Shenzhen','Shenzhen Leopards']}
    for k,v in aliases.items():catalog['CBA_'+k]['aliases']=v
    Path('data/cba_teams.json').write_text(json.dumps(catalog,indent=2),'utf8')
    report=dict(captured_at_utc=now.isoformat(),games=len(g),teams=len(teams),
        seasons=g.groupby('sezon').size().to_dict(),errors=errors,
        source='Public RealGM team schedule numeric facts; not a supported developer API',
        date_precision='day; same-day results excluded',
        regulation_minutes='48 through 2024-25; 40 from 2025-26; explicit live override required when uncertain')
    Path('docs/kanit/cba').mkdir(parents=True,exist_ok=True)
    Path('docs/kanit/cba/collection.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
    return g


if __name__=='__main__':collect()
