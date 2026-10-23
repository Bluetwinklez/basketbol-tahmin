"""Read local pregame quotes as they were observed, with no future snapshots."""
import json
from pathlib import Path

import pandas as pd

from .odds import no_vig


class _HistoryConflict(ValueError):
    pass


def history(event_id, root='.', as_of=None, limit=200):
    if not 1 <= limit <= 1000:
        raise ValueError('limit must be between 1 and 1000')
    now = pd.Timestamp.now(tz='UTC')
    cutoff = now if as_of is None else pd.Timestamp(as_of)
    if pd.isna(cutoff) or cutoff.tzinfo is None or cutoff > now:
        raise ValueError('as_of must be a timezone-aware timestamp no later than now')
    cutoff = cutoff.tz_convert('UTC')
    folder = Path(root)/'data/bulten'
    paths = sorted(folder.glob('iddaa_*.json'))
    if (folder/'latest.json').exists():
        paths.append(folder/'latest.json')
    observed=Path(root)/'data/observations/odds'
    paths+=sorted(observed.glob('iddaa_*.json'))
    if (observed/'latest.json').exists():paths.append(observed/'latest.json')
    # The timestamp is read from content, never trusted from the filename.
    observations, skipped = {}, 0
    identity = None
    for path in paths:
        try:
            snapshot = json.loads(path.read_text('utf8'))
            captured = pd.Timestamp(snapshot['captured_at_utc'])
            if pd.isna(captured) or captured.tzinfo is None:
                raise ValueError('Missing capture timezone')
            if captured > cutoff:
                continue
            events = [e for e in snapshot['events'] if str(e['event_id']) == str(event_id)]
            if not events:
                continue
            if len(events) != 1:
                raise ValueError('Duplicate event ID')
            event = events[0]; start = pd.Timestamp(event['start_utc'])
            if pd.isna(start) or start.tzinfo is None:
                raise ValueError('Missing fixture timezone')
            start = start.tz_convert('UTC')
            if captured >= start:
                continue
            current = (event['home'], event['away'], event['competition_id'], start.isoformat())
            quote = event.get('moneyline')
            if quote is None:
                continue
            if (quote['market_id'] != '1_2' or quote['includes_overtime'] is not True
                    or quote['price_field'] != 'odd'):
                raise ValueError('Incompatible market')
            probability = float(no_vig(quote['home_odds'], quote['away_odds'])[0])
            row = dict(captured_at_utc=captured.tz_convert('UTC').isoformat(),
                       start_utc=start.tz_convert('UTC').isoformat(), home=event['home'], away=event['away'],
                       home_odds=quote['home_odds'], away_odds=quote['away_odds'],
                       market_home=probability, minimum_combination_count=quote['minimum_combination_count'],
                       promotion_flag=event.get('promotion_flag'))
            if identity is not None and identity != current:
                raise _HistoryConflict('Fixture identity or scheduled tipoff changed; do not merge histories')
            if captured in observations and observations[captured] != row:
                raise _HistoryConflict('Conflicting quotes at the same capture instant')
            identity = current
            observations[captured] = row
        except _HistoryConflict:
            raise
        except (OSError, TypeError, KeyError, ValueError, OverflowError):
            skipped += 1
    rows = [observations[k] for k in sorted(observations)]
    movement = rows[-1]['market_home']-rows[0]['market_home'] if rows else None
    return dict(event_id=str(event_id), as_of_utc=cutoff.isoformat(), observations=len(rows),
                returned=min(limit, len(rows)), truncated=len(rows)>limit, skipped_files=skipped,
                first_observed=rows[0] if rows else None, latest_observed=rows[-1] if rows else None,
                market_home_change=movement, history=rows[-limit:],
                note='First/last locally observed pregame quote, not verified opening/closing prices. '
                     'Movement is descriptive, not an activated model feature or a profit estimate.')
