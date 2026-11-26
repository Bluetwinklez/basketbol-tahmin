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

SETTLEMENT_SPEC = "football-settlement-evidence-v1"
SETTLEMENT_FILE = "settlement_finals.json"
RESULT_FIELDS = ("league", "season_year", "provider_event_id", "provider_home_id", "provider_away_id",
                 "home", "away", "start_utc", "status", "home_score", "away_score")


def read_settlement_evidence(path):
    if not path.exists():
        return {"spec": SETTLEMENT_SPEC, "fixtures": {}}
    evidence = json.loads(path.read_text(encoding="utf8"))
    if evidence.get("spec") != SETTLEMENT_SPEC or not isinstance(evidence.get("fixtures"), dict):
        raise ValueError("Invalid football settlement evidence")
    return evidence


def retain_settlement_facts(evidence, report):
    """Keep the earliest observation of each distinct fact, including disagreements."""
    if report.get("spec") != "football-fixture-confirmation-v1":
        raise ValueError("Invalid football fixture confirmation")
    cutoff = timestamp(report["checked_at_utc"])
    for review in report["reviews"]:
        if review["status"] not in ("confirmed", "date_conflict"):
            continue
        fact = review["observation"]
        provider_id = str(fact.get("provider_event_id", ""))
        league = fact["league"]
        if league not in CODES or not provider_id.isascii() or not provider_id.isdigit():
            raise ValueError("Invalid football settlement provider identity")
        identity = f"{league}:{provider_id}"
        book = evidence["fixtures"]
        state = fact["status"]
        if state != "final" and identity not in book:
            continue
        start = timestamp(fact["start_utc"])
        captured = timestamp(fact["captured_at"])
        if (captured > cutoff or fact["event_id"] != review["event_id"]
                or fact["home"] == fact["away"]
                or fact["source_url"] != f"https://www.espn.com/soccer/game/_/gameId/{provider_id}"):
            raise ValueError("Invalid football settlement provenance")
        if state == "final" and (start >= captured or any(
            type(fact.get(side)) is not int or fact[side] < 0 for side in ("home_score", "away_score")
        )):
            raise ValueError("Invalid observed football final")
        observations = book.setdefault(identity, [])
        fields = (*RESULT_FIELDS, "event_id")
        signature = tuple(fact.get(field) for field in fields)
        if not any(tuple(old.get(field) for field in fields) == signature for old in observations):
            observations.append(fact)
    return evidence


def settlement_finals(evidence, held_ids=(), held_provider_keys=(), now=None):
    """Filter disputes at the provider and archive identities before settlement."""
    clock = timestamp(now or pd.Timestamp.now(tz="UTC"))
    by_event = {}
    providers = {}
    for key, observations in evidence["fixtures"].items():
        visible = [fact for fact in observations if timestamp(fact["captured_at"]) <= clock]
        for fact in visible:
            identity = (fact["league"], fact["event_id"])
            providers.setdefault(identity, set()).add(key)
        signatures = {tuple(fact.get(field) for field in RESULT_FIELDS) for fact in visible}
        if (len(signatures) != 1 or key in held_provider_keys
                or any(fact["event_id"] in held_ids for fact in visible)):
            continue
        fact = min(visible, key=lambda row: timestamp(row["captured_at"]))
        identity = (fact["league"], fact["event_id"])
        if fact["status"] != "final":
            continue
        by_event[identity] = fact
    return [fact for identity, fact in sorted(by_event.items()) if len(providers[identity]) == 1]


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
                if prior and any(prior.get(k)!=row.get(k) for k in (*RESULT_FIELDS, 'home_name', 'away_name')):
                    raise ValueError('Conflicting publisher fixture pages')
                unique[row['provider_event_id']]=row
            group=groups[code]
            reports.extend(confirm(f,list(unique.values()),aliases) for f in group.to_dict('records'))
        except Exception as exc: errors.append(dict(league=code,reason=f'{type(exc).__name__}: {exc}'))
    result=dict(spec='football-fixture-confirmation-v1',checked_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
                reviews=reports,errors=errors,note='Publisher fixture validation and settlement facts only. No scores imported into model training archives; explicit aliases, ordered teams and unique same-day identity required.')
    output = root.parent/'football_fixture_checks'
    evidence_path = output / SETTLEMENT_FILE
    evidence = read_settlement_evidence(evidence_path)
    retain_settlement_facts(evidence, result)
    write_json(evidence_path, evidence)
    write_json(output/'latest.json',result)
    return result
