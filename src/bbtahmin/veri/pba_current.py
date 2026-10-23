"""Public Sportsmetric PBA page facts; read React data without executing scripts.

This independent publisher fills a current-season gap. Its historical timezones,
box-score quality and completeness are not assumed official or fully verified.
"""
import hashlib,json,re
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from .competitions import fetch
from .asia import save

URL='https://www.sportsmetric.ph/leagues/pba'
CAMPAIGN='2025-26'  # Source season 50; matched against RealGM's 2025-2026 cup copies.
TEAM_IDS={'phoenix':'1744','rainorshine':'938','ginebra':'432','blackwater':'1643',
          'magnolia':'1241','converge':'2520','meralco':'935','nlex':'1644','smb':'937',
          'terrafirma':'1620','titan':'2789','tnt':'431','macau':'2827'}


def flight(html):
    text=''
    for script in BeautifulSoup(html,'html.parser').select('script'):
        raw=script.get_text()
        if raw.startswith('self.__next_f.push('):
            value=json.loads(raw[len('self.__next_f.push('):-1])
            if value[0]==1 and isinstance(value[1],str):text+=value[1]
    records={}
    for m in re.finditer(r'(?:^|\n)([0-9a-f]+):',text):
        try:records[m[1]]=json.JSONDecoder().raw_decode(text[m.end():])[0]
        except ValueError:continue  # Import/stylesheet records are not game data.
    if not records:raise ValueError('No structured publisher page data')
    return records


def resolve(value,records,_seen=None):
    seen=set() if _seen is None else set(_seen)
    while isinstance(value,str) and re.fullmatch(r'\$[0-9a-f]+(?::.*)?',value):
        if value in seen or len(seen)>=32:raise ValueError('Cyclic/oversized data reference')
        seen.add(value);parts=value[1:].split(':')
        if parts[0] not in records:raise ValueError('Unresolved publisher reference')
        value=records[parts[0]]
        for key in parts[1:]:
            if isinstance(value,str) and value.startswith('$'):value=resolve(value,records,seen)
            if isinstance(value,list):
                if key=='props' and len(value)==4 and value[0]=='$':value=value[3]
                elif key.isdigit():value=value[int(key)]
                else:raise ValueError('Unsupported publisher element reference path')
            else:value=value[key]
    return value


def objects(records):
    def walk(value):
        if isinstance(value,dict):
            yield value
            for v in value.values():yield from walk(v)
        elif isinstance(value,list):
            for v in value:yield from walk(v)
    for value in records.values():yield from walk(value)


def parse(html,captured):
    records=flight(html);found=list(objects(records))
    seasons=[r for r in found if r.get('league')=='PBA' and r.get('id')=='pba-gov-cup-50' and r.get('label')=="PBA 50th Season Governors' Cup"]
    if not seasons:raise ValueError('Not the expected senior PBA conference')
    games=[];fixtures=[];teams={};box=[];rejected=[];ids=set()
    for r in found:
        if r.get('league')!='PBA' or r.get('seasonId')!='pba-gov-cup-50' or 'homeTeam' not in r:continue
        if r['id'] in ids:raise ValueError('Duplicate publisher game identity')
        ids.add(r['id']);sides=[resolve(r[k],records) for k in ('homeTeam','awayTeam')];codes=[]
        for t in sides:
            if not isinstance(t,dict) or t.get('league')!='PBA' or t.get('seasonId')!=r['seasonId']:raise ValueError('Publisher team/league mismatch')
            name=t['id'].removesuffix('-pba-gov-cup-50')
            if not re.fullmatch('[a-z]+',name):raise ValueError('Unknown publisher team namespace')
            code='PBA_'+TEAM_IDS[name] if name in TEAM_IDS else 'PBA_SM_'+name
            codes.append(code);teams[code]=dict(name=t['name'],aliases=[t['shortName']]+({'phoenix':['Phoenix Puls'],'rainorshine':['Rain Shine','Rain or Shine']}.get(name,[])))
        when=pd.Timestamp(r['startTime'])
        if when.tzinfo is None or not pd.Timestamp('2026-07-01T00:00Z')<=when<pd.Timestamp('2027-07-01T00:00Z'):raise ValueError('Wrong publisher season/time')
        base=dict(mac_id='PBA_SM_'+hashlib.sha256(r['id'].encode()).hexdigest()[:20],lig='PBA_GOV',sezon=CAMPAIGN,
            ev=codes[0],dep=codes[1],home_name=sides[0]['name'],away_name=sides[1]['name'],gender='Men',regulation_minutes=48,
            tarafsiz_saha=True,neutral_venue_verified=False,source_url=URL,source_event_id=r['id'],source_season_id=r['seasonId'],
            source_start_utc=when.isoformat(),captured_at_utc=captured,available_at_utc=None,venue_label=r.get('venue'))
        if r['status']=='UPCOMING' and when>pd.Timestamp(captured):
            fixtures.append(dict(base,tarih_utc=when,date_precision='timestamp',status='scheduled'));continue
        if r['status']!='FINAL' or when>=pd.Timestamp(captured):continue
        h,a=r['homeScore'],r['awayScore']
        if type(h) is not int or type(a) is not int or min(h,a)<=0 or h==a:raise ValueError('Invalid publisher final score')
        # Historical clock quality is uncertified: do not advertise exact UTC tipoffs.
        games.append(dict(base,tarih_utc=when.floor('D'),date_precision='day',ev_skor=h,dep_skor=a))
        for side,team,actual in [('home',codes[0],h),('away',codes[1],a)]:
            players=(r.get('boxScore') or {}).get(side,[])
            if not players:continue
            if any(type(p.get('pts')) is not int or p['pts']<0 for p in players) or sum(p['pts'] for p in players)!=actual:
                rejected.append(dict(event_id=r['id'],side=side,reason='Player points do not sum to recorded final'));continue
            for p in players:
                fields={k:p.get(k) for k in ('pts','reb','ast','stl','blk','to','pf','fgA','fgM','ftA','ftM','threeA','threeM')}
                if not isinstance(p.get('playerId'),str) or not p['playerId'] or any(type(v) is not int or v<0 for v in fields.values()) or any(fields[m]>fields[a] for m,a in [('fgM','fgA'),('ftM','ftA'),('threeM','threeA')]):
                    rejected.append(dict(event_id=r['id'],side=side,reason='Invalid player counting statistic'));continue
                minimum=2*fields['fgM']+fields['threeM']+fields['ftM']
                maximum=4*fields['fgM']-fields['threeM']+fields['ftM']
                if (fields['threeM']>fields['fgM'] or fields['threeA']>fields['fgA'] or
                        not minimum<=fields['pts']<=maximum or (fields['pts']-minimum)%2):
                    rejected.append(dict(event_id=r['id'],side=side,reason='Scoring identity inconsistent, allowing unreported four-point makes'));continue
                box.append(dict(mac_id=base['mac_id'],team=team,player_id=p['playerId'],player_name=p.get('playerName'),
                    minutes_label=p.get('min'),**fields,source_url=URL,captured_at_utc=captured,
                    used_in_default_model=False,note='Individually checked postgame source rows; team boxes may be partial after quarantine. Target-game boxes are never pregame inputs. Provider IDs are season-scoped. Four-point makes are not inferred as observed data.'))
    unique={};conflicts=set()
    for row in box:
        key=(row['mac_id'],row['team'],row['player_id'])
        previous=unique.setdefault(key,row)
        fields=('minutes_label','pts','reb','ast','stl','blk','to','pf','fgA','fgM','ftA','ftM','threeA','threeM')
        if any(previous[k]!=row[k] for k in fields):conflicts.add(key)
    for key in conflicts:rejected.append(dict(event_id=key[0],side=key[1],reason='Conflicting duplicated player counting row'))
    box=[row for key,row in unique.items() if key not in conflicts]
    return games,fixtures,teams,box,rejected


