"""Validate an entire source snapshot before merging or replacing any archive."""
import gzip
import json
from pathlib import Path


def validate(rows, code, season):
    ids, fixtures = set(), set()
    for item in rows:
        if item['league'] != code or item['season'] != season:
            raise ValueError('Source competition/season mismatch')
        natural = (item['date'], item['home'], item['away'])
        if item['event_id'] in ids or natural in fixtures:
            raise ValueError('Duplicate source identity')
        ids.add(item['event_id']); fixtures.add(natural)


def save(rows, code, season, root, metadata=None):
    rows = list(rows)
    validate(rows, code, season)
    target = Path(root) / f'{code}_{season}.json.gz'
    if target.exists():
        old = json.loads(gzip.decompress(target.read_bytes()))['rows']
        validate(old, code, season)
        merged = {r['event_id']: r for r in rows}
        for previous in old:
            fresh = merged.get(previous['event_id'])
            if fresh and any(fresh[k] != previous[k] for k in ('date', 'home', 'away')):
                raise ValueError('Source fixture identity changed')
            if previous['status'] == 'final':
                if fresh and fresh['status'] == 'final' and any(
                        fresh[k] != previous[k] for k in ('home_goals', 'away_goals')):
                    raise ValueError('Conflicting final score; retained previous snapshot')
                if not fresh or fresh['status'] != 'final':
                    merged[previous['event_id']] = previous
        rows = list(merged.values())
    validate(rows, code, season)
    licensed_path=Path(root)/'licensed_overlays'/f'{code}_{season}.json.gz'
    if licensed_path.exists():
        # A new community snapshot must not invalidate an independently checked
        # retained final. Check before the atomic replacement, not after it.
        from .licensed import merge as verify_licensed
        licensed_rows=json.loads(gzip.decompress(licensed_path.read_bytes()))['rows']
        verify_licensed(rows,licensed_rows)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(metadata or {}, rows=rows)
    encoded = gzip.compress(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(), mtime=0)
    temporary = target.with_suffix('.part')
    temporary.write_bytes(encoded)
    temporary.replace(target)
    return rows
