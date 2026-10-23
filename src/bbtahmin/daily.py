"""One-command pregame research, immutable forecasts and separate settlement.

Only source-confirmed fixtures can enter the prospective record. Local archives
are not a live feed. A failed refresh never becomes a successful empty schedule.
"""
import contextlib
import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd

from .prospective import freeze, settle, verify
from .quality import timestamp

LEAGUES = ('E', 'KBL', 'JP_B1', 'JP_B2', 'PBA_GOV')
EURO_URL = 'https://api-live.euroleague.net/v2/competitions/E/seasons/{season}/games'


def refresh(leagues):
    """Refresh requested public sources independently; retain per-source errors."""
    outcomes = {}
    groups = [('E', ['E']), ('KBL', ['KBL']),
              ('Japan', [c for c in leagues if c.startswith('JP_')]), ('PBA', ['PBA_GOV'])]
    today = pd.Timestamp.now(tz='UTC')
    year = today.year if today.month >= 7 else today.year - 1
    for source, codes in groups:
        codes = [c for c in codes if c in leagues]
        if not codes:
            continue
        print(f'Refreshing {source} schedules/results...', file=sys.stderr, flush=True)
        try:
            # Collectors' progress belongs on stderr/inside the report, not JSON stdout.
            with contextlib.redirect_stdout(io.StringIO()) as log:
                if source == 'E':
                    from .veri.competitions import fetch
                    from .runtime_history import refresh_europe
                    from .euro_facts import facts
                    url = EURO_URL.format(season=f'E{year}')
                    payload = json.loads(fetch(url, refresh=True))
                    captured = pd.Timestamp.now(tz='UTC').isoformat()
                    fixtures, results = facts(payload, captured, f'E{year}', url)
                    refresh_europe(payload, captured, year=year)
                    target = Path('data/schedules/E.json')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(json.dumps(dict(fixtures=fixtures, results=results), indent=2))
                elif source == 'KBL':
                    from .veri.korea import collect
                    collect(first=today.year, last=today.year)
                elif source == 'Japan':
                    from .veri.japan import collect
                    collect(years=(year,), divisions=tuple(int(c[-1]) for c in codes))
                else:
                    from .veri.pba_current import collect
                    collect()
            for code in codes:
                outcomes[code] = dict(status='refreshed', log=log.getvalue())
            print(f'{source}: refreshed.', file=sys.stderr, flush=True)
        except Exception as exc:
            for code in codes:
                outcomes[code] = dict(status='failed', error=f'{type(exc).__name__}: {exc}')
            print(f'{source}: refresh failed ({type(exc).__name__}). See report.', file=sys.stderr, flush=True)
    return outcomes


def source_facts(code):
    """Read fixture capture times and finals without claiming archive freshness."""
    if code == 'E':
        path = Path('data/schedules/E.json')
        if not path.exists():
            raise ValueError('No EuroLeague schedule snapshot; run with --guncelle')
        payload = json.loads(path.read_text())
        return payload['fixtures'], payload['results']
    root = Path('data/asia')
    fixtures_path = root / f'{code}_fixtures.parquet'
    archive_path = root / f'{code}.parquet'
    if not archive_path.exists() or not fixtures_path.exists():
        raise ValueError(f'No fixture/archive snapshot for {code}; run with --guncelle')
    def convert(row, final=False):
        result = dict(event_id=row['mac_id'], league=code, home=row['ev'], away=row['dep'],
                      start_utc=timestamp(row['tarih_utc']).isoformat(),
                      captured_at=timestamp(row['captured_at_utc']).isoformat(),
                      source_url=row['source_url'],
                      home_name=row.get('home_name') or row['ev'], away_name=row.get('away_name') or row['dep'],
                      status='final' if final else row['status'])
        if final:
            result.update(home_score=int(row['ev_skor']), away_score=int(row['dep_skor']))
        return result
    # PBA's current publisher has day-only historical clocks. Never settle an
    # exact-time prospective fixture using a guessed midnight result timestamp.
    archive = pd.read_parquet(archive_path)
    finals = [convert(r, True) for r in archive.to_dict('records')
              if r.get('date_precision') == 'timestamp']
    fixtures = [convert(r) for r in pd.read_parquet(fixtures_path).to_dict('records')]
    return fixtures, finals


def record_path(root, fixture):
    identity = f"{fixture['league']}:{fixture['event_id']}"
    return root / 'forecasts' / (hashlib.sha256(identity.encode()).hexdigest() + '.json')