def collect():
    text=fetch(URL,refresh=True);captured=pd.Timestamp.now(tz='UTC').isoformat();games,fixtures,teams,box,rejected=parse(text,captured)
    existing=Path('data/asia/PBA_GOV.parquet');duplicate_links=[];new=[];box_ids={}
    old=pd.read_parquet(existing) if existing.exists() else pd.DataFrame()
    for r in games:
        matches=[]
        if not old.empty:
            for p in old.itertuples():
                if p.mac_id==r['mac_id']:continue
                if p.sezon==r['sezon'] and abs(p.tarih_utc-r['tarih_utc'])<=pd.Timedelta(days=1) and {p.ev:p.ev_skor,p.dep:p.dep_skor}=={r['ev']:r['ev_skor'],r['dep']:r['dep_skor']}:matches.append(p.mac_id)
        if len(matches)>1:raise ValueError('Ambiguous cross-source PBA duplicate')
        if matches:
            duplicate_links.append(dict(publisher_id=r['source_event_id'],publisher_mac_id=r['mac_id'],existing_id=matches[0]))
            box_ids[r['mac_id']]=matches[0]
        else:new.append(r)
    report=dict(source='Independent public Sportsmetric publisher',sources=[URL],captured_at_utc=captured,
        current_model_season=CAMPAIGN,
        identity_evidence='Within source season 50 only, Macau Giant Pandas is linked to RealGM team 2827 (displayed as Macau Black Knights): eleven unique date/opponent/score pairs agree. This is not an inferred cross-season ownership history.',
        current_publisher_final_games=len(games),cross_source_duplicates=duplicate_links,rejected_boxes=rejected,
        validated_player_match_rows=len(box),
        limitations='Current conference publisher data, not an official PBA API. Historic clocks unverified: day precision and whole-day feature withholding. Three recent score pairs were independently checked against the official PBA homepage; that does not verify all history. No provider box is a target-game pregame feature. Completeness and original publication times unknown.')
    if not new and not old.empty:new=old.to_dict('records')
    save('PBA_GOV',new,teams,report,fixtures)
    root=Path('data/asia');path=root/'PBA_GOV_player_boxes.parquet'
    # This file is the validated snapshot of one explicitly identified campaign.
    # Replace it: merging old rows would resurrect statistics now quarantined.
    data=pd.DataFrame(box)
    if not data.empty:
        data['mac_id']=data.mac_id.map(lambda k:box_ids.get(k,k))
        data['team']=data.team.replace({'PBA_SM_macau':'PBA_2827'})
    data.to_parquet(path,index=False)
    print('PBA current',len(new),'new finals;',len(box),'validated player rows;',len(rejected),'box rejections',flush=True)


if __name__=='__main__':collect()
