"""Separate, gender-checked ECW/FEC/VTB archives from public result pages."""
import hashlib
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path('data/raw/expansion')
FIBA={'ELW':('euroleague-women','Women','EuroLeague Women',211,208762),
      'ECW':('eurocup-women','Women','EuroCup Women',165,208763),
      'FEC':('fiba-europe-cup','Men','FIBA Europe Cup',212,208765)}


def fetch(url,refresh=False):
    path=ROOT/(hashlib.sha256(url.encode()).hexdigest()+'.html')
    if refresh or not path.exists():
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'bbtahmin/0.3 research'}),timeout=25) as r:
            raw=r.read(6_000_001)
        if len(raw)>6_000_000:raise ValueError('Response exceeds limit')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return path.read_text('utf8')


def fiba_games(html,code,year):
    """Read server-rendered public page data; no private API or browser code."""
    text=''
    for script in BeautifulSoup(html,'html.parser').select('script'):
        raw=script.get_text()
        if raw.startswith('self.__next_f.push('):
            try:
                value=json.loads(raw[len('self.__next_f.push('):-1])
                if value[0]==1:text+=value[1]
            except (ValueError,IndexError,TypeError):continue
    candidates=[]
    for match in re.finditer(r'"games"\s*:',text):
        try:
            rows,_=json.JSONDecoder().raw_decode(text[match.end():].lstrip())
        except ValueError:continue
        if isinstance(rows,list) and rows and isinstance(rows[0],dict) and 'teamA' in rows[0]:
            candidates.append(rows)
    if not candidates:raise ValueError('No structured competition games on this page')
    rows=max(candidates,key=len)
    for row in rows:
        comp=row.get('competition',{})
        if comp.get('gender')!=FIBA[code][1] or comp.get('officialName')!=FIBA[code][2] or comp.get('season')!=year:
            raise ValueError('Wrong competition, gender or season; refusing page fallback')
    return rows


def normalize_fiba(rows,code,year):
    records=[];fixtures=[];teams={};now=pd.Timestamp.now(tz='UTC')
    for row in rows:
        a,b=row.get('teamA'),row.get('teamB')
        if not a or not b or not a.get('organisationId') or not b.get('organisationId'):continue
        for t in [a,b]:
            key=f'{code}_{t["organisationId"]}'
            entry=teams.setdefault(key,dict(name=t['officialName'],aliases=[]))
            entry['aliases']=sorted(set(entry['aliases']+[t.get('shortName',''),t.get('code','')])-{''})
        h,d=f'{code}_{a["organisationId"]}',f'{code}_{b["organisationId"]}'
        if h==d:raise ValueError('Same organisation on both sides')
        when=pd.Timestamp(row['gameDateTimeUTC'])
        when=when.tz_localize('UTC') if when.tzinfo is None else when.tz_convert('UTC')
        base=dict(mac_id=f'{code}_F{row["gameId"]}',lig=code,sezon=f'{year-1}-{str(year)[-2:]}',
                  tarih_utc=when,ev=h,dep=d,regulation_minutes=40,tarafsiz_saha=False,
                  source='fiba-public-page',date_precision='timestamp')
        fixtures.append(base)
        hs,ds=row.get('teamAScore'),row.get('teamBScore')
        if (row.get('liveGameStatus')!=999 or row.get('isLive') or when>=now
                or not isinstance(hs,(int,float)) or not isinstance(ds,(int,float))
                or min(hs,ds)<=0 or hs==ds):continue
        records.append(dict(base,ev_skor=int(hs),dep_skor=int(ds)))
    return records,fixtures,teams


