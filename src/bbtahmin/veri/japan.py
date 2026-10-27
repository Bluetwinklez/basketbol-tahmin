"""Official public B.LEAGUE schedule facts, with observed UI pagination.

Detailed S3 contexts are not required and no unavailable endpoint is bypassed.
Only the selected division's regular league event is collected.
"""
import json,re,time
from pathlib import Path
from urllib.parse import urlencode,urlparse
import pandas as pd
from bs4 import BeautifulSoup
from .competitions import fetch,ROOT
from .asia import save
import hashlib

BASE='https://www.bleague.jp/schedule/'
ALIASES={'ls':['Shiga Lakes','Shiga Lake Stars','Shiga Lakestars'],
         'nv':['Nagasaki Velca'],'oe':['Osaka Evessa'],
         'sr':['Sun Rockers Shibuya','SUN Rockers Shibuya','Tokyo Sunrockers'],
         'rf':['Rizing Fukuoka','Rizing Fukuoka BB','Rizing Zephyr Fukuoka'],
         'ez':['Earthfriends Tokyo Z','Erth Tokyo Z'],
         'hb':['Tokyo Hachioji','Tokyo Hac','Tokyo Hachioji Bee Trains'],'tu':['Tokyo United']}


def parse_topics(topics,year,division,captured,last_date=None,rejected=None):
    if division not in (1,2):raise ValueError('Unsupported Japanese division')
    code=f'JP_B{division}';records=[];fixtures=[];teams={};excluded=0
    for topic in topics:
        soup=BeautifulSoup(topic,'html.parser')
        for node in soup.select('.champion-box .title,li.list-item'):
            if node.name!='li':
                m=re.search(r'(\d{4})\.(\d{2})\.(\d{2})',node.get_text())
                if not m:continue  # Additional event headlines include all-star games.
                last_date=f'{m[1]}-{m[2]}-{m[3]}';continue
            spans=node.select('.info-arena > span')
            round_label=spans[0].get_text(strip=True) if spans else ''
            reorganised=(year>=2026 and spans and 'setu-none' in spans[0].get('class',[]) and not round_label)
            if node.select_one('.game_ajst') is not None or not (re.match(r'^第\d+節',round_label) or reorganised):excluded+=1;continue
            if last_date is None:raise ValueError('Missing date across schedule pagination')
            gid=node.get('id','')
            if not gid.isdigit():raise ValueError('Missing Japanese schedule identity')
            names=[];ids=[]
            for side in ('home','away'):
                team=node.select_one('.team.'+side);img=team.select_one('img') if team else None
                if team is None or img is None:raise ValueError('Changed Japanese team schema')
                token=Path(urlparse(img['src']).path).stem
                if not re.fullmatch(r'[a-z0-9_-]+',token):raise ValueError('Unknown Japanese logo identity')
                tid='JP_'+token;name=team.select_one('.team-name').get_text(' ',strip=True)
                ids.append(tid);names.append(name)
                teams[tid]=dict(name=name,aliases=ALIASES.get(token,[]),source_identity='Official schedule logo code: '+token)
            clock=spans[-1].get_text(strip=True) if spans else ''
            if not re.fullmatch(r'\d{1,2}:\d{2}',clock):excluded+=1;continue
            when=pd.Timestamp(last_date+' '+clock,tz='Asia/Tokyo').tz_convert('UTC')
            start_year=when.tz_convert('Asia/Tokyo').year if when.tz_convert('Asia/Tokyo').month>=7 else when.tz_convert('Asia/Tokyo').year-1
            if start_year!=year:raise ValueError('Japanese response belongs to another season')
            base=dict(mac_id=code+'_'+gid,lig=code,sezon=f'{year}-{str(year+1)[-2:]}',tarih_utc=when,
                ev=ids[0],dep=ids[1],home_name=names[0],away_name=names[1],regulation_minutes=40,
                gender='Men',tarafsiz_saha=False,neutral_venue_verified=False,date_precision='timestamp',
                source_url='https://www.bleague.jp/game_detail/?ScheduleKey='+gid,
                captured_at_utc=captured,available_at_utc=None,source_division=division,
                source_event=2 if division==1 else 7,
                source_round_label=round_label,league_reorganisation=bool(year>=2026),
                competition_code=('JP_PREMIER' if division==1 else 'JP_ONE') if year>=2026 else code,
                legacy_storage_code=code,
                venue_label=spans[-2].get_text(' ',strip=True) if len(spans)>=2 else None)
            state=node.select_one('.info-scorestate');state=state.get_text(strip=True) if state else ''
            if when>pd.Timestamp(captured):fixtures.append(dict(base,status='scheduled'));continue
            if state!='FINAL':excluded+=1;continue
            scores=[node.select_one('.'+side+'-score') for side in ('home','away')]
            if all(s is not None and not s.get_text(strip=True) for s in scores) and rejected is not None:
                rejected.append(dict(mac_id=base['mac_id'], source_url=base['source_url'],
                    tarih_utc=when.isoformat(), captured_at_utc=captured,
                    reason='Official FINAL has two empty score fields',
                    source_state=state, home_score_text='', away_score_text=''))
                excluded+=1
                continue
            if any(s is None or not re.fullmatch(r'\d+',s.get_text(strip=True)) for s in scores):raise ValueError('Final without valid Japanese scores')
            h,a=[int(s.get_text(strip=True)) for s in scores]
            if min(h,a)<=0 or h==a:excluded+=1;continue
            records.append(dict(base,ev_skor=h,dep_skor=a))
    return records,fixtures,teams,last_date,excluded


