"""Timestamped NBA fixtures and finals from ESPN's dated scoreboards."""
import json
from datetime import timedelta

import pandas as pd

from ..live_feed import CODES, ESPN
from ..quality import timestamp
from .http import CachedHTTP
from .nba_kutu import ESPN_KOD


# Canonical ev/dep values in data/maclar.parquet (NBA rows).
ARCHIVE_CODES = frozenset('''ATL BOS BRK CHI CHO CLE DAL DEN DET GSW HOU IND LAC LAL MEM
                            MIA MIL MIN NOP NYK OKC ORL PHI PHO POR SAC SAS TOR UTA WAS'''.split())
ESPN_CODES = {**ESPN_KOD, **CODES}


def _status(status):
    state, name = status.get('state'), status.get('name')
    if state == 'pre' and name in (None, 'STATUS_SCHEDULED') and status.get('completed') is not True:
        return 'scheduled'
    if state == 'post' and name in (None, 'STATUS_FINAL') and status.get('completed') is True:
        return 'final'
    return 'other'


def parse_espn(payload, captured_at, source_url):
    """Return scheduled fixtures and completed results; ignore other states."""
    if not any(league.get('abbreviation') == 'NBA' for league in payload.get('leagues', [])):
        raise ValueError('Wrong ESPN scoreboard league; expected NBA')
    events = payload.get('events')
    if not isinstance(events, list):
        raise ValueError('Missing ESPN NBA scoreboard events')
    captured = timestamp(captured_at).isoformat()
    fixtures, results = [], []
    unknown, seen = set(), set()
    for event in events:
        event_id = event['id']
        if not event_id or event_id in seen:
            raise ValueError(f'Missing or duplicate ESPN NBA event ID: {event_id!r}')
        seen.add(event_id)
        competitions = event.get('competitions', [])
        if len(competitions) != 1:
            raise ValueError(f'Ambiguous ESPN NBA competition for {event_id}')
        game = competitions[0]
        competitors = game.get('competitors', [])
        sides = {team['homeAway']: team for team in competitors}
        if len(competitors) != 2 or set(sides) != {'home', 'away'}:
            raise ValueError(f'Invalid ESPN NBA competitors for {event_id}')
        home, away = sides['home'], sides['away']
        tricodes = [side['team']['abbreviation'] for side in (home, away)]
        codes = [ESPN_CODES.get(code, code) for code in tricodes]
        invalid = [code for code, mapped in zip(tricodes, codes) if mapped not in ARCHIVE_CODES]
        if invalid:
            unknown.update(invalid)
            continue
        if codes[0] == codes[1]:
            raise ValueError(f'Identical ESPN NBA teams for {event_id}')
        status = _status(game.get('status', event.get('status', {})).get('type', {}))
        if status == 'other' or game.get('timeValid') is False:
            continue
        row = dict(event_id=event_id, league='NBA', home=codes[0], away=codes[1],
                   home_name=home['team'].get('displayName') or codes[0],
                   away_name=away['team'].get('displayName') or codes[1],
                   start_utc=timestamp(event['date']).isoformat(), captured_at=captured,
                   source_url=source_url, status=status)
        if status == 'final':
            row.update(home_score=int(home['score']), away_score=int(away['score']))
            results.append(row)
        else:
            fixtures.append(row)
    if unknown:
        raise ValueError(f'Unknown ESPN NBA team tricodes: {", ".join(sorted(unknown))}')
    return fixtures, results


def collect():
    """Fetch today's board and seven days ahead, plus yesterday for finals."""
    today = pd.Timestamp.now(tz='America/New_York').date()
    http = CachedHTTP()
    fixtures, results = {}, {}
    for offset in range(-1, 8):
        day = today + timedelta(days=offset)
        url = f'{ESPN}?dates={day:%Y%m%d}'
        raw = http.get(url, nba=True, refresh=True)
        captured = pd.Timestamp.now(tz='UTC')
        scheduled, finals = parse_espn(json.loads(raw), captured, url)
        for fixture in scheduled:
            if timestamp(fixture['start_utc']) > captured:
                fixtures[fixture['event_id']] = fixture
        if offset <= 0:
            results.update((row['event_id'], row) for row in finals)
    return [row for event_id, row in fixtures.items() if event_id not in results], list(results.values())
