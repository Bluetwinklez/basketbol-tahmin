"""Turkish men's BSL: TBLStat historical facts and beIN current fixtures.

Historical calendar days stay day precision. Current standings never pretend
to supply exact final tipoff timestamps; pending forecasts need full match data.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from ..takim_ad import anahtar
from .competitions import fetch, save

ARCHIVE = 'https://bsl.tblstat.net'
CURRENT = 'https://beinsports.com.tr/lig/basketbol-super-ligi/'
# Explicit same-club source identities, checked against both public catalogs.
# 12998 is an additional provider listing and deliberately has no guessed merge.
BEIN_IDS = {11774:81,10824:1,10818:78,12031:86,10822:79,12704:92,10817:4,
            10819:9,10813:10,13000:94,10811:11,12999:95,10823:20,12705:93,10812:3,11775:84}
MONTHS = {anahtar(name):i for i,name in enumerate(
    ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'], 1)}


def catalog(html, year):
    soup = BeautifulSoup(html, 'html.parser'); token = f'{year%100:02d}{(year+1)%100:02d}'
    meta = soup.select_one('meta[name="description"]')
    if meta is None or 'Basketbol Süper Ligi' not in meta.get('content', '') or f'{year}-{str(year+1)[-2:]}' not in meta['content']:
        raise ValueError('Wrong Turkish senior league/season')
    names = {}
    for a in soup.select('a[onclick]'):
        match = re.fullmatch(r"go\('team/(\d+)/"+token+r"'\)", a['onclick'])
        if match:
            name = a.get_text(' ', strip=True)
            if name: names[anahtar(name)] = ('TR_BSL_'+match[1], name)
    if len(names) < 8: raise ValueError('Incomplete Turkish team catalog')
    return names


def team_dates(html, year):
    soup = BeautifulSoup(html, 'html.parser')
    if f'{year}-{str(year+1)[-2:]}' not in soup.title.get_text():
        raise ValueError('Wrong Turkish team season')
    dates = {}
    for a in soup.select('a[onclick]'):
        match = re.fullmatch(r"go\('game/(\d+)'\)", a['onclick'])
        if not match: continue
        tr = a.find_parent('tr'); cells = tr.find_all('td', recursive=False)
        if len(cells) != 4: continue
        text = cells[1].get_text(strip=True)
        if not re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', text): continue
        date = pd.to_datetime(text, format='%d.%m.%Y').tz_localize('UTC')
        if not year <= date.year <= year+1: raise ValueError('Turkish team date outside season')
        dates[match[1]] = date
    return dates


def historical(html, year, teams, captured, source_url, dates=None):
    soup = BeautifulSoup(html, 'html.parser')
    if f'{year}-{str(year+1)[-2:]}' not in soup.title.get_text(): raise ValueError('Wrong Turkish result season')
    records = []
    for tr in soup.select('table.gday tr'):
        cells = tr.find_all('td', recursive=False)
        if len(cells) not in (3,4): continue
        offset = int(len(cells)==4)
        match = re.fullmatch(r'(\d+)\s*-\s*(\d+)(?:\s+(UZ))?', cells[1+offset].get_text(' ', strip=True))
        link = cells[1+offset].find('a', onclick=re.compile(r"go\('game/\d+'\)"))
        if not match or link is None: continue
        gid = re.search(r'game/(\d+)', link['onclick'])[1]
        date = (pd.to_datetime(cells[0].get_text(strip=True), format='%d.%m.%Y').tz_localize('UTC')
                if offset else (dates or {}).get(gid))
        if date is None: continue
        if not year <= date.year <= year+1: raise ValueError('Turkish date outside season')
        hs, ds = int(match[1]), int(match[2])
        if min(hs, ds) <= 0 or hs == ds or date >= pd.Timestamp(captured).floor('D'): continue
        keys = [anahtar(cells[i].get_text(' ', strip=True)) for i in (offset,2+offset)]
        if any(k not in teams for k in keys): raise ValueError('Unknown historical Turkish team')
        home, away = (teams[k][0] for k in keys)
        gid = re.search(r'game/(\d+)', link['onclick'])[1]
        records.append(dict(mac_id='TR_BSL_T'+gid, lig='TR_BSL', sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=date, ev=home, dep=away, ev_skor=hs, dep_skor=ds,
            home_name=teams[keys[0]][1], away_name=teams[keys[1]][1],
            source_url=ARCHIVE+'/game/'+gid, listing_url=source_url, captured_at_utc=captured,
            date_precision='day', regulation_minutes=40, tarafsiz_saha=False, overtime=bool(match[3])))
    return records


def next_data(html, year):
    script = BeautifulSoup(html, 'html.parser').select_one('#__NEXT_DATA__')
    if script is None: raise ValueError('Missing beIN fixture data')
    payload = json.loads(script.get_text())['props']['pageProps']
    if payload.get('slug') != 'basketbol-super-ligi' and payload.get('rewriteId') != 'basketbol-super-ligi':
        raise ValueError('Wrong beIN league')
    if payload['orgData']['activeOrganization']['id'] != 393 or payload['orgData']['activeSeason']['name'] != f'{year}/{year+1}':
        raise ValueError('Wrong beIN competition/season')
    return payload


def identity(home, away, when):
    day = when.tz_convert('Europe/Istanbul').strftime('%Y%m%d')
    return f'TR_BSL_B{day}_{home}_{away}'


def fixtures(payload, year, captured, identities=None):
    result = []
    for row in payload['data']:
        if row['league']['id'] != 393 or row['league']['sportId'] != 23: raise ValueError('Mixed beIN competition')
        h, a = row['homeTeam'], row['awayTeam']
        if h['id'] not in BEIN_IDS or a['id'] not in BEIN_IDS: raise ValueError('Unverified beIN team mapping')
        home, away = ('TR_BSL_'+str(BEIN_IDS[t['id']]) for t in (h,a))
        # The rendered 23 Oct 19:00 Istanbul fixture is 16:00 in this feed,
        # cross-checked against the federation's dated weekly programme.
        when = pd.Timestamp(row['matchDate'])
        when = when.tz_localize('UTC') if when.tzinfo is None else when.tz_convert('UTC')
        if not year <= when.year <= year+1: raise ValueError('beIN date outside season')
        provider_id=str(row['id'])
        if not provider_id.isdecimal(): raise ValueError('Invalid beIN fixture ID')
        stable_key=f'{year}:{provider_id}'
        event_id=(identities or {}).get(stable_key, f'TR_BSL_BID{year}_{provider_id}')
        result.append(dict(mac_id=event_id, lig='TR_BSL', sezon=f'{year}-{str(year+1)[-2:]}',
            tarih_utc=when, ev=home, dep=away, home_name=h['name'].strip(), away_name=a['name'].strip(),
            source_url=CURRENT+'fikstur', source_event_id=str(row['id']), captured_at_utc=captured,
            date_precision='timestamp', regulation_minutes=40, tarafsiz_saha=False,
            status='scheduled' if row['liteMatchStatus']=='preMatch' and when>pd.Timestamp(captured) else 'unverified'))
    return result


def recent_results(payload, year, captured):
    result = {}
    def walk(value):
        if isinstance(value, list):
            for item in value: walk(item)
        elif isinstance(value, dict):
            if {'homeTeamScore','awayTeamScore','homeTeamLogo','awayTeamLogo','niceDate'} <= value.keys():
                m = re.fullmatch(r'(\d+)\s+(\S+)\s+(\d{4})', value['niceDate'])
                if not m or anahtar(m[2]) not in MONTHS: raise ValueError('Unknown beIN result date')
                date = pd.Timestamp(year=int(m[3]), month=MONTHS[anahtar(m[2])], day=int(m[1]), tz='UTC')
                if not year <= date.year <= year+1: raise ValueError('beIN result outside season')
                ids = [re.search(r'/B(\d+)\.png', value[k]) for k in ('homeTeamLogo','awayTeamLogo')]
                if not all(ids) or any(int(m[1]) not in BEIN_IDS for m in ids): raise ValueError('Unknown beIN result team')
                home, away = ['TR_BSL_'+str(BEIN_IDS[int(m[1])]) for m in ids]
                hs, ds = value['homeTeamScore'], value['awayTeamScore']
                if type(hs) is not int or type(ds) is not int or min(hs,ds)<=0 or hs==ds: raise ValueError('Invalid beIN final score')
                if date >= pd.Timestamp(captured).floor('D'): return
                gid = identity(home, away, date)
                row = dict(mac_id=gid, lig='TR_BSL', sezon=f'{year}-{str(year+1)[-2:]}', tarih_utc=date,
                    ev=home, dep=away, ev_skor=hs, dep_skor=ds, home_name=value['homeTeamName'], away_name=value['awayTeamName'],
                    source_url=CURRENT+'puan-durumu', captured_at_utc=captured, date_precision='day',
                    regulation_minutes=40, tarafsiz_saha=False)
                if gid in result and any(result[gid][k]!=row[k] for k in ('ev_skor','dep_skor')): raise ValueError('Conflicting beIN result copies')
                result[gid] = row
            else:
                for item in value.values(): walk(item)
    walk(payload['data'])
    return list(result.values())


def collect(first=2016, last=None):
    now = pd.Timestamp.now(tz='UTC'); active = now.year if now.month>=7 else now.year-1
    last = active if last is None else last
    if not 2002 <= first <= last <= active: raise ValueError('Invalid Turkey season bounds')
    records, teams, sources, errors = [], {}, [], []
    for year in range(first, min(last, active-1)+1):
        token=f'{year%100:02d}{(year+1)%100:02d}'; url=ARCHIVE+'/games/'+token
        cats=catalog(fetch(ARCHIVE+'/teams/'+token),year)
        dates = {}
        team_urls = [ARCHIVE+'/team/'+code.removeprefix('TR_BSL_')+'/'+token for code,_ in cats.values()]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for page in pool.map(fetch, team_urls):
                for gid,date in team_dates(page,year).items():
                    if gid in dates and dates[gid]!=date: raise ValueError('Conflicting Turkish team dates')
                    dates[gid]=date
        r=historical(fetch(url),year,cats,now.isoformat(),url,dates);records+=r;sources.extend([url]+team_urls)
        for key,name in cats.values():
            old=teams.get(key,{})
            teams[key]=dict(name=name,aliases=sorted(set(old.get('aliases',[])+[old.get('name',name)])))
        print('Turkey',year,len(r),flush=True)
    scheduled = []
    registry_path=Path('data/competitions/TR_BSL_fixture_ids.json')
    registry=json.loads(registry_path.read_text()) if registry_path.exists() else {}
    previous_path=Path('data/competitions/TR_BSL_fixtures.parquet')
    if previous_path.exists():
        previous=pd.read_parquet(previous_path)
        if 'source_event_id' in previous:
            for item in previous.to_dict('records'):
                provider=str(item['source_event_id']);season_year=str(item['sezon'])[:4]
                registry.setdefault(f'{season_year}:{provider}',item['mac_id'])
    if first <= active <= last:
        try:
            current = next_data(fetch(CURRENT+'fikstur',refresh=True),active)
            standings = next_data(fetch(CURRENT+'puan-durumu',refresh=True),active)
            records += recent_results(standings,active,now.isoformat())
            scheduled=fixtures(current,active,now.isoformat(),registry);sources += [CURRENT+'fikstur',CURRENT+'puan-durumu']
            for row in scheduled:
                for key,name in [(row['ev'],row['home_name']),(row['dep'],row['away_name'])]:
                    old=teams.get(key,{})
                    teams[key]=dict(name=name,aliases=sorted(set(old.get('aliases',[])+[old.get('name',name)])))
        except Exception as exc:
            errors.append(dict(source=CURRENT, error=f'{type(exc).__name__}: {exc}', retained_previous_snapshot=True))
    result=save('TR_BSL',records,scheduled,teams,sources,errors)
    if scheduled:
        for item in scheduled: registry[f"{item['sezon'][:4]}:{item['source_event_id']}"]=item['mac_id']
        temporary=registry_path.with_suffix('.part')
        temporary.write_text(json.dumps(registry,indent=2));temporary.replace(registry_path)
    target=Path('docs/kanit/competitions/TR_BSL_collection.json');report=json.loads(target.read_text())
    report.update(current_sources='beIN publisher fixtures and standings; historical TBLStat numerical facts',
        source_team_identity_map=BEIN_IDS, unknown_provider_teams=[12998],
        current_result_rule='Standings results have day precision; cannot automatically settle exact-time forecasts.',
        current_coverage='Current published fixture week; standings lastMatches can be a rolling window. Historical coverage not guaranteed complete.')
    target.write_text(json.dumps(report,indent=2))
    return result