def run(leagues=LEAGUES, output='rapor/daily', update=False, hours=48, threshold=.65, now=None):
    if not leagues or any(c not in LEAGUES for c in leagues):
        raise ValueError('Unsupported daily schedule league')
    if not 1 <= hours <= 168 or not .5 <= threshold <= 1:
        raise ValueError('Hours must be 1..168 and probability threshold 0.5..1')
    if now is not None and update:
        raise ValueError('Historical clock cannot refresh current providers')
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    refreshed = refresh(leagues) if update else {}
    clock = timestamp(now or pd.Timestamp.now(tz='UTC'))
    report = dict(spec='daily-research-v1', checked_at_utc=clock.isoformat(), sources=refreshed,
                  probability_threshold=threshold, upcoming=[], skipped=[], settlements=[])
    all_results = []
    seen = set()
    # Reuse the project's original prospective records as well as this local
    # ledger. The earliest known forecast wins, even after models/data change.
    records, known = {}, {}
    paths = sorted(set((root / 'forecasts').glob('*.json')) |
                   set(Path('docs/kanit/prospective').glob('*.json')))
    for path in paths:
        try:
            candidate = json.loads(path.read_text())
            if not isinstance(candidate, dict) or candidate.get('spec') != 'prospective-v1':
                continue
            record = verify(candidate)
            records[str(path)] = record
            for item in record['forecasts']:
                f = item['fixture']; key = (f['league'], f['event_id'])
                old = known.get(key)
                if old is None or timestamp(record['recorded_at_utc']) < timestamp(old[1]['recorded_at_utc']):
                    known[key] = (path, record, item)
        except Exception as exc:
            # A damaged existing ledger must not silently permit replacement.
            raise ValueError(f'Invalid existing forecast record {path}: {exc}') from exc
    from .tahmin import tahmin_et
    from threadpoolctl import threadpool_limits
    for code in dict.fromkeys(leagues):
        try:
            fixtures, results = source_facts(code)
            all_results.extend(results)
        except Exception as exc:
            report['skipped'].append(dict(league=code, reason=str(exc)))
            continue
        for f in sorted(fixtures, key=lambda f: (f['start_utc'], f['event_id'])):
            if not clock < timestamp(f['start_utc']) <= clock + pd.Timedelta(hours=hours):
                continue
            entry = dict(fixture=f)
            try:
                key = (code, f['event_id'])
                if key in seen:
                    raise ValueError('Duplicate fixture in schedule')
                seen.add(key)
                path = record_path(root, f)
                if key in known:
                    path, record, item = known[key]
                    old = item['fixture']
                    if (any(old[k] != f[k] for k in ('event_id', 'league', 'home', 'away')) or
                            timestamp(old['start_utc']) != timestamp(f['start_utc'])):
                        raise ValueError('Fixture changed; original forecast retained, manual review required')
                    p = item['prediction']
                    entry['record_status'] = 'existing_immutable'
                else:
                    if refreshed.get(code, {}).get('status') == 'failed':
                        raise ValueError('Refresh failed; no new forecast from this source')
                    captured = timestamp(f['captured_at'])
                    if not captured <= clock or clock - captured > pd.Timedelta(hours=24):
                        raise ValueError('Fixture capture is stale or in the future; refresh first')
                    if f['status'] != 'scheduled':
                        raise ValueError('Fixture is not confirmed scheduled')
                    with threadpool_limits(limits=1):
                        p = tahmin_et(code, [(f['home'], f['away'])], f['start_utc'])[0]
                    # Use the actual post-computation clock in production: a slow
                    # model must not backdate a forecast past the real tipoff.
                    recorded = clock if now is not None else pd.Timestamp.now(tz='UTC')
                    record = freeze([p], [f], path, now=recorded)
                    records[str(path)] = record
                    known[key] = (path, record, record['forecasts'][0])
                    entry['record_status'] = 'new_immutable'
                entry.update(prediction=p, record=str(path),
                             threshold_passed=max(p['ev_kazanir'], 1-p['ev_kazanir']) >= threshold,
                             source_confirmation_fresh=bool(timestamp(f['captured_at']) <= clock and
                                 clock-timestamp(f['captured_at']) <= pd.Timedelta(hours=24) and
                                 refreshed.get(code, {}).get('status') != 'failed'),
                             selected=bool(p.get('selection_eligible', False) and
                                           timestamp(f['captured_at']) <= clock and
                                           clock-timestamp(f['captured_at']) <= pd.Timedelta(hours=24) and
                                           refreshed.get(code, {}).get('status') != 'failed' and
                                           max(p['ev_kazanir'], 1-p['ev_kazanir']) >= threshold))
                report['upcoming'].append(entry)
            except Exception as exc:
                report['skipped'].append(dict(league=code, event_id=f['event_id'], reason=str(exc)))
    for path, record in sorted(records.items()):
        try:
            if not any(item['fixture']['league'] in leagues for item in record['forecasts']):
                continue
            check = settle(record, all_results, now=clock if now is not None else pd.Timestamp.now(tz='UTC'))
            # Count each fixture once, using its earliest frozen forecast.
            fixtures_by_id = {item['fixture']['event_id']: item['fixture'] for item in record['forecasts']}
            retained = []
            for game in check['games']:
                f = fixtures_by_id[game['event_id']]
                key = (f['league'], f['event_id'])
                if f['league'] in leagues and str(known[key][0]) == path:
                    retained.append(game)
            check['games'] = retained
            if not check['games']:
                continue
            # Batch metrics are recomputed below from the retained game rows.
            for key in ('settled_games','pending_games','winner_accuracy','mean_total_absolute_error','mean_score_mae'):
                check.pop(key)
            report['settlements'].append(dict(record=str(path), **check))
        except Exception as exc:
            report['skipped'].append(dict(record=str(path), reason=str(exc)))
    games = [g for check in report['settlements'] for g in check['games']]
    finals = [g for g in games if g['status'] == 'final']
    report['performance'] = dict(settled_games=len(finals), pending_games=len(games)-len(finals),
        winner_accuracy=sum(g['winner_correct'] for g in finals)/len(finals) if finals else None,
        mean_score_mae=sum(g['score_mae'] for g in finals)/len(finals) if finals else None,
        mean_total_absolute_error=sum(g['total_absolute_error'] for g in finals)/len(finals) if finals else None,
        mean_margin_absolute_error=sum(g['margin_absolute_error'] for g in finals)/len(finals) if finals else None)
    report['note'] = ('Model probabilities are not measured accuracy. Rejected/low-probability forecasts remain visible. '
                      'Only source-confirmed timestamped finals settle. No live predictor. Small batches do not establish general accuracy.')
    stamp = pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S%fZ')
    with (root / f'check_{stamp}.json').open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    (root / 'latest.md').write_text(markdown(report), encoding='utf8')
    return report


