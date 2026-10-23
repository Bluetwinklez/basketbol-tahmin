"""Additional official federation results and public club schedule facts."""
import hashlib,json,re,time,urllib.request
from pathlib import Path
from urllib.parse import urlencode
import pandas as pd
from bs4 import BeautifulSoup
from .competitions import fetch

BG='https://comps.basketball.bg/games.inc.php'


def key(prefix,name):return prefix+hashlib.sha256(name.encode()).hexdigest()[:16]


def parse_bg(html,year,url,captured):
    soup=BeautifulSoup(html,'html.parser');rows=[];excluded=0
    choices=soup.select('select#champ_id option')
    if not any('а група' in o.get_text().lower() and 'жени' in o.get_text().lower() for o in choices):raise ValueError('Wrong Bulgarian competition/category')
    for tr in soup.select('.tbl_games > .tr'):
        comp=tr.select_one('.champ');label=comp.get_text(' ',strip=True) if comp else ''
        if not (label.lower().startswith('а група жени') or label.lower().startswith('жени - а група')):excluded+=1;continue
        h,a=tr.select_one('.home'),tr.select_one('.away');date=tr.select_one('.date')
        if h is None or a is None or date is None:raise ValueError('Changed official Bulgarian row')
        names=[x.select_one('.td_name').get_text(' ',strip=True) for x in (h,a)]
        scores=[x.select_one('.td_score').get_text(strip=True) for x in (h,a)]
        if not all(re.fullmatch(r'\d+',s) for s in scores):raise ValueError('Unfinished result in official results response')
        hs,ds=map(int,scores)
        m=re.fullmatch(r'(\d\d)-(\d\d)-(\d{4})\s+(\d\d:\d\d)',date.get_text(' ',strip=True))
        link=tr.select_one('a[href^="game-"]')
        if not m or link is None:raise ValueError('Missing final identity/time')
        when=pd.Timestamp(f'{m[3]}-{m[2]}-{m[1]} {m[4]}',tz='Europe/Sofia').tz_convert('UTC')
        if not year<=when.year<=year+1:raise ValueError('Wrong season response')
        if min(hs,ds)<=0 or hs==ds or when>=pd.Timestamp(captured):excluded+=1;continue
        identity=lambda n:'ECW_813' if n=='Монтана 2003' else key('BG_W_',n)
        rows.append(dict(mac_id='BG_W_'+link['href'].split('-')[1],lig='BG_W_A',sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when,ev=identity(names[0]),dep=identity(names[1]),ev_skor=hs,dep_skor=ds,
            home_name=names[0],away_name=names[1],gender='Women',tarafsiz_saha=False,regulation_minutes=40,
            source_url='https://comps.basketball.bg/'+link['href'],listing_url=url,captured_at_utc=captured,
            available_at_utc=None,date_precision='timestamp',phase=label,neutral_venue_verified=False))
    return rows,excluded


