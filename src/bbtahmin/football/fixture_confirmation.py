"""Independent publisher fixture checks; never an automatic training import."""
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError,URLError
from ..veri.public_bytes import fetch_bytes
import pandas as pd
from .data import key
from ..quality import timestamp

CODES={'EN1':'eng.1','EN2':'eng.2','DE1':'ger.1','ES1':'esp.1','FR1':'fra.1',
       'IT1':'ita.1','NL1':'ned.1','PT1':'por.1','TR1':'tur.1'}


def facts(payload,code,captured):
    captured=timestamp(captured)
    if {x.get('slug') for x in payload.get('leagues',[])}!={CODES[code]}:
        raise ValueError('Publisher competition identity mismatch')
    out=[];seen=set()
    for event in payload.get('events',[]):
        competitions=event.get('competitions',[])
        if len(competitions)!=1: continue
        game=competitions[0]
        if game.get('timeValid') is not True: continue
        sides={r['homeAway']:r for r in game.get('competitors',[])}
        if set(sides)!={'home','away'}: continue
        if sides['home']['team']['id']==sides['away']['team']['id']: raise ValueError('Same publisher club on both sides')
        start=timestamp(event['date']);status=game.get('status',event.get('status',{})).get('type',{})
        state='scheduled' if status.get('name')=='STATUS_SCHEDULED' else ('final' if status.get('name')=='STATUS_FULL_TIME' and status.get('completed') is True else 'unverified')
        if state=='unverified':continue
        identity=event['id']
        if identity in seen: raise ValueError('Duplicate publisher fixture')
        seen.add(identity)
        result=dict(provider_event_id=identity,league=code,season_year=event['season']['year'],start_utc=start.isoformat(),captured_at=captured.isoformat(),
                    home_name=sides['home']['team']['displayName'],away_name=sides['away']['team']['displayName'],
                    provider_home_id=sides['home']['team']['id'],provider_away_id=sides['away']['team']['id'],
                    source_url=f'https://www.espn.com/soccer/game/_/gameId/{identity}',status=state)
        if state=='final':
            if start>=captured: raise ValueError('Future publisher final')
            scores=[str(sides[s].get('score','')) for s in ('home','away')]
            if not all(v.isdigit() for v in scores): raise ValueError('Invalid publisher final score')
            result.update(home_score=int(scores[0]),away_score=int(scores[1]))
        out.append(result)
    return out


def confirm(fixture,observations,aliases):
    links={key(a):key(b) for a,b in aliases.items()}
    home=links.get(fixture['home'],fixture['home']);away=links.get(fixture['away'],fixture['away'])
    candidates=[r for r in observations if r['league']==fixture['league'] and r['season_year']==int(fixture['season'][:4]) and
                key(r['home_name'])==home and key(r['away_name'])==away and
                abs((timestamp(r['start_utc']).tz_localize(None).normalize()-pd.Timestamp(fixture['date'])).days)<=2]
    if len(candidates)!=1: return dict(status='ambiguous' if candidates else 'unconfirmed',event_id=fixture['event_id'])
    result=dict(candidates[0],event_id=fixture['event_id'],home=fixture['home'],away=fixture['away'])
    if result['start_utc'][:10]!=fixture['date']:
        return dict(status='date_conflict',event_id=fixture['event_id'],observation=result)
    return dict(status='confirmed',event_id=fixture['event_id'],observation=result)


def refresh(lookback=2,root=None):
    from .data import ROOT,load,write_json
    root=Path(root or ROOT)
    if type(lookback) is not int or not 2<=lookback<=45:raise ValueError('Lookback must be 2..45 days')
    now=pd.Timestamp.now(tz='UTC');frame=load(root);reports=[];errors=[]
    aliases=json.loads((root/'provider_aliases.json').read_text(encoding='utf8'))['aliases']
    groups={code:frame.loc[(frame.league==code)&(frame.date>=(now-pd.Timedelta(days=lookback)).strftime('%Y-%m-%d'))&
                          (frame.date<=(now+pd.Timedelta(days=7)).strftime('%Y-%m-%d'))] for code in CODES}
    def fetch_day(item):
        code,slug,day=item
        try:
            url=f'https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={day}&limit=100'
            for attempt in range(3):
                try:
                    payload=json.loads(fetch_bytes(url,refresh=True));break
                except (URLError,TimeoutError) as exc:
                    if attempt==2 or (isinstance(exc,HTTPError) and exc.code<500):raise
                    time.sleep(.5*(2**attempt))
            return code,facts(payload,code,pd.Timestamp.now(tz='UTC').isoformat()),None
        except Exception as exc:return code,[],dict(league=code,date=day,reason=f'{type(exc).__name__}: {exc}')
    observations_by_code={code:[] for code in CODES}
    with ThreadPoolExecutor(max_workers=4) as pool:
        # Inspect neighboring dates too: matching only the archive's disputed
        # day would fail to discover the very date errors this check targets.
        requests=[(code,slug,day) for code,slug in CODES.items() for day in sorted({
            (pd.Timestamp(date)+pd.Timedelta(days=offset)).strftime('%Y%m%d')
            for date in groups[code].date.unique() for offset in range(-2,3)})]
        for code,observations,error in pool.map(fetch_day,requests):
            observations_by_code[code].extend(observations)
            if error:errors.append(error)
    for code,slug in CODES.items():
        try:
            observations=observations_by_code[code]
            # A provider may include a nearby game on multiple date pages.
            unique={}
            for row in observations:
                prior=unique.get(row['provider_event_id'])
                if prior and any(prior[k]!=row[k] for k in ('start_utc','home_name','away_name','status')):
                    raise ValueError('Conflicting publisher fixture pages')
                unique[row['provider_event_id']]=row
            group=groups[code]
            reports.extend(confirm(f,list(unique.values()),aliases) for f in group.to_dict('records'))
        except Exception as exc: errors.append(dict(league=code,reason=f'{type(exc).__name__}: {exc}'))
    result=dict(spec='football-fixture-confirmation-v1',checked_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                reviews=reports,errors=errors,note='Publisher fixture validation and settlement facts only. No scores imported into model training archives; explicit aliases, ordered teams and unique same-day identity required.')
    write_json(root.parent/'football_fixture_checks/latest.json',result)
    return result
