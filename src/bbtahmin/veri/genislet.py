"""Additive, restartable historical backfill. Never replaces existing game results.

NBA: sportsdataverse's ESPN schedule/team/player release archives (ending years).
Europe: official EuroLeague/EuroCup season API (starting years).
All downloaded data is cached; each source failure is recorded independently.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import euroleague
from .http import CachedHTTP
from .nba_kutu import ESPN_KOD
from .schema import normalize
from .teams import team_code

RELEASE = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download'
HISTORICAL = {'NJ': 'BRK', 'NJN': 'BRK', 'SEA': 'OKC', 'VAN': 'MEM',
              'CHH': 'NOP', 'NOH': 'NOP', 'NOK': 'NOP', 'WSB': 'WAS'}


def download(tag, name, year, refresh=False):
    """An interrupted request must not corrupt a reusable cache entry."""
    path = Path('data/raw/espn') / f'{name}_{year}.parquet'
    url = f'{RELEASE}/{tag}/{path.name}'
    if refresh or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers={'User-Agent': 'bbtahmin/0.1'})
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
        temporary = path.with_suffix('.part')
        temporary.write_bytes(raw)
        try:
            pd.read_parquet(temporary)  # validate before replacing a good cache
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return pd.read_parquet(path), url


def nba_code(abbreviation, name, ending_year):
    # The original Charlotte Hornets became New Orleans in 2002. The current
    # Charlotte team is a separate franchise; a display-name-only join is wrong.
    if name == 'Charlotte Hornets' and ending_year <= 2002:
        return 'NOP'
    abbreviation = str(abbreviation).upper()
    return HISTORICAL.get(abbreviation) or ESPN_KOD.get(abbreviation) or team_code(name)


def halftime(value):
    """Release line scores are strings of dicts, sometimes numpy-array reprs."""
    if not isinstance(value, str):
        return None
    scores = {}
    for part in re.findall(r'\{[^{}]*\}', value):
        period = re.search(r"'period':\s*([\d.]+)", part)
        points = re.search(r"'value':\s*([\d.]+)", part)
        if period and points:
            scores[int(float(period[1]))] = float(points[1])
    return int(scores[1] + scores[2]) if 1 in scores and 2 in scores else None


def nba_rows(schedule, ending_year, source):
    rows, mapping, rejected = [], {}, []
    for r in schedule.to_dict('records'):
        if r.get('season_type') not in (2, 3) or r.get('status_type_completed') != True:
            continue
        try:
            if pd.notna(r.get('season')) and int(r['season']) != ending_year:
                raise ValueError('record belongs to a different season')
            h, a = [nba_code(r.get(f'{side}_abbreviation'), r[f'{side}_display_name'], ending_year)
                    for side in ('home', 'away')]
            hs, away = float(r['home_score']), float(r['away_score'])
            if hs <= 0 or away <= 0 or hs == away or not hs.is_integer() or not away.is_integer():
                raise ValueError('invalid final score')
            date = pd.to_datetime(r['date'], utc=True)
            if pd.isna(date):
                raise ValueError('missing date')
            local = pd.Timestamp(r['game_date']) if pd.notna(r.get('game_date')) else date.tz_convert('America/New_York')
            identifier = f'NBA_{local:%Y%m%d}0{h}'
            mapping[str(r['game_id'])] = identifier
            period = r.get('status_period')
            rows.append(dict(mac_id=identifier, lig='NBA', sezon=f'{ending_year-1}-{str(ending_year)[-2:]}',
                             tarih_utc=date, ev=h, dep=a, ev_skor=int(hs), dep_skor=int(away),
                             uzatma=bool(pd.notna(period) and float(period) > 4),
                             ev_iy=halftime(r.get('home_linescores')), dep_iy=halftime(r.get('away_linescores')),
                             tarafsiz_saha=r.get('neutral_site') if pd.notna(r.get('neutral_site')) else None,
                             asama='playoff' if r['season_type'] == 3 else 'normal', kaynak=source))
        except (ValueError, KeyError, TypeError) as exc:
            rejected.append(dict(game_id=str(r.get('game_id')), error=str(exc)))
    return rows, mapping, rejected


def merge_games(existing, incoming):
    """Preserve results and IDs; enrich matching scores, quarantine conflicts."""
    records = {r['mac_id']: r for r in existing.to_dict('records')}
    by_result = {}
    result_columns = ('lig','sezon','ev','dep','ev_skor','dep_skor')
    for old in records.values():
        by_result.setdefault(tuple(old[c] for c in result_columns), []).append(old)
    added, enriched, conflicts = 0, 0, []
    for r in incoming:
        key = r['mac_id']
        if key not in records:
            # Some ESPN records have the local date shifted by one day. Adding
            # them under a new ID would silently count a real game twice.
            candidates = by_result.get(tuple(r[c] for c in result_columns), [])
            duplicates = [old for old in candidates if old['kaynak'] != r['kaynak'] and
                          abs(pd.Timestamp(old['tarih_utc'])-pd.Timestamp(r['tarih_utc'])) <= pd.Timedelta(hours=36)]
            if duplicates:
                conflicts.append(dict(mac_id=key,reason='possible duplicate with shifted source date',
                                      existing_mac_ids=[d['mac_id'] for d in duplicates],source=r['kaynak']))
                continue
            records[key] = r
            by_result.setdefault(tuple(r[c] for c in result_columns), []).append(r)
            added += 1
            continue
        old = records[key]
        if any(old[c] != r[c] for c in ('lig', 'sezon', 'ev', 'dep', 'ev_skor', 'dep_skor')):
            conflicts.append(dict(mac_id=key, existing={c: str(old[c]) for c in ('ev', 'dep', 'ev_skor', 'dep_skor')},
                                  incoming={c: str(r[c]) for c in ('ev', 'dep', 'ev_skor', 'dep_skor')}, source=r['kaynak']))
            continue
        changed = False
        for col in ('ev_iy', 'dep_iy', 'tarafsiz_saha'):
            # ESPN explicitly identifies neutral courts, including the 2020 bubble.
            if pd.notna(r[col]) and (pd.isna(old[col]) or (col == 'tarafsiz_saha' and bool(r[col]))):
                if pd.isna(old[col]) or old[col] != r[col]:
                    old[col], changed = r[col], True
        enriched += changed
    return normalize(list(records.values())), dict(added=added, enriched=enriched, conflicts=conflicts)


def save_table(rows, path, keys):
    """Keep previously collected seasons when a remote season fails."""
    path = Path(path)
    table = pd.DataFrame(rows)
    if path.exists():
        table = pd.concat([pd.read_parquet(path), table], ignore_index=True)
    if not table.empty:
        if 'athlete_id' in keys:
            table['athlete_id'] = pd.to_numeric(table.athlete_id,errors='coerce')
            table = table[table.athlete_id.notna()].copy()
            table['athlete_id'] = table.athlete_id.astype('Int64')
        if 'oyuncu' in keys:
            # A nullable numeric ESPN ID can arrive as 3934719.0; it is the
            # same athlete as the existing string ID "3934719".
            table['oyuncu'] = table.oyuncu.astype(str).str.replace(r'\.0$','',regex=True)
        table = table.drop_duplicates(keys, keep='last')
        temporary = path.with_suffix('.part')
        table.to_parquet(temporary, index=False,compression='zstd',compression_level=9)
        os.replace(temporary, path)
    return len(table)


def run(start=1993, end=None, details=True, europe=True, nba=True):
    """Years are season START years. Current season is refreshed on every run."""
    now = pd.Timestamp.now(tz='UTC')
    current = now.year if now.month >= 7 else now.year - 1
    end = current if end is None else end
    if start > end:
        raise ValueError('start must not be after end')
    path = Path('data/maclar.parquet')
    games = pd.read_parquet(path) if path.exists() else normalize([])
    before = len(games)
    status, merges = [], []
    Path('data').mkdir(exist_ok=True)
    Path('docs/kanit').mkdir(parents=True, exist_ok=True)
    http = CachedHTTP()
    if europe:
        for league, first in [('E', 2000), ('U', 2002)]:
            if isinstance(europe, (list, tuple, set)) and league not in europe:
                continue
            for year in range(max(start, first), end + 1):
                item = dict(lig=league, sezon=f'{year}-{str(year+1)[-2:]}')
                try:
                    rows, detail = euroleague.collect(http, league, year, refresh=year == current)
                    games, merge = merge_games(games, rows)
                    merges.append(merge)
                    item.update(status='ok', **detail, added=merge['added'])
                    games.to_parquet(path, index=False)
                except Exception as exc:
                    item.update(status='error', error=str(exc))
                status.append(item)
                print(json.dumps(item, ensure_ascii=False), flush=True)
    if nba:
        for year in range(max(start, 1993) + 1, end + 2):
            item = dict(lig='NBA', sezon=f'{year-1}-{str(year)[-2:]}')
            try:
                schedule, source = download('espn_nba_schedules', 'nba_schedule', year, refresh=year-1 == current)
                rows, mapping, rejected = nba_rows(schedule, year, source)
                games, merge = merge_games(games, rows)
                merges.append(merge)
                item.update(status='ok', added=merge['added'], enriched=merge['enriched'],
                            listed=len(schedule), accepted=len(rows), rejected=rejected)
                games.to_parquet(path, index=False)
                # Do not attach statistics from a conflicting result to an existing game.
                invalid = {r['mac_id'] for r in merge['conflicts']}
                mapping = {k: v for k, v in mapping.items() if v not in invalid}
                context = schedule.copy()
                context['mac_id'] = context.game_id.astype(str).map(mapping)
                context = context[context.mac_id.notna()]
                context_columns = ['mac_id','game_id','date','neutral_site','venue_id','venue_full_name',
                                   'venue_address_city','venue_address_state','status_period','season','season_type']
                context = context[[c for c in context_columns if c in context]].copy()
                context['kaynak'] = source
                save_table(context.to_dict('records'),'data/nba_mac_baglami.parquet',['mac_id'])
                if details:
                    for tag, name, output, role, player in [
                        ('espn_nba_team_boxscores', 'team_box', 'nba_takim_istatistik', 'team_home_away', None),
                        ('espn_nba_player_boxscores', 'player_box', 'nba_oyuncu_istatistik', 'home_away', 'athlete_id')]:
                        try:
                            raw, detail_source = download(tag, name, year, refresh=year-1 == current)
                            raw['mac_id'] = raw.game_id.astype(str).map(mapping)
                            raw = raw[raw.mac_id.notna()].copy()
                            raw['rol'] = raw[role].map({'home': 'ev', 'away': 'dep'})
                            columns = ['mac_id', 'rol', 'game_id', 'season', 'season_type',
                                       'field_goals_made', 'field_goals_attempted', 'three_point_field_goals_made',
                                       'three_point_field_goals_attempted', 'free_throws_made', 'free_throws_attempted',
                                       'offensive_rebounds', 'defensive_rebounds', 'rebounds', 'assists', 'steals',
                                       'blocks', 'turnovers', 'total_turnovers', 'fouls', 'points', 'team_score',
                                       'minutes', 'plus_minus', 'athlete_id', 'athlete_display_name', 'team_id']
                            out = raw[[c for c in columns if c in raw]].copy()
                            out['kaynak'] = detail_source
                            keys = ['mac_id', 'rol'] + ([player] if player else [])
                            save_table(out.to_dict('records'), f'data/{output}.parquet', keys)
                            item[output] = len(out)
                        except Exception as exc:
                            item[f'{output}_error'] = str(exc)
            except Exception as exc:
                item.update(status='error', error=str(exc))
            status.append(item)
            print(json.dumps(dict(item,rejected_count=len(item.get('rejected',[])),
                                  rejected=item.get('rejected',[])[:3]), ensure_ascii=False), flush=True)
    for filename in ('nba_mac_baglami','nba_takim_istatistik','nba_oyuncu_istatistik'):
        detail_path = Path(f'data/{filename}.parquet')
        if detail_path.exists():
            table = pd.read_parquet(detail_path)
            table = table[table.mac_id.isin(games.mac_id)]
            table.to_parquet(detail_path,index=False)
    if nba and details:
        materialize_boxes(games)
    coverage = games.groupby(['lig', 'sezon']).size().rename('mac_sayisi').reset_index()
    coverage.to_csv('docs/kanit/genislet_kapsam.csv', index=False)
    report = dict(timestamp=datetime.now(timezone.utc).isoformat(), before=before, after=len(games),
                  added=len(games)-before, enriched=sum(m['enriched'] for m in merges),
                  conflicts=[c for m in merges for c in m['conflicts']], sources=status,
                  note='Additional data is not evidence of increased predictive accuracy. Re-run chronological evaluation.')
    Path('docs/kanit/genislet.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf8')
    return report


def materialize_boxes(games):
    """Make expanded detail tables usable by the existing pregame box features."""
    path = Path('data/nba_takim_istatistik.parquet')
    if path.exists():
        t = pd.read_parquet(path)
        required = ['field_goals_attempted','three_point_field_goals_attempted','free_throws_attempted',
                    'offensive_rebounds','defensive_rebounds','total_turnovers','fouls','team_score']
        for c in required:
            t[c] = pd.to_numeric(t[c], errors='coerce')
        # Both sides need complete stats; partial box scores must not become zeros.
        t = t.dropna(subset=required)
        complete = t.groupby('mac_id').rol.nunique()
        t = t[t.mac_id.isin(complete[complete == 2].index)]
        periods = {}
        context = Path('data/nba_mac_baglami.parquet')
        if context.exists():
            c = pd.read_parquet(context)
            periods = c.set_index('mac_id').status_period.to_dict()
        overtime = games.set_index('mac_id').uzatma.fillna(False).to_dict()
        def duration(mac):
            p = periods.get(mac)
            extra = max(0, float(p)-4) if pd.notna(p) else int(overtime.get(mac, False))
            return 2880. + 300.*extra
        output = pd.DataFrame(dict(mac_id=t.mac_id, rol=t.rol, say=t.team_score,
                                   fga2=t.field_goals_attempted-t.three_point_field_goals_attempted,
                                   fga3=t.three_point_field_goals_attempted, fta=t.free_throws_attempted,
                                   oreb=t.offensive_rebounds,dreb=t.defensive_rebounds,tov=t.total_turnovers,
                                   faul=t.fouls,sure=t.mac_id.map(duration)))
        save_table(output.to_dict('records'),'data/kutu_nba.parquet',['mac_id','rol'])
    path = Path('data/nba_oyuncu_istatistik.parquet')
    if path.exists():
        p = pd.read_parquet(path)
        p['minutes'] = pd.to_numeric(p.minutes, errors='coerce')
        p = p[p.minutes > 0]
        output = pd.DataFrame(dict(mac_id=p.mac_id,rol=p.rol,oyuncu=p.athlete_id.astype(str),saniye=p.minutes*60))
        save_table(output.to_dict('records'),'data/oyuncular_nba.parquet',['mac_id','rol','oyuncu'])
