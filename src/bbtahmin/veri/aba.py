"""Senior men's ABA League numeric facts from the official season calendar.

The calendar calls Central European wall clocks CET even in summer. Interpret
them in Europe/Belgrade, including DST. Same-day scores are not certified finals.
"""
import json
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from .competitions import fetch

BASE = 'https://www.aba-liga.com'
CODE = 'ABA'


def parse_calendar(html, year, captured_at):
    soup = BeautifulSoup(html, 'html.parser')
    selected = soup.select_one('select#season option[selected]')
    if selected is None or selected.get('value') != f'{year % 100}/1/':
        raise ValueError('Wrong ABA season or division; refusing fallback')
    captured = pd.Timestamp(captured_at)
    if captured.tzinfo is None:
        raise ValueError('Timezone-aware capture required')
    records, fixtures, teams, omitted = [], [], {}, 0
    for tr in soup.select('tr'):
        link = tr.select_one('p.hidden-xs a[href*="/match/"]')
        short = tr.select_one('p.visible-xs a[href*="/match/"]')
        score, clock = tr.select_one('.scoretable'), tr.select_one('.locationtable')
        if not link or not short or score is None or clock is None:
            continue
        match = re.fullmatch(r'https://www\.aba-liga\.com/match/(\d+)/(\d+)/1/(?:Overview|Preview)/[^?#]+', link['href'])
        if not match or int(match[2]) != year % 100:
            raise ValueError('Wrong ABA match identity')
        names = link.get_text(' ', strip=True).split(' : ')
        codes = short.get_text(' ', strip=True).split(' : ')
        if names == [':'] and codes == [':'] and not score.get_text(strip=True):
            omitted += 1  # Undrawn playoff placeholders have no team identities.
            continue
        if len(names) != 2 or len(codes) != 2 or any(not re.fullmatch('[A-Z0-9]{2,5}', c) for c in codes) or codes[0] == codes[1]:
            raise ValueError('Malformed ABA team identities')
        for code, name in zip(codes, names):
            teams['ABA_' + code] = dict(name=name, aliases=[code])
        raw_clock = clock.get_text(' ', strip=True)
        date = re.search(r'(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+CET', raw_clock)
        if date is None:
            omitted += 1
            continue
        when = pd.to_datetime(f'{date[1]} {date[2]}', format='%d.%m.%Y %H:%M').tz_localize('Europe/Belgrade', ambiguous='raise', nonexistent='raise').tz_convert('UTC')
        if not year <= when.year <= year + 1:
            raise ValueError('ABA date outside requested season')
        score_text = score.get_text(' ', strip=True)
        base = dict(mac_id=f'ABA_{year}_{match[1]}', lig='ABA', sezon=f'{year}-{str(year+1)[-2:]}',
                    tarih_utc=when, ev='ABA_'+codes[0], dep='ABA_'+codes[1],
                    home_name=names[0], away_name=names[1], source_url=link['href'],
                    captured_at_utc=captured.isoformat(), date_precision='timestamp',
                    regulation_minutes=40, tarafsiz_saha=False,
                    status='scheduled' if not score_text and when > captured else 'unverified')
        fixtures.append(base)
        points = re.fullmatch(r'(\d+)\s*:\s*(\d+)(?:\s*\([^)]*\))?', score_text)
        # A calendar live score is not an official final flag. Only prior UTC
        # days enter training/settlement; never certify today's running score.
        if points and when < captured.floor('D') and not re.search('live|playing', str(score.get('class', [])), re.I):
            hs, ds = int(points[1]), int(points[2])
            if min(hs, ds) > 0 and hs != ds:
                records.append(dict(base, status='final', ev_skor=hs, dep_skor=ds))
    if not fixtures:
        raise ValueError('No dated senior ABA fixtures')
    if len({r['mac_id'] for r in fixtures}) != len(fixtures):
        raise ValueError('Duplicate ABA match IDs')
    return records, fixtures, teams, omitted


def collect(first=2010, last=None, refresh=False):
    now = pd.Timestamp.now(tz='UTC')
    active = now.year if now.month >= 7 else now.year - 1
    last = active if last is None else last
    if not 2001 <= first <= last <= active:
        raise ValueError('Invalid ABA season bounds')
    root = Path('data/competitions'); root.mkdir(parents=True, exist_ok=True)
    records, fixtures, teams, sources, errors, omitted = [], [], {}, [], [], 0
    for year in range(first, last+1):
        url = f'{BASE}/calendar/{year % 100}/1/'
        try:
            html = fetch(url, refresh=refresh or year == active)
            r, f, t, n = parse_calendar(html, year, now)
            records += r; fixtures += f; sources.append(url); omitted += n
            for key, entry in t.items():
                previous = teams.get(key, {})
                entry['aliases'] = sorted(set(entry['aliases'] + previous.get('aliases', []) + ([previous['name']] if previous else [])))
                teams[key] = entry
        except Exception as exc:
            errors.append(dict(year=year, error=f'{type(exc).__name__}: {exc}'))
    if not fixtures or not records and not (root/'ABA.parquet').exists():
        raise ValueError(f'No usable ABA archive: {errors}')
    from .competitions import save
    # Use the same validated, conflict-rejecting persistence as other European
    # competitions; an unchanged result gains fresh provenance on refresh.
    g = save('ABA', records, fixtures, teams, sources, errors)
    report_path = Path('docs/kanit/competitions/ABA_collection.json')
    report = json.loads(report_path.read_text())
    report.update(omitted_undated=omitted, captured_at_utc=now.isoformat(),
                  final_rule='Only positive non-tied scores from earlier UTC days; same-day calendar scores unverified.',
                  timezone='Europe/Belgrade (calendar labels summer clocks CET)',
                  identity='League-scoped official abbreviations; sponsor aliases preserved; no cross-league merge.')
    report_path.write_text(json.dumps(report, indent=2))
    if errors:
        print(json.dumps(dict(partial_errors=errors), indent=2), flush=True)
    return g
