"""Validated official EuroLeague schedule and final facts, season-scoped."""
import pandas as pd


def facts(payload, captured, season, url):
    rows = payload.get('data', [])
    if payload.get('total', len(rows)) != len(rows):
        raise ValueError('Incomplete official schedule')
    fixtures, results, seen = [], [], set()
    for row in rows:
        if row['season']['code'] != season:
            raise ValueError('Wrong official season')
        event = row['identifier']
        if event in seen:
            raise ValueError('Duplicate official fixture')
        seen.add(event)
        start = pd.Timestamp(row['utcDate'])
        if start.tzinfo is None:
            raise ValueError('Official start needs timezone')
        home, away = row['local']['club'], row['road']['club']
        if home['code'] == away['code']:
            raise ValueError('Identical official teams')
        common = dict(event_id=event, source_url=url, captured_at=captured, start_utc=start.isoformat(),
                      league='E', home=home['code'], away=away['code'],
                      home_name=home['name'], away_name=away['name'])
        if row.get('played'):
            h, a = row['local']['score'], row['road']['score']
            if type(h) is int and type(a) is int and min(h, a) > 0 and h != a and start < pd.Timestamp(captured):
                results.append(dict(common, status='final', home_score=h, away_score=a))
        elif (row.get('confirmedDate') and row.get('confirmedHour') and
              row.get('gameStatus') == 'Confirmed' and start > pd.Timestamp(captured)):
            fixtures.append(dict(common, status='scheduled'))
    return fixtures, results
