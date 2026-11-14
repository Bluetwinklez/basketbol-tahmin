"""Explicit historical CC0 backfill; no current-season or cross-league inference."""
import hashlib
from .data import parse_text
from .storage import save


def import_2019(text, source_url, captured, root):
    marker = '▪ Playoffs, Semifinals'
    if text.count(marker) != 1:
        raise ValueError('Expected explicit regular-season/playoff boundary')
    regular = text.split(marker)[0]
    rows = parse_text(regular, 'TR2', '2019-20', source_url, captured)
    if len(rows) != 306 or len({r['home'] for r in rows} | {r['away'] for r in rows}) != 18:
        raise ValueError('Incomplete 18-team regular season')
    if any(r['status'] != 'final' for r in rows):
        raise ValueError('Historical regular season requires final scores')
    metadata = dict(league='TR2',season='2019-20',source_url=source_url,
                    source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                    license='CC0-1.0',captured_at_utc=captured,
                    note='Community regular-season results, not official verification. Playoffs excluded. Day precision; July dates belong to pandemic-extended 2020 season.')
    return save(rows,'TR2','2019-20',root,metadata)
