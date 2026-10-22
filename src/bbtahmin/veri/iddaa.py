"""Experimental read-only adapter for Iddaa's website JSON backend.

This is NOT a documented third-party developer API or a Nesine integration.
The upstream schema can change. No login, paid key or betting action is used.
Source discovery: borakilicoglu/iddaa-mcp; implementation is independent.
"""
import json
import math
import os
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

BASE = 'https://sportsbookv2.iddaa.com/sportsbook/'
ENDPOINTS = {'events': 'events?st=2&type=0&version=0',
             'competitions': 'competitions', 'markets': 'get_market_config'}
LATEST = Path('data/bulten/latest.json')
LEAGUES = {'abd amerika basketbol ligi':'NBA','abd amerikan basketbol ligi':'NBA','nba':'NBA','euroleague':'E',
           'eurocup':'U','avustralya nbl':'NBL'}


def key(value):
    value = str(value).replace('ı','i').replace('İ','i')
    return ' '.join(unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower().split())


def _get(endpoint):
    request = urllib.request.Request(BASE+endpoint,headers={'User-Agent':'bbtahmin/0.2 research',
                                                           'Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=20) as response:
        raw = response.read(4_000_001)
    if len(raw)>4_000_000:
        raise ValueError('Bulletin response exceeds 4 MB')
    payload = json.loads(raw)
    if not isinstance(payload,dict) or payload.get('isSuccess') is not True or 'data' not in payload:
        raise ValueError('Bulletin upstream returned an unsuccessful response')
    return payload['data']


def _price(value):
    try:
        result = float(value)
        return result if math.isfinite(result) and result>1 else None
    except (TypeError,ValueError):
        return None


def normalize(events,competitions,markets,captured_at):
    captured = pd.Timestamp(captured_at)
    if captured.tzinfo is None:
        raise ValueError('Capture time must include a timezone')
    captured = captured.tz_convert('UTC')
    catalog = {str(c['i']):c for c in competitions}
    result, rejected = [], []
    for event in events:
        try:
            if event.get('sid')!=2:
                continue
            start = pd.to_datetime(event['d'],unit='s',utc=True)
            if pd.isna(start) or not event.get('hn') or not event.get('an'):
                raise ValueError('Missing teams or start time')
            competition = catalog.get(str(event['ci']),{})
            league_name = competition.get('n','Unknown')
            row = dict(event_id=str(event['i']),home=event['hn'],away=event['an'],
                       start_utc=start.isoformat(),league_name=league_name,
                       model_league=LEAGUES.get(key(league_name)),competition_id=str(event['ci']),
                       source='iddaa-web-experimental',captured_at_utc=captured.isoformat(),
                       pre_match=bool(start>captured),minimum_combination_count=int(event.get('mbc',0)),
                       promotion_flag=event.get('kOdd'),moneyline=None,totals=[])
            for market in event.get('m',[]):
                market_id=f"{market.get('t')}_{market.get('st')}"
                definition=markets.get(market_id,{})
                if definition.get('st')!=2 or market.get('s')!=1:
                    continue
                outcomes={o.get('n'):o for o in market.get('o',[])}
                base=dict(market_id=market_id,market_name=definition.get('n'),price_field='odd',
                          includes_overtime=True,minimum_combination_count=int(market.get('mbc',row['minimum_combination_count'])))
                if market_id=='1_2' and key(definition.get('n'))=='mac sonucu (uzt.dahil)' and set(outcomes)=={'1','2'}:
                    home,away=(_price(outcomes[s].get('odd')) for s in ('1','2'))
                    if home and away:
                        row['moneyline']=dict(base,home_odds=home,away_odds=away,
                                              home_alternative_price=_price(outcomes['1'].get('wodd')),
                                              away_alternative_price=_price(outcomes['2'].get('wodd')))
                if market_id=='2_114' and 'uzt.dahil' in key(definition.get('n')) and set(outcomes)=={'Alt','Üst'}:
                    try:
                        line=float(market.get('sov'))
                    except (TypeError,ValueError):
                        continue
                    under,over=(_price(outcomes[s].get('odd')) for s in ('Alt','Üst'))
                    if under and over and math.isfinite(line) and line>0:
                        row['totals'].append(dict(base,line=line,under_odds=under,over_odds=over,
                                                  push_possible=line.is_integer()))
            result.append(row)
        except (KeyError,TypeError,ValueError,OverflowError) as error:
            rejected.append(dict(event_id=str(event.get('i')),reason=str(error)))
    if len({r['event_id'] for r in result})!=len(result):
        raise ValueError('Duplicate upstream event IDs')
    return dict(source_url=BASE+ENDPOINTS['events'],experimental=True,
                captured_at_utc=captured.isoformat(),events=result,rejected=rejected)


def collect(path=LATEST):
    events=_get(ENDPOINTS['events'])
    competitions=_get(ENDPOINTS['competitions'])
    markets=_get(ENDPOINTS['markets'])
    if not isinstance(events,dict) or not isinstance(events.get('events'),list) or not isinstance(competitions,list) or not isinstance(markets,dict) or not isinstance(markets.get('m'),dict):
        raise ValueError('Upstream bulletin schema changed')
    # Mark capture AFTER all responses: an earlier capture would misdate knowledge.
    snapshot=normalize(events['events'],competitions,markets['m'],pd.Timestamp.now(tz='UTC'))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    timestamp=pd.Timestamp(snapshot['captured_at_utc']).strftime('%Y%m%dT%H%M%S%fZ')
    content=json.dumps(snapshot,ensure_ascii=False,indent=2)
    archive=path.parent/f'iddaa_{timestamp}.json'
    archive.write_text(content,'utf8')
    temporary=path.with_suffix('.part');temporary.write_text(content,'utf8');os.replace(temporary,path)
    return snapshot


def load(path=LATEST,now=None):
    path=Path(path)
    if not path.exists():
        raise ValueError('No bulletin snapshot; run python -m bbtahmin bulten --guncelle')
    snapshot=json.loads(path.read_text('utf8'))
    now=pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    captured=pd.Timestamp(snapshot['captured_at_utc'])
    if now.tzinfo is None or captured.tzinfo is None or captured>now:
        raise ValueError('Invalid or future bulletin capture time')
    snapshot['age_minutes']=(now-captured).total_seconds()/60
    snapshot['stale']=snapshot['age_minutes']>15
    return snapshot
