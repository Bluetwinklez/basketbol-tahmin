"""Official KBL public website requests, excluding D-League/cups/all-stars.

Channel/TeamCode are public web-client routing headers, not authentication.
No bearer token, logged-in session or paid credential is used.
"""
import hashlib,json,re,time,urllib.request
from pathlib import Path
from urllib.parse import urlencode
import pandas as pd
from .asia import save

BASE='https://api.kbl.or.kr/'
HEADERS={'User-Agent':'BasketballPregameResearch/0.5','Channel':'WEB','TeamCode':'XX',
         'X-Requested-With':'XMLHttpRequest','lang':'ko'}
ALIASES={'06':['KT Sonicboom','Suwon KT Sonicboom','Busan KT Sonicboom'],
         '16':['Dongbu Promy','Wonju DB Promy','Wonju Dongbu Promy']}


def get(path,refresh=False):
    cache=Path('data/raw/asia/kbl')/(hashlib.sha256(path.encode()).hexdigest()+'.json')
    if refresh or not cache.exists():
        with urllib.request.urlopen(urllib.request.Request(BASE+path,headers=HEADERS),timeout=25) as r:raw=r.read(5_000_001)
        if len(raw)>5_000_000:raise ValueError('KBL response exceeds bound')
        data=json.loads(raw)
        if not isinstance(data,list):raise ValueError('Unexpected KBL response, not an empty result')
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_bytes(raw);time.sleep(1.05)
    return json.loads(cache.read_text())


def parse(rows,seasons,captured):
    games=[];fixtures=[];aliases={};excluded={}
    for r in rows:
        if r.get('seasonGrade')!=1 or str(r.get('gameCode'))!='01':
            excluded['other_competitions']=excluded.get('other_competitions',0)+1;continue
        source=seasons.get(r.get('seasonCode'))
        if source is None or r.get('seasonName1')!=source['seasonName']:raise ValueError('Wrong KBL season identity')
        gmkey=r.get('gmkey','');expected=f"S{r['seasonCode']}G01N{r['gameNo']}"
        if gmkey!=expected or r.get('glkey')!=source['glkey']:raise ValueError('KBL game/competition key conflict')
        date=str(r['gameDate']);clock=str(r.get('gameStart',''))
        if not re.fullmatch(r'\d{8}',date) or not re.fullmatch(r'\d{4}',clock):raise ValueError('Unknown KBL date/time format')
        when=pd.Timestamp(pd.to_datetime(date+clock,format='%Y%m%d%H%M')).tz_localize('Asia/Seoul').tz_convert('UTC')
        if not source['gamedateStart']<=date<=source['gamedateEnd']:raise ValueError('KBL result outside catalog season window')
        h,a=str(r['tcodeH']),str(r['tcodeA'])
        if h==a or not all(re.fullmatch(r'\d{2}',x) for x in (h,a)):raise ValueError('Invalid senior KBL team codes')
        for side,tid in [('H',h),('A',a)]:aliases.setdefault('KBL_'+tid,set()).update([r['tname'+side],r['tnameF'+side]])
        year=int(source['seasonName'][:4]);base=dict(mac_id='KBL_'+gmkey,lig='KBL',sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when,ev='KBL_'+h,dep='KBL_'+a,home_name=r['tnameFH'],away_name=r['tnameFA'],
            regulation_minutes=40,gender='Men',tarafsiz_saha=False,date_precision='timestamp',neutral_venue_verified=False,
            source_url=BASE+'match/'+gmkey,captured_at_utc=captured,available_at_utc=None,
            venue_name=r.get('stadiumnameEn') or r.get('stadiumname'),source_season_code=r['seasonCode'])
        hs,ds=r.get('scoreH'),r.get('scoreA')
        if when>pd.Timestamp(captured) and r.get('isStarted')==0:
            fixtures.append(dict(base,status='scheduled'));continue
        if r.get('isEnded')!=1 or r.get('playingQuarter')!='X' or when>=pd.Timestamp(captured):
            excluded['not_final']=excluded.get('not_final',0)+1;continue
        if type(hs) is not int or type(ds) is not int or min(hs,ds)<=0 or hs==ds:raise ValueError('Invalid KBL final scores')
        games.append(dict(base,ev_skor=hs,dep_skor=ds))
    return games,fixtures,aliases,excluded


def collect(first=2017,last=2026):
    catalog=get('season/list',refresh=True)
    seasons={s['seasonCode']:s for s in catalog if s.get('seasonGrade')==1 and s.get('gameCode')=='01' and re.fullmatch(r'\d{4}-\d{4}',s.get('seasonName',''))}
    current=get('common/teamList',refresh=True);teams={}
    for r in current:
        k='KBL_'+r['teamCode'];teams[k]=dict(name=r['teamNameFullEn'],aliases=[r['teamName'],r['teamNameFull'],r['teamNameEn'],*ALIASES.get(r['teamCode'],[])])
    records=[];fixtures=[];sources=[];counts=[]
    for year in range(first,last+1):
        query=urlencode(dict(fromDate=f'{year}0101',toDate=f'{year}1231',seasonGrade=1));url=BASE+'match/list?'+query
        rows=get('match/list?'+query,refresh=year>=pd.Timestamp.now(tz='UTC').year)
        captured=pd.Timestamp.now(tz='UTC').isoformat();g,f,aliases,excluded=parse(rows,seasons,captured)
        for key,names in aliases.items():
            entry=teams.setdefault(key,dict(name=sorted(names)[0],aliases=[]));entry['aliases']=sorted(set(entry['aliases'])|names)
        records+=g;fixtures+=f;sources.append(url);counts.append(dict(calendar_year=year,returned=len(rows),accepted=len(g),excluded=excluded))
        save('KBL',records,teams,dict(source='Official KBL API public website',sources=sources,counts=counts,captured_at_utc=captured,
            limitations='Senior men regular season only, exact source season/game identities; D-League/cups/playoffs excluded. Calendar-window responses are unpaginated in the observed client; independent completeness is unverified. Historical publication, relocations/ownership continuity and neutral venues require caution. Public web routing headers only; no authentication.'),fixtures if year>=pd.Timestamp.now(tz='UTC').year else None)
        print('KBL',year,len(g),flush=True)


if __name__=='__main__':collect()
