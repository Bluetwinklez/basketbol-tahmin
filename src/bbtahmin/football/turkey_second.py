"""Explicit historical CC0 backfill; no current-season or cross-league inference."""
import hashlib
from collections import Counter
from .data import parse_text
from .storage import save


def validate_2019(rows):
    """Require the complete directed round robin before touching an archive."""
    teams = {r['home'] for r in rows} | {r['away'] for r in rows}
    if len(rows) != 306 or len(teams) != 18:
        raise ValueError('Incomplete 18-team regular season')
    actual = Counter((r['home'], r['away']) for r in rows)
    expected = Counter((home, away) for home in teams for away in teams if home != away)
    if actual != expected:
        raise ValueError('Regular season must contain each directed pairing exactly once')
    if any(r['league'] != 'TR2' or r['season'] != '2019-20' or
           r['status'] != 'final' for r in rows):
        raise ValueError('Historical regular season requires TR2 2019-20 final scores')
    if any(not '2019-08-16' <= r['date'] <= '2020-07-19' for r in rows):
        raise ValueError('Date outside historical regular-season window')
    return dict(teams=len(teams), finals=len(rows), directed_pairings=len(actual),
                home_games_per_team=17, away_games_per_team=17,
                first_date=min(r['date'] for r in rows),
                last_date=max(r['date'] for r in rows))


def import_2019(text, source_url, captured, root):
    marker = '▪ Playoffs, Semifinals'
    if text.count(marker) != 1:
        raise ValueError('Expected explicit regular-season/playoff boundary')
    regular = text.split(marker)[0]
    rows = parse_text(regular, 'TR2', '2019-20', source_url, captured)
    validate_2019(rows)
    metadata = dict(league='TR2',season='2019-20',source_url=source_url,
                    source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    license='CC0-1.0',captured_at_utc=captured,
                    note='Community regular-season results, not official verification. Playoffs excluded. Day precision; July dates belong to pandemic-extended 2020 season.')
    return save(rows,'TR2','2019-20',root,metadata)