def markdown(report):
    def cell(value):
        return str(value).replace('|', '/').replace('\n', ' ')
    lines = ['# Daily basketball research', '', f"Checked: {report['checked_at_utc']}", '',
             '| Tipoff (Istanbul) | League | Fixture | Score forecast | Home win | Data gate / probability filter |',
             '|---|---|---|---|---|---|']
    for entry in report['upcoming']:
        f, p = entry['fixture'], entry['prediction']
        when = timestamp(f['start_utc']).tz_convert('Europe/Istanbul').strftime('%d %b %H:%M')
        lines.append(f"| {when} | {f['league']} | {cell(f['home_name'])} – {cell(f['away_name'])} | "
                     f"{p['ev_skor']:.1f}–{p['dep_skor']:.1f} | {p['ev_kazanir']:.1%} | "
                     f"{'passed' if entry['selected'] else 'not selected'} |")
    perf = report['performance']
    rate = f"{perf['winner_accuracy']:.1%}" if perf['winner_accuracy'] is not None else 'not available'
    lines += ['', f"Settled: {perf['settled_games']}; pending: {perf['pending_games']}; winner accuracy: {rate}.", '',
              '| Fixture ID | Status | Final | Winner correct | Team MAE | Total error | Margin error | Total / margin in 80% |',
              '|---|---|---|---|---|---|---|---|']
    for check in report['settlements']:
        for g in check['games']:
            if g['status'] == 'final':
                lines.append(f"| {cell(g['event_id'])} | final | {g['actual_home']}–{g['actual_away']} | "
                             f"{g['winner_correct']} | {g['score_mae']:.2f} | {g['total_absolute_error']:.2f} | "
                             f"{g['margin_absolute_error']:.2f} | {g['total_in_80']} / {g['margin_in_80']} |")
            else:
                lines.append(f"| {cell(g['event_id'])} | pending | — | — | — | — | — | — |")
    if report['skipped']:
        lines += ['', '## Unresolved inputs', '']
        lines += [f"- {cell(item.get('event_id', item.get('league', item.get('record', ''))))}: {cell(item['reason'])}"
                  for item in report['skipped']]
    for code, outcome in report['sources'].items():
        if outcome['status'] == 'failed':
            lines += ['', f"Source refresh failed ({code}): {cell(outcome['error'])}"]
    return '\n'.join(lines + ['', report['note'], ''])
