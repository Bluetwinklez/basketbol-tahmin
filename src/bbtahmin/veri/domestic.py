"""Official Czech senior women's ZBL archive, with explicit cross-source mappings."""
import hashlib,json,re,time
from pathlib import Path
from urllib.parse import urlencode
import pandas as pd
from bs4 import BeautifulSoup
from .competitions import fetch

BASE='https://zbl.basketball/zapasy'
# Explicit senior women's identities. Unmapped clubs keep their own namespace.
MAPPING={'Žabiny Brno':'ECW_892','KP Brno':'ECW_891'}


def identity(name):
    return MAPPING.get(name,'CZ_W_'+hashlib.sha256(name.encode()).hexdigest()[:16])


def parse(html,year,url,captured,excluded=None):
    soup=BeautifulSoup(html,'html.parser')
    if not soup.title or 'ŽBL' not in soup.title.get_text():raise ValueError('Wrong official competition page')
    rows=[];fixtures=[]
    for tr in soup.select('table tbody tr'):
        cells=tr.find_all('td',recursive=False)
        if len(cells)>=3:
            future=re.fullmatch(r'(\d{4})-(\d\d)-(\d\d)-(\d\d)-(\d\d)',cells[2].get('data-sort',''))
            if future:
                t=pd.Timestamp(f'{future[1]}-{future[2]}-{future[3]} {future[4]}:{future[5]}',tz='Europe/Prague').tz_convert('UTC')
                if t>=pd.Timestamp(captured):
                    if excluded is not None:excluded.append(dict(source=url,reason='Future fixture, not a finished result'))
                    continue
        if len(cells)<7:raise ValueError('Changed ZBL result table')
        if 'kontumov' in tr.get_text(' ',strip=True).lower():
            if excluded is not None:excluded.append(dict(source=url,reason='Official forfeit; excluded from played-score modeling'))
            continue
        date=cells[2].get('data-sort','');m=re.fullmatch(r'(\d{4})-(\d\d)-(\d\d)-(\d\d)-(\d\d)',date)
        link=cells[4].select_one('a[href^="/zapas/"]')
        names=[n.get_text(' ',strip=True) for n in cells[3].select('.text-nowrap')]
        if not m or link is None or len(names)!=2:raise ValueError('Missing fixture date, score or senior team names')
        when=pd.Timestamp(f'{m[1]}-{m[2]}-{m[3]} {m[4]}:{m[5]}',tz='Europe/Prague').tz_convert('UTC')
        if not year<=when.year<=year+1:raise ValueError('Wrong season response')
        event=re.fullmatch(r'/zapas/(\d+)(?:#.*)?',link['href'])
        if not event:raise ValueError('Unknown fixture identifier')
        home,away=map(identity,names)
        base=dict(mac_id='CZ_W_ZBL_'+event[1],lig='CZ_W_ZBL',sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when,ev=home,dep=away,home_name=names[0],away_name=names[1],gender='Women',
            regulation_minutes=40,tarafsiz_saha=False,neutral_venue_verified=False,
            source_url='https://zbl.basketball/zapas/'+event[1],listing_url=url,
            captured_at_utc=captured,available_at_utc=None,date_precision='timestamp',
            phase=cells[6].get_text(' ',strip=True))
        fixtures.append(base)
        score=link.get_text(' ',strip=True).split()
        if len(score)!=2 or not all(re.fullmatch(r'\d+',v) for v in score):continue
        hs,ds=map(int,score)
        if when>=pd.Timestamp(captured) or min(hs,ds)<=0 or hs==ds:continue
        rows.append(dict(base,ev_skor=hs,dep_skor=ds))
    return rows,fixtures


def collect(years=(2022,2023,2024,2025,2026)):
    captured=pd.Timestamp.now(tz='UTC').isoformat();records=[];fixtures=[];sources=[];counts=[];excluded=[]
    for year in years:
        listing=fetch(BASE+'?y='+str(year),refresh=year>=2026)
        s=BeautifulSoup(listing,'html.parser');select=s.select_one('select[name="p1"]')
        if select is None:raise ValueError('Missing official phase catalog')
        phases=[o['value'] for o in select.select('option[value]') if o['value'].isdigit() and int(o['value'])>0]
        if not phases:raise ValueError('No phases for requested season')
        for phase in phases:
            url=BASE+'?'+urlencode({'y':year,'c':0,'k':0,'p1[]':phase,'d_od':'','d_do':''})
            html=fetch(url,refresh=year>=2026);r,f=parse(html,year,url,captured,excluded)
            records+=r;fixtures+=f;sources.append(url);counts.append(dict(year=year,phase=phase,listed=len(f),finished=len(r)))
            time.sleep(.25)
        print('ZBL',year,'cumulative results',len(records),flush=True)
    g=pd.DataFrame(records)
    if g.empty:raise ValueError('No official completed results')
    if (g.ev==g.dep).any():raise ValueError('Same club on both sides')
    root=Path('data/domestic');root.mkdir(parents=True,exist_ok=True);path=root/'CZ_W_ZBL.parquet'
    if path.exists():g=pd.concat([pd.read_parquet(path),g],ignore_index=True)
    for _,part in g.groupby('mac_id'):
        if len(part[['ev','dep','ev_skor','dep_skor','tarih_utc']].drop_duplicates())!=1:raise ValueError('Persisted official score conflict')
    g=g.drop_duplicates('mac_id',keep='first').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    temporary=path.with_suffix('.part');g.to_parquet(temporary,index=False);temporary.replace(path)
    pd.DataFrame(fixtures).drop_duplicates('mac_id').to_parquet(root/'CZ_W_ZBL_fixtures.parquet',index=False)
    report=dict(captured_at_utc=captured,games=len(g),seasons=g.groupby('sezon').size().to_dict(),
        teams=len(set(g.ev)|set(g.dep)),excluded=excluded,phases=counts,sources=sources,explicit_mappings=MAPPING,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),used_in_default_model=False,
        limitations='Official listing numeric facts; not independently crosschecked. All discovered phases requested; completeness unverified. Historical publication time unknown. Neutral venues and overtime not independently verified. No fuzzy identity mapping.')
    evidence=Path('docs/kanit/domestic');evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'CZ_W_ZBL_collection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return g

if __name__=='__main__':collect()