def save(code,records,fixtures,teams,sources,errors):
    root=Path('data/competitions');root.mkdir(parents=True,exist_ok=True)
    g=pd.DataFrame(records)
    path=root/f'{code}.parquet'
    if g.empty and path.exists():g=pd.read_parquet(path)
    if g.empty:raise ValueError(f'No finished {code} games')
    if path.exists():g=pd.concat([pd.read_parquet(path),g],ignore_index=True)
    fields=['lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor']
    for _,part in g.groupby('mac_id'):
        if len(part[fields].drop_duplicates())!=1:raise ValueError('Conflicting persisted competition results')
    if code == 'TR_BSL':
        from ..archive_checks import reconcile_results
        g=reconcile_results(g)
    g=g.drop_duplicates('mac_id',keep='last').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    temp=path.with_suffix('.part');g.to_parquet(temp,index=False);temp.replace(path)
    catalog=root/f'{code}_teams.json'
    previous=json.loads(catalog.read_text()) if catalog.exists() else {}
    for key,entry in teams.items():
        old=previous.get(key,{})
        entry['aliases']=sorted(set(entry.get('aliases',[])+old.get('aliases',[])+([old['name']] if old.get('name') else [])))
        previous[key]=entry
    teams=previous
    catalog.write_text(json.dumps(teams,ensure_ascii=False,indent=2))
    if fixtures:pd.DataFrame(fixtures).drop_duplicates('mac_id').to_parquet(root/f'{code}_fixtures.parquet',index=False)
    evidence=Path('docs/kanit/competitions');evidence.mkdir(parents=True,exist_ok=True)
    report=dict(timestamp_utc=pd.Timestamp.now(tz='UTC').isoformat(),league=code,games=len(g),
        teams=len(teams),seasons=g.groupby('sezon').size().to_dict(),sources=sources,errors=errors,
        gender=FIBA[code][1] if code in FIBA else 'Men',
        coverage=('Current-team cohort schedules; historical games between departed teams may be absent.' if code=='VTB' else 'Finished non-tied games with positive scores from public pages; not a completeness guarantee. Aggregate-leg ties and unplayed games excluded.'),
        note='Normalized numeric facts from public pages; no supported developer API contract. Nominal home/away, neutral venues not independently verified.')
    (evidence/f'{code}_collection.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
    return g


def collect_fiba(code):
    slug,gender,name,marketing,old=FIBA[code];records=[];fixtures=[];teams={};sources=[]
    for year in [2024,2025,2026,2027]:
        url=(f'https://www.fiba.basketball/en/history/{marketing}-fiba-'
             f'{"womens" if gender=="Women" else "mens"}-european-club-competitions-tier-{1 if code=='ELW' else 2}/{old}/games') if year==2024 else f'https://www.fiba.basketball/en/events/{slug}-{year-2001:02d}-{year-2000:02d}/games'
        # Reuse a previously downloaded exact source page where available.
        local=ROOT/f'{code}_2024_history.html' if year==2024 else ROOT/f'{code}_{year}.html'
        current=pd.Timestamp.now(tz='UTC');active=current.year+(current.month>=7)
        html=local.read_text() if local.exists() and year<active else fetch(url,refresh=year>=active)
        rows=fiba_games(html,code,year);r,f,t=normalize_fiba(rows,code,year)
        captured=pd.Timestamp.now(tz='UTC').isoformat()
        for row in r+f:
            row.update(captured_at_utc=captured,source_url=url)
        final_ids={row['mac_id'] for row in r}
        for row in f:
            row['status']='final' if row['mac_id'] in final_ids else ('scheduled' if row['tarih_utc']>pd.Timestamp.now(tz='UTC') else 'unverified')
        records+=r;fixtures+=f;sources.append(url)
        for key,entry in t.items():
            previous=teams.setdefault(key,entry)
            previous['aliases']=sorted(set(previous['aliases']+entry['aliases']+[entry['name']]))
    return save(code,records,fixtures,teams,sources,[])


def collect_vtb():
    from .cba import parse_schedule
    prefix='/international/league/35/VTB-United-League';base='https://basketball.realgm.com'
    tasks=[];teams={};sources=[]
    for year in [2024,2025,2026,2027]:
        url=base+prefix+'/teams';sources.append(url)
        soup=BeautifulSoup(fetch(url),'html.parser')
        found={}
        for link in soup.select('table a[href]'):
            m=re.fullmatch(prefix+r'/team/(\d+)/([^/]+)/schedule(?:/\d+)?',link['href'])
            if m:found[m[1]]=m[2]
        if len(found)<8:raise ValueError('Incomplete VTB team catalog')
        for team,slug in found.items():
            teams['VTB_'+team]=dict(name=slug.replace('-',' '),aliases=[])
            tasks.append((team,year,base+prefix+f'/team/{team}/{slug}/schedule/{year}'))
    errors=[];records=[]
    def one(task):
        team,year,url=task
        try:
            current=pd.Timestamp.now(tz='UTC');active=current.year+(current.month>=7)
            soup=BeautifulSoup(fetch(url,refresh=year>=active),'html.parser')
            for tr in soup.select('table tr'):
                venue=tr.select_one('td[data-th="Venue"]')
                if venue is not None and 'VTB United League' not in venue.get_text(' ',strip=True):tr.decompose()
            rows=parse_schedule(str(soup),team,year)
            for r in rows:
                r.update(mac_id=r['mac_id'].replace('CBA_','VTB_',1),lig='VTB',
                         ev=r['ev'].replace('CBA_','VTB_',1),dep=r['dep'].replace('CBA_','VTB_',1),regulation_minutes=40)
            return rows,None
        except Exception as e:return [],dict(team=team,year=year,error=str(e))
    with ThreadPoolExecutor(max_workers=2) as pool:
        for rows,error in pool.map(one,tasks):
            records+=rows
            if error:errors.append(error)
    cutoff=pd.Timestamp.now(tz='UTC').floor('D')
    records=[r for r in records if r['tarih_utc']<cutoff]
    return save('VTB',records,[],teams,list(dict.fromkeys(sources)),errors)


def collect(codes=('ECW','FEC','VTB')):
    for code in codes:
        collect_vtb() if code=='VTB' else collect_fiba(code)


if __name__=='__main__':collect()

