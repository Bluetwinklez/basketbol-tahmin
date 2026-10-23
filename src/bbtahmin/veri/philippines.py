"""Dated PBA conference facts from public team schedules, with W/L cross-checks.

The league prefix alone does NOT filter a team schedule: the per-row competition
label is mandatory. Governors, Commissioners and Philippine Cups stay separate.
"""
import re,time,hashlib,urllib.error,json
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from .competitions import fetch,ROOT
from .asia import save,CODES

BASE='https://basketball.realgm.com'
PREFIX='/international/league/132/PBA--Governors-Cup'
COMPETITIONS={'PBA - Governors Cup':'PBA_GOV','PBA - Commissioners Cup':'PBA_COM','PBA - Philippine Cup':'PBA_PHI'}
ALIASES={'1744':['Phoenix Puls','Phoenix Fuel Masters','Phoenix Super LPG Fuel Masters'],
         '938':['Rain or Shine','Rain Shine','Rain or Shine Elasto Painters']}


def parse(html,team_id,end_year,captured):
    soup=BeautifulSoup(html,'html.parser');rows=[];excluded=0
    for tr in soup.select('tr'):
        cells={c.get('data-th'):c for c in tr.select('td[data-th]')}
        if not {'Date','Opponent','Result','Venue'}<=cells.keys():continue
        labels=[label for label in COMPETITIONS if cells['Venue'].get_text(' ',strip=True).endswith(label)]
        if len(labels)!=1:excluded+=1;continue
        code=COMPETITIONS[labels[0]]
        link=cells['Result'].find('a',href=re.compile('/international/boxscore/'))
        opponent=cells['Opponent'].find('a',href=re.compile('/team/'))
        score=re.fullmatch(r'([WL]),\s*(\d+)\s*-\s*(\d+)',cells['Result'].get_text(' ',strip=True))
        if not link or not opponent or not score:excluded+=1;continue
        other=re.search(r'/team/(\d+)/',opponent['href'])
        if not other:raise ValueError('Missing PBA opponent identity')
        away=cells['Opponent'].get_text(' ',strip=True).startswith('@')
        h,a=(other[1],str(team_id)) if away else (str(team_id),other[1])
        hs,ds=int(score[2]),int(score[3])
        if min(hs,ds)<=0 or hs==ds:excluded+=1;continue
        if ((ds>hs) if away else (hs>ds))!=(score[1]=='W'):raise ValueError('PBA score orientation conflicts with team W/L')
        day=pd.Timestamp(cells['Date'].get_text(' ',strip=True),tz='UTC')
        if not end_year-1<=day.year<=end_year:raise ValueError('Wrong PBA source season')
        if day>=pd.Timestamp(captured).floor('D'):excluded+=1;continue
        rows.append(dict(mac_id='PBA_R'+link['href'].rsplit('/',1)[-1],lig=code,sezon=f'{end_year-1}-{str(end_year)[-2:]}',
            tarih_utc=day,ev='PBA_'+h,dep='PBA_'+a,ev_skor=hs,dep_skor=ds,gender='Men',
            regulation_minutes=48,tarafsiz_saha=True,neutral_venue_verified=False,date_precision='day',
            source_url=BASE+link['href'],captured_at_utc=captured,available_at_utc=None,
            source_competition=labels[0],venue_label=cells['Venue'].get_text(' ',strip=True),
            court_note='PBA designated sides are retained; no verified home-court advantage assumed.'))
    return rows,excluded


def collect(first=2015,last=2027):
    last_request=0.;records={c:[] for c in ('PBA_GOV','PBA_COM','PBA_PHI')};teams={};counts=[];sources=[];errors=[]
    def get(path):
        nonlocal last_request
        url=BASE+path;cache=ROOT/(hashlib.sha256(url.encode()).hexdigest()+'.html')
        if not cache.exists():time.sleep(max(0.,1.05-(time.monotonic()-last_request)))
        text=fetch(url);last_request=time.monotonic();return text
    for year in range(first,last+1):
        seed=PREFIX+f'/team/1744/Phoenix-Fuel-Masters/schedule/{year}'
        page=get(seed);soup=BeautifulSoup(page,'html.parser');choices={}
        for option in soup.select('option[value]'):
            m=re.fullmatch(PREFIX+r'/team/(\d+)/([^/]+)/schedule/'+str(year),option['value'])
            if m:choices[m[1]]=dict(name=option.get_text(strip=True),slug=m[2],path=option['value'])
        if len(choices)<8:errors.append(dict(year=year,reason='Incomplete or missing team selector'));continue
        before=sum(map(len,records.values()));excluded=0;blocked=False
        for tid,entry in sorted(choices.items()):
            teams['PBA_'+tid]=dict(name=entry['name'],aliases=ALIASES.get(tid,[]))
            try:
                text=page if entry['path']==seed else get(entry['path'])
                rows,n=parse(text,tid,year,pd.Timestamp.now(tz='UTC').isoformat());excluded+=n
            except Exception as e:
                # Never bypass an unavailable source. Preserve and report partial coverage.
                errors.append(dict(year=year,team=tid,error=type(e).__name__+': '+str(e)))
                if isinstance(e,urllib.error.HTTPError) and e.code in (401,403,429):blocked=True;break
                continue
            for row in rows:records[row['lig']].append(row)
        counts.append(dict(end_year=year,teams_requested=len(choices),source_rows=sum(map(len,records.values()))-before,excluded=excluded));sources.append(BASE+seed)
        captured=pd.Timestamp.now(tz='UTC').isoformat()
        identities={}
        for rows in records.values():
            for row in rows:
                values=tuple(row[k] for k in ('lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor'))
                old=identities.setdefault(row['mac_id'],values)
                if old!=values:raise ValueError('PBA fixture conflicts across conference/season copies')
        for code,rows in records.items():
            if rows:save(code,rows,teams,dict(source='RealGM public team schedules',sources=sources,counts=counts,errors=errors,captured_at_utc=captured,
                limitations='Per-row conference labels checked; team-copy results deduplicated and W/L orientation crosschecked. Day precision; same-day results withheld. Current season/complete league coverage unverified. Neutral/home status and original publication time unknown. Imports/rules differ by conference and era; separate models required. No guarantee of current PBA coverage.'))
        print('PBA',year,'source rows',sum(map(len,records.values()))-before,flush=True)
        if blocked:break
    evidence=Path('docs/kanit/asia_data');evidence.mkdir(parents=True,exist_ok=True)
    (evidence/f'PBA_attempts_{first}_{last}.json').write_text(json.dumps(dict(first=first,last=last,counts=counts,errors=errors,
        captured_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),note='Failed/missing selectors are unknown coverage, not proof of zero games.'),indent=2))


if __name__=='__main__':collect()