def save(code,rows,report):
    g=pd.DataFrame(rows)
    if g.empty:raise ValueError('No validated finished observations')
    path=Path(f'data/domestic/{code}.parquet');path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():g=pd.concat([pd.read_parquet(path),g],ignore_index=True)
    for _,part in g.groupby('mac_id'):
        if len(part[['ev','dep','tarih_utc','ev_skor','dep_skor']].drop_duplicates())!=1:raise ValueError('Conflicting persisted regional result')
    if (g.ev==g.dep).any():raise ValueError('Same team on both sides')
    g=g.drop_duplicates('mac_id',keep='first').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    temp=path.with_suffix('.part');g.to_parquet(temp,index=False);temp.replace(path)
    evidence=Path('docs/kanit/domestic');evidence.mkdir(parents=True,exist_ok=True)
    report.update(games=len(g),teams=len(set(g.ev)|set(g.dep)),seasons=g.groupby('sezon').size().to_dict(),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),used_in_default_model=False)
    (evidence/f'{code}_collection.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    return g


def bulgaria(years=(2022,2023,2024,2025,2026)):
    captured=pd.Timestamp.now(tz='UTC').isoformat();rows=[];sources=[];excluded=0
    page=BeautifulSoup(fetch('https://comps.basketball.bg/champ-4792-a-grupa-jeni'),'html.parser')
    seasons={int(o.get_text().split('/')[0]):o['value'] for o in page.select('select#season option') if re.fullmatch(r'\d{4}/\d{4}',o.get_text())}
    for year in years:
        if year not in seasons:raise ValueError('Requested season absent from official catalog')
        params=dict(bg_id=3,act='results',age_id=0,gender=0,season=seasons[year],region_id=0,regiongroup_id=0,bigchamp_id=0,champ_id=0)
        url=BG+'?'+urlencode(params);r,n=parse_bg(fetch(url,refresh=year>=2026),year,url,captured)
        rows+=r;excluded+=n;sources.append(url);print('Bulgaria',year,len(r),flush=True);time.sleep(.25)
    return save('BG_W_A',rows,dict(source='basketball.bg',sources=sources,captured_at_utc=captured,excluded=excluded,
        coverage='All returned senior A-group phases, excluding friendlies. Completeness, overtime and neutral venues not independently verified; publication time unknown.'))


def parnu():
    # Only the public anonymous client used by the official club calendar. Never store its token.
    official='https://bcparnu.ee/calendar';page=BeautifulSoup(fetch(official,refresh=True),'html.parser')
    src=next((s['src'] for s in page.select('script[src]') if s['src'].startswith('/assets/index-')),None)
    if not src:raise ValueError('Changed official club application')
    script=fetch('https://bcparnu.ee'+src)
    match=re.search(r'"(https://[a-z]+\.supabase.co)"',script);token=re.search(r'"(eyJ[^" ]+)"',script)
    if not match or not token:raise ValueError('Public club calendar configuration missing')
    url=match[1]+'/rest/v1/games?select=*&order=game_date.desc&limit=1000'
    with urllib.request.urlopen(urllib.request.Request(url,headers={'apikey':token[1],'Authorization':'Bearer '+token[1]}),timeout=25) as r:
        data=json.load(r)
    if not isinstance(data,list) or len(data)>=1000:raise ValueError('Invalid or potentially truncated public club calendar')
    captured=pd.Timestamp.now(tz='UTC').isoformat();rows=[];states={};competitions={}
    allowed={'OlyBet Eesti-Läti korvpalliliiga':'EE_LV_M','Optibet Eesti-Läti Korvpalliliiga':'EE_LV_M',
             'Optibet Korvpalli Meistriliiga':'EE_M_KML','Eesti Meistriliiga':'EE_M_KML','Optibet Eesti Meistriliiga':'EE_M_KML'}
    for r in data:
        states[r['status']]=states.get(r['status'],0)+1;competitions[r['competition']]=competitions.get(r['competition'],0)+1
        if r['competition'] not in allowed or r['status'] not in ('finished','completed','final'):continue
        hs,ds=r.get('home_score'),r.get('away_score');when=pd.Timestamp(r['game_date'])
        if type(hs) is not int or type(ds) is not int or min(hs,ds)<=0 or hs==ds or when>=pd.Timestamp(captured):continue
        if 'BC Pärnu' not in (r['home_team'],r['away_team']):raise ValueError('Non-club fixture in cohort')
        identity=lambda n:'FEC_58616' if n=='BC Pärnu' else key('EE_M_',n)
        year=when.year if when.month>=7 else when.year-1
        rows.append(dict(mac_id='PARNU_'+r['id'],lig=allowed[r['competition']],sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when,ev=identity(r['home_team']),dep=identity(r['away_team']),ev_skor=hs,dep_skor=ds,
            home_name=r['home_team'],away_name=r['away_team'],gender='Men',regulation_minutes=40,tarafsiz_saha=False,
            source_url=official,captured_at_utc=captured,available_at_utc=None,date_precision='timestamp',neutral_venue_verified=False))
    return save('PARNU_DOMESTIC',rows,dict(source=official,captured_at_utc=captured,observed_statuses=states,
        observed_competitions=competitions,coverage='Official senior club cohort only; not a complete Estonian/Latvian league archive. Unknown competitions excluded; no European double counting. Publication time unknown.'))

if __name__=='__main__':bulgaria();parnu()
