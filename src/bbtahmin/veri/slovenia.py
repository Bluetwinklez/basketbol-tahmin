"""Verified senior-women first league via the federation's published public API."""
import json,time
from urllib.parse import urlencode
import pandas as pd
from .competitions import fetch
from .regional import save,key

BASE='https://api.kzs.si/api/v1/public/'


def items(payload):
    if payload.get('status')!='OK':raise ValueError('Official API error')
    data=payload['data'];rows=data['items']
    count=data.get('count',0);limit=data.get('limit',0)
    if count>len(rows) or limit and len(rows)>=limit:raise ValueError('Potentially paginated response; refusing partial archive')
    return rows


def validate_competition(comp,year):
    if (comp.get('gender'),comp.get('category'),comp.get('rank'))!=('FEMALE','ABSOLUTE','FIRST') or comp.get('type') not in ('LEAGUE',None):
        raise ValueError('Not senior women first league')
    if comp.get('season',{}).get('name')!=f'{year}/{year+1}' or comp.get('name') not in ('1. Ž SKL','1. SKL za ženske','1. SKL za članice'):raise ValueError('Wrong season or competition')


def parse(rows,comp,year,url,captured):
    validate_competition(comp,year);result=[]
    for r in rows:
        refs=[c for c in r.get('competitions',[]) if c.get('competitionId')==comp['id'] and c.get('seasonId')==comp['season']['id']]
        if not refs:raise ValueError('Unrelated fixture in competition response')
        if r.get('status')!='FINISHED':continue
        hs,ds=r.get('firstTeamScore'),r.get('secondTeamScore');when=pd.Timestamp(r['dateTime'])
        if when.tzinfo is None:raise ValueError('Missing official timezone')
        if type(hs) is not int or type(ds) is not int or min(hs,ds)<=0 or hs==ds or when>=pd.Timestamp(captured):continue
        if not year<=when.year<=year+1:raise ValueError('Out-of-season result')
        names=[r['firstTeamName'],r['secondTeamName']]
        identity=lambda n:'ECW_58477' if n.casefold()=='cinkarna celje' else key('SI_W_',n)
        result.append(dict(mac_id='SI_W_'+str(r['id']),lig='SI_W_SKL',sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when,ev=identity(names[0]),dep=identity(names[1]),ev_skor=hs,dep_skor=ds,
            home_name=names[0],away_name=names[1],gender='Women',regulation_minutes=40,tarafsiz_saha=False,
            source_url=url,captured_at_utc=captured,available_at_utc=None,date_precision='timestamp',
            venue_name=r.get('sportHallName'),venue_id=r.get('sportHallId'),neutral_venue_verified=False))
    return result


def collect(years=(2022,2023,2024,2025,2026)):
    seasons=items(json.loads(fetch(BASE+'seasons/?sortBy=name&sort=DESC')))
    catalog={s['name']:s['id'] for s in seasons};captured=pd.Timestamp.now(tz='UTC').isoformat();records=[];sources=[];counts=[]
    for year in years:
        sid=catalog[f'{year}/{year+1}'];q=urlencode(dict(genders='FEMALE',seasonId=sid,categories='ABSOLUTE',ranks='FIRST'))
        candidates=items(json.loads(fetch(BASE+'competitions/?'+q,refresh=year>=2026)))
        choices=[c for c in candidates if c.get('name') in ('1. Ž SKL','1. SKL za ženske','1. SKL za članice') and c.get('type') in ('LEAGUE',None)]
        if len(choices)!=1:raise ValueError('Ambiguous or missing senior league identity')
        comp=choices[0];validate_competition(comp,year)
        url=BASE+'matches/?'+urlencode({'competitionId':comp['id']})
        rows=items(json.loads(fetch(url,refresh=year>=2026)));parsed=parse(rows,comp,year,url,captured)
        records+=parsed;sources.append(url);counts.append(dict(year=year,competition_id=comp['id'],listed=len(rows),finished=len(parsed)))
        print('Slovenia',year,len(parsed),flush=True);time.sleep(.25)
    return save('SI_W_SKL',records,dict(source='Košarkarska zveza Slovenije public API',sources=sources,
        captured_at_utc=captured,counts=counts,explicit_mapping={'Cinkarna Celje':'ECW_58477'},
        coverage='Discovered official senior-women first league, all returned fixtures. API count=0/limit=0 does not independently certify completeness. Only necessary match facts retained; referee/contact/administrative metadata excluded. Publication time, neutral venue and overtime unverified.'))

if __name__=='__main__':collect()