def collect(years=(2021,2022,2023,2024,2025,2026),divisions=(1,2),refresh_current=True):
    last_request=0.
    incomplete=[]
    def get(url,refresh=False):
        nonlocal last_request
        cache=ROOT/(hashlib.sha256(url.encode()).hexdigest()+'.html')
        if refresh or not cache.exists():time.sleep(max(0.,1.05-(time.monotonic()-last_request)))
        result=fetch(url,refresh);last_request=time.monotonic();return result
    for division in divisions:
        records=[];fixtures=[];teams={};counts=[];sources=[];rejected=[]
        for year in years:
            params=dict(year=year,mon='all',day='',tab=division,event=2 if division==1 else 7)
            page_url=BASE+'?'+urlencode(params);full=get(page_url)
            for key,value in [('year',year),('tab',division),('event',params['event'])]:
                if not re.search(r"var\s+"+key+r"\s*=\s*'"+str(value)+r"'",full):raise ValueError('Wrong Japanese season/division/event response')
            index=0;last_date=None;ids=set();before=len(records);excluded=0;pages=0
            while True:
                query=dict(params,data_format='json',index=index);url=BASE+'?'+urlencode(query)
                payload=json.loads(get(url,refresh=refresh_current and year>=2026));captured=pd.Timestamp.now(tz='UTC').isoformat()
                rejected_before=len(rejected)
                rows,upcoming,catalog,last_date,n=parse_topics(payload['topics'],year,division,captured,last_date,rejected)
                current={r['mac_id'] for r in rows+upcoming+rejected[rejected_before:]}
                if ids&current:raise ValueError('Repeated Japanese pagination results')
                ids|=current;records+=rows;fixtures+=upcoming;teams.update(catalog);excluded+=n;pages+=1
                next_index=payload.get('index')
                if not next_index:break
                if type(next_index) is not int or next_index<=index or pages>=100:raise ValueError('Invalid/truncated Japanese pagination')
                index=next_index
            counts.append(dict(year=year,accepted=len(records)-before,pages=pages,excluded=excluded));sources.append(page_url)
            report=dict(rejected_finals=rejected,partial=bool(rejected),source='Official B.LEAGUE public schedule',sources=sources,counts=counts,captured_at_utc=captured,
                refresh_current_requested=refresh_current,cache_reparse_only=not refresh_current,
                limitations='Regular-season event only; playoffs/cups excluded. All advertised pages requested, not an independent completeness proof. Logo codes are source identities; reorganisations, renamed clubs and 2026 league changes require caution. Historical publication, neutral venues and overtime unverified. No blocked detailed-context endpoint used.')
            active=pd.Timestamp.now(tz='UTC');active_year=active.year if active.month>=7 else active.year-1
            # Historical-only backfills must not erase the current schedule.
            # A freshly observed empty CURRENT schedule must revoke old fixtures.
            save(f'JP_B{division}',records,teams,report,fixtures if year>=active_year else None)
            print('Japan',division,year,len(records)-before,'pages',pages,flush=True)
        if rejected:incomplete.append(f'JP_B{division}: {len(rejected)} blank-score finals quarantined')
    if incomplete:raise ValueError('Partial Japanese refresh; valid results saved; '+ '; '.join(incomplete))


if __name__=='__main__':collect()
