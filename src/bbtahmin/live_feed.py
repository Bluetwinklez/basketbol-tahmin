"""NBA/ESPN scoreboard observations, isolated from unvalidated in-play predictors.

ESPN is the default independent provider; NBA CDN access may be unavailable.
"""
import hashlib,json,re,urllib.request
from pathlib import Path
import pandas as pd
from .quality import timestamp

URL='https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json'
ESPN='https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
CODES={'BKN':'BRK','CHA':'CHO','PHX':'PHO'}


def parse(payload,captured_at):
    captured=timestamp(captured_at);meta=payload.get('meta',{});updated=meta.get('time');verified=False
    if updated:
        parsed=pd.Timestamp(updated)
        if parsed.tzinfo is not None:
            age=(captured-parsed.tz_convert('UTC')).total_seconds();verified=bool(0<=age<=120)
    rows=[]
    for g in payload.get('scoreboard',{}).get('games',[]):
        if g.get('gameStatus')!=2:continue
        period=g.get('period');clock=g.get('gameClock','');m=re.fullmatch(r'PT(\d+)M([0-9.]+)S',clock)
        if type(period) is not int or period<1 or not m:raise ValueError('Invalid official live state')
        seconds=int(m[1])*60+float(m[2]);duration=720 if period<=4 else 300
        if not 0<=seconds<=duration:raise ValueError('Clock exceeds official period')
        home,away=g['homeTeam'],g['awayTeam'];h,a=home['score'],away['score']
        if any(type(v) is not int or v<0 for v in [h,a]):raise ValueError('Invalid official score')
        if home['teamTricode']==away['teamTricode']:raise ValueError('Identical live teams')
        rows.append(dict(event_id=g['gameId'],league='NBA',home=CODES.get(home['teamTricode'],home['teamTricode']),
            away=CODES.get(away['teamTricode'],away['teamTricode']),home_score=h,away_score=a,
            period=period,remaining_seconds=seconds,regulation_minutes=48,overtime=period>4,
            start_utc=timestamp(g['gameTimeUTC']).isoformat(),captured_at_utc=captured.isoformat(),
            source_updated_at=updated,source_freshness_verified=verified,source_url=URL,
            used_for_prediction=False,note='Official scoreboard capture only. Download freshness does not establish source freshness. No validated NBA in-play model is claimed.'))
    return rows


def parse_espn(payload,captured_at):
    captured=timestamp(captured_at)
    if not any(l.get('abbreviation')=='NBA' for l in payload.get('leagues',[])):raise ValueError('Wrong scoreboard league')
    rows=[]
    for event in payload.get('events',[]):
        competitions=event.get('competitions',[])
        if len(competitions)!=1:raise ValueError('Ambiguous scoreboard competition')
        game=competitions[0];status=game.get('status',event.get('status',{}))
        if status.get('type',{}).get('state')!='in':continue
        if len(game['competitors'])!=2:raise ValueError('Ambiguous scoreboard competitors')
        sides={t['homeAway']:t for t in game['competitors']}
        if set(sides)!={'home','away'}:raise ValueError('Invalid scoreboard sides')
        h,a=sides['home'],sides['away'];period=status['period'];clock=status['displayClock']
        if type(period) is not int or period<1 or not re.fullmatch(r'\d{1,2}:\d{2}',clock):raise ValueError('Invalid live clock')
        mm,ss=map(int,clock.split(':'));seconds=mm*60+ss
        if ss>=60 or seconds>(720 if period<=4 else 300):raise ValueError('Clock exceeds period')
        hs,as_=int(h['score']),int(a['score'])
        if min(hs,as_)<0:raise ValueError('Negative score')
        if h['team']['abbreviation']==a['team']['abbreviation']:raise ValueError('Identical live teams')
        rows.append(dict(event_id=event['id'],league='NBA',home=CODES.get(h['team']['abbreviation'],h['team']['abbreviation']),
            away=CODES.get(a['team']['abbreviation'],a['team']['abbreviation']),home_score=hs,away_score=as_,
            period=period,remaining_seconds=seconds,regulation_minutes=48,overtime=period>4,
            start_utc=timestamp(event['date']).isoformat(),captured_at_utc=captured.isoformat(),
            source_url=ESPN,source_updated_at=None,source_freshness_verified=False,used_for_prediction=False,
            note='Public broadcaster scoreboard observation; source update timestamp unavailable, so live freshness is unverified.'))
    return rows


def capture(provider='espn'):
    if provider not in ('espn','nba'):raise ValueError('Unknown live provider')
    url=ESPN if provider=='espn' else URL
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'bbtahmin/0.4 research'}),timeout=25) as r:
        payload=json.load(r)
    captured=pd.Timestamp.now(tz='UTC');rows=(parse_espn if provider=='espn' else parse)(payload,captured)
    listed=len(payload.get('events',[])) if provider=='espn' else len(payload.get('scoreboard',{}).get('games',[]))
    report=dict(captured_at_utc=captured.isoformat(),source_url=url,provider=provider,live_games=rows,
        total_listed=listed,prediction_enabled=False)
    root=Path('data/observations/live');root.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(report,sort_keys=True,allow_nan=False).encode();digest=hashlib.sha256(raw).hexdigest()
    path=root/(captured.strftime('%Y%m%dT%H%M%S')+'_'+digest[:12]+'.json')
    with path.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
    return report
