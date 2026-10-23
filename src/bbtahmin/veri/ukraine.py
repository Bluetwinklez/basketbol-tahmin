"""Separate senior men's SuperLeague archive from the FBU's public widget.

Use its advertised full-season export, avoiding partial first-page training.
The export's result-only filter is required; same-day running scores are excluded.
"""
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
from bs4 import BeautifulSoup
from openpyxl import load_workbook

from .competitions import fetch, save
from .public_bytes import fetch_bytes
from .waba import html as widget_html

PAGE = 'https://fbu.ua/statistics/league-224/calendar'
SERVICE = 'https://widgets.baskethotel.com/widget-service/'


def team_catalog(html):
    options = BeautifulSoup(html, 'html.parser').select('select[id$="filter-team"] option[value]')
    teams = {}
    for option in options:
        if not option['value']: continue
        if not option['value'].isdigit(): raise ValueError('Invalid FBU team identity')
        teams[option.get_text(' ', strip=True)] = 'UKR_'+option['value']
    if len(teams) < 5: raise ValueError('Missing FBU senior team catalog')
    return teams


def parse_export(raw, year, catalog, captured, source_url, scheduled=False):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sum(f.file_size for f in archive.infolist()) > 15_000_000:
            raise ValueError('FBU workbook exceeds expanded size limit')
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
    rows = iter(workbook.active.values)
    title = next(rows); columns = next(rows)
    if title[:2] != ('SuperLeague', f'{year}-{year+1}') or columns[:8] != ('id', 'weekday', 'date', 'time', 'home team', 'away team', 'arena', 'score'):
        raise ValueError('Wrong FBU league, season or export columns')
    finals, fixtures, seen = [], [], set(); capture = pd.Timestamp(captured)
    for row in rows:
        if all(v is None for v in row): continue
        number, _, day, clock, home, away, venue, points, *_ = row
        if isinstance(number, bool) or not isinstance(number, (int, float, str)):
            raise ValueError('Invalid FBU game number')
        if not re.fullmatch(r'\d+(?:\.0+|/\d+)?', str(number)):
            raise ValueError('Invalid FBU game number')
        number = str(number).replace('/', 'x') if '/' in str(number) else str(int(float(number)))
        if home not in catalog or away not in catalog or catalog[home] == catalog[away]:
            raise ValueError('Unknown or identical FBU team')
        identity = f'UKR_{year}_N{number}_{catalog[home]}_{catalog[away]}'
        if identity in seen: raise ValueError('Duplicate FBU fixture identity')
        seen.add(identity)
        local = pd.to_datetime(f'{day} {clock}', format='%d/%m/%Y %H:%M:%S')
        when = local.tz_localize('Europe/Kyiv', ambiguous='raise', nonexistent='raise').tz_convert('UTC')
        if not year <= local.year <= year+1: raise ValueError('FBU date outside requested season')
        base = dict(mac_id=identity, lig='UKR', sezon=f'{year}-{str(year+1)[-2:]}',
                    tarih_utc=when, ev=catalog[home], dep=catalog[away], home_name=home, away_name=away,
                    source_url=source_url, captured_at_utc=captured, date_precision='timestamp',
                    source_timezone='Europe/Kyiv (federation local schedule)', venue_name=venue,
                    regulation_minutes=40, tarafsiz_saha=False, neutral_venue_verified=False,
                    status='scheduled' if scheduled and when > capture else 'unverified')
        match = re.fullmatch(r'(\d+)-(\d+)', str(points or ''))
        if not match: continue
        hs, ds = map(int, match.groups())
        if scheduled:
            if hs or ds: base['status'] = 'unverified'
            fixtures.append(base)
        elif min(hs, ds) > 0 and hs != ds and when < capture.floor('D'):
            finals.append(dict(base, status='final', ev_skor=hs, dep_skor=ds))
    workbook.close()
    return finals, fixtures


def collect(first=2020, last=None):
    now = pd.Timestamp.now(tz='UTC'); active = now.year if now.month >= 7 else now.year-1
    last = active if last is None else last
    if not 2009 <= first <= last <= active: raise ValueError('Invalid Ukraine season bounds')
    page = fetch(PAGE, refresh=True)
    if not re.search(r'leagueID:\s*224\b', page): raise ValueError('Not the FBU senior men league')
    config = fetch('https://fbu.ua/js/script-federation.js', refresh=True)
    api = re.search(r'MBT\.API\.ApiId\s*=\s*"([a-z0-9]+)"', config)
    if not api: raise ValueError('Missing published FBU widget identifier')
    common = dict(api=api[1], lang='en', nnav='1')
    def initial(season=None):
        params = {**common, 'request[0][container]': 'schedule-long', 'request[0][widget]': '303',
                  'request[0][param][league_id]': '224', 'request[0][param][show_season_selector]': '1'}
        if season: params['request[0][param][season_id]'] = season
        return widget_html(fetch(SERVICE+'show?'+urlencode(params), refresh=season is None or season == current_id))
    current_id = None
    initial_html = initial(); soup = BeautifulSoup(initial_html, 'html.parser')
    seasons = {}
    for option in soup.select('select[id$="filter-season"] option'):
        label = option.get_text(strip=True)
        if label in seasons: seasons[label] = None  # Ambiguous old seasons require manual review.
        else: seasons[label] = option['value']
    current_id = seasons.get(f'{active}-{active+1}')
    records, fixtures, teams, sources, counts, errors = [], [], {}, [], [], []
    for year in range(first, last+1):
        sid = seasons.get(f'{year}-{year+1}')
        if sid is None: raise ValueError('Missing or ambiguous FBU senior season')
        season_html = initial_html if sid == current_id else initial(sid)
        selected = BeautifulSoup(season_html, 'html.parser').select_one('select[id$="filter-season"] option[selected]')
        if selected is None or selected.get('value') != sid: raise ValueError('FBU returned a different season')
        catalog = team_catalog(season_html)
        for name, key in catalog.items():
            previous = teams.get(key, {})
            teams[key] = dict(name=name, aliases=sorted(set(previous.get('aliases', [])+[previous.get('name', name)])))
        for kind in (['results_only', 'schedule_only'] if year == active else ['results_only']):
            url = SERVICE+'export/view/schedule_and_results?'+urlencode(dict(api=api[1], season_id=sid, lang='en', type=kind))
            raw = fetch_bytes(url, refresh=year == active)
            r, f = parse_export(raw, year, catalog, now.isoformat(), url, kind == 'schedule_only')
            records += r; fixtures += f; sources.append(url)
            counts.append(dict(year=year, provider_season=sid, export_type=kind, finals=len(r), fixtures=len(f)))
        print('Ukraine', year, counts[-1], flush=True)
    result = save('UKR', records, fixtures, teams, sources, errors)
    target = Path('docs/kanit/competitions/UKR_collection.json'); report = json.loads(target.read_text())
    report.update(counts=counts, source=PAGE, timezone='Europe/Kyiv',
        limitations='Only published result-only exports, no same-day finals. Wartime interruptions, neutral/bubble venues and historical publication times are not independently certified.')
    target.write_text(json.dumps(report, indent=2))
    return result
