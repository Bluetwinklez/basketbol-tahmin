"""Senior women match facts from the federation's public statistics backend.

The same endpoint contains undated playoff SERIES totals. Those are not games.
CONFIRMED alone never establishes a completed basketball result.
"""
import json
import pandas as pd
from .competitions import fetch
from .regional import save, key

BASE = 'https://basket.fi/wp-json/basket/v1/pena-api/api/v1/'


def competition(rows):
    choices = [r for r in rows if (r.get('name'), r.get('gender'), r.get('age_group_code')) ==
               ('Naisten Korisliiga', 'FEMALE', 'SENIOR')]
    if len(choices) != 1:
        raise ValueError('Ambiguous senior women competition')
    return choices[0]


def parse(payload, comp, season, year, url, captured):
    if (payload.get('competition_public_id'), payload.get('season_public_id')) != (comp, season):
        raise ValueError('Wrong Finnish competition or season response')
    games = payload['games']
    if payload.get('count') != len(games):
        raise ValueError('Potentially incomplete Finnish response')
    result = []; excluded = 0
    for r in games:
        if r.get('deleted_at') or r.get('status') != 'CONFIRMED' or not r.get('time'):
            excluded += 1; continue
        when = pd.Timestamp(r['time'])
        if when.tzinfo is None:
            raise ValueError('Missing Finnish timezone')
        hs, ds = r.get('score_a'), r.get('score_b')
        if (type(hs) is not int or type(ds) is not int or min(hs, ds) <= 0 or hs == ds
                or when >= pd.Timestamp(captured)):
            excluded += 1; continue
        if not year <= when.year <= year + 1:
            raise ValueError('Out-of-season Finnish result')
        # Exact aliases only within the verified senior-women competition.
        names = [r.get('team_' + side + '_name_fi') or r['team_' + side + '_name_en'] for side in ('a', 'b')]
        identity = lambda n: 'ECW_66458' if n in ('HBA-Märsky', 'HBA-Marsky') else key('FI_W_', n)
        result.append(dict(mac_id='FI_W_' + r['game_public_id'], lig='FI_W_KL', sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when, ev=identity(names[0]), dep=identity(names[1]), ev_skor=hs, dep_skor=ds,
            home_name=names[0], away_name=names[1], gender='Women', regulation_minutes=40, tarafsiz_saha=False,
            source_url=url, captured_at_utc=captured, available_at_utc=None, date_precision='timestamp',
            source_status=r['status'], source_provider=r.get('picked_source'), phase=r.get('phase'),
            venue_name=r.get('arena_name_fi'), neutral_venue_verified=False))
    return result, excluded


def collect(years=(2022, 2023, 2024, 2025, 2026)):
    comp = competition(json.loads(fetch(BASE + 'competitions', refresh=True))['competitions'])
    cid = comp['public_id']; prefix = BASE + 'competitions/' + cid + '/seasons'
    catalog = json.loads(fetch(prefix, refresh=True))
    if catalog.get('competition_public_id') != cid:
        raise ValueError('Unrelated season catalog')
    rows = []; sources = []; counts = []; captured = pd.Timestamp.now(tz='UTC').isoformat()
    for year in years:
        choices = [s for s in catalog['seasons'] if str(s.get('season_start_year')) == str(year) and str(s.get('season_end_year')) == str(year+1)]
        if len(choices) != 1:
            raise ValueError('Ambiguous Finnish season')
        sid = choices[0]['season_public_id']; url = prefix + '/' + sid + '/games'
        data = json.loads(fetch(url, refresh=year >= 2026))
        games, excluded = parse(data, cid, sid, year, url, captured)
        rows += games; sources.append(url); counts.append(dict(year=year, listed=len(data['games']), accepted=len(games), excluded=excluded))
        print('Finland', year, len(games), flush=True)
    return save('FI_W_KL', rows, dict(source='Finnish Basketball Association public statistics backend', sources=sources,
        captured_at_utc=captured, counts=counts, explicit_mapping={'HBA-Märsky': 'ECW_66458'},
        coverage='All returned dated, confirmed, positive non-tied senior-women results. Undated playoff series totals excluded. Response counts checked; independent completeness, historical publication time, overtime and neutral venues unverified.'))


if __name__ == '__main__': collect()
