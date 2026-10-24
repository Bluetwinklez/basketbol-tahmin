"""CC0 OpenFootball imports. Day precision is never invented into a tipoff."""
import gzip
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path('data/football')
LEAGUES = {'TR1': 'Turkish Süper Lig', 'EN1': 'Premier League', 'EN2': 'Championship',
           'DE1': 'Bundesliga', 'DE2': '2. Bundesliga', 'ES1': 'La Liga', 'ES2': 'Segunda División',
           'IT1': 'Serie A', 'IT2': 'Serie B', 'FR1': 'Ligue 1', 'FR2': 'Ligue 2',
           'NL1': 'Eredivisie', 'PT1': 'Primeira Liga', 'AT1': 'Austrian Bundesliga',
           'UY1': 'Uruguay Primera División', 'VE1': 'Venezuela Primera División', 'SV1': 'El Salvador Primera División', 'HN1': 'Honduras Liga Nacional', 'BO1': 'Bolivia División Profesional', 'AR2': 'Argentine Primera Nacional', 'MX2': 'Liga de Expansión MX', 'US1': 'Major League Soccer', 'JP1': 'Japan J1 League', 'CN1': 'Chinese Super League', 'BR1': 'Brazilian Série A', 'AR1': 'Argentine Primera División', 'CO1': 'Colombian Primera A', 'BR2': 'Brazilian Série B', 'BE1': 'Belgian Pro League', 'GR1': 'Greek Super League', 'SC1': 'Scottish Premiership'}
JSON_CODES = {c: c[:2].lower()+'.'+c[2:] for c in LEAGUES if c not in ('TR1', 'BR2', 'BR1', 'AR1', 'CO1', 'US1', 'JP1', 'CN1', 'AR2', 'MX2', 'UY1', 'VE1', 'SV1', 'HN1', 'BO1')}
JSON_CODES['SC1'] = 'sco.1'
# Explicit identity aliases only; no fuzzy cross-club merges.
ALIASES = {'kasimpasa sk': 'kasimpasa', 'kasimpasa': 'kasimpasa', 'konyaspor': 'atiker konyaspor',
           'alanyaspor': 'aytemiz alanyaspor', 'genclerbirligi': 'genclerbirligi', 'crb al': 'cr brasil al'}


def key(name):
    name = name.replace('ı', 'i')
    text = ''.join(c for c in unicodedata.normalize('NFKD', name.casefold()) if not unicodedata.combining(c))
    text = re.sub(r'\s+', ' ', text).strip()
    return ALIASES.get(text, text)


def write_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.part')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    tmp.replace(path)


def git_source(name, refresh=True):
    path = Path('.runtime/openfootball')/name
    url = f'https://github.com/openfootball/{name}.git'
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--depth', '1', url, str(path)], check=True, timeout=180, capture_output=True)
    elif refresh:
        subprocess.run(['git', '-C', str(path), 'pull', '--ff-only'], check=True, timeout=180, capture_output=True)
    return path


def row(code, season, day, home, away, score, source, captured):
    day = pd.Timestamp(day).strftime('%Y-%m-%d')
    pandemic_extension = code == 'BR2' and season == '2020' and '2021-01-01' <= day <= '2021-01-29'
    if not pandemic_extension and not (int(season[:4]) <= int(day[:4]) <= int(season[:4])+(len(season)>4)):
        raise ValueError('Date outside source season')
    if not all(isinstance(t, str) and t.strip() for t in (home, away)) or key(home)==key(away):
        raise ValueError('Invalid teams')
    if score is not None and (not isinstance(score, list) or len(score)!=2 or
                             any(type(n) is not int or not 0 <= n <= 30 for n in score)):
        raise ValueError('Invalid regulation score')
    event = hashlib.sha256(f'{code}|{season}|{day}|{key(home)}|{key(away)}'.encode()).hexdigest()[:24]
    # Same-day scores are unverified; a future score never becomes training data.
    status = 'final' if score is not None and day < captured[:10] else ('scheduled' if score is None and day > captured[:10] else 'unverified')
    return dict(event_id=code+'_'+event, league=code, season=season, date=day, home=key(home), away=key(away),
                home_name=home.strip(), away_name=away.strip(), home_goals=score[0] if status=='final' else None,
                away_goals=score[1] if status=='final' else None, status=status, date_precision='day',
                source_url=source, captured_at_utc=captured, source_kind='community_CC0_not_official')


def parse_json(payload, code, season, source, captured):
    if not isinstance(payload, dict) or not isinstance(payload.get('matches'), list):
        raise ValueError('Missing matches')
    if season[:4] not in payload.get('name', ''):
        raise ValueError('Source season label mismatch')
    rows=[]
    for m in payload['matches']:
        scores=m.get('score', {})
        if scores is None or scores == []: scores={}
        elif isinstance(scores,list): scores={'ft':scores}  # Short form, including 0-0 finals.
        if not isinstance(scores, dict): raise ValueError('Invalid score schema')
        rows.append(row(code,season,m['date'],m['team1'],m['team2'],scores.get('ft'),source,captured))
    return rows


def parse_turkey(text, season, source, captured):
    return parse_text(text, 'TR1', season, source, captured)


def parse_text(text, code, season, source, captured):
    """Two documented Football.TXT layouts; reject unparsed match-like lines."""
    label = r'(?:Süper Lig|Super Lig)' if code == 'TR1' else (r'Brasileiro Série A' if code == 'BR1' else r'Brasileiro Série B')
    if code=='MX2': label=r'(?:Liga de Expansión MX|Ascenso MX)'
    if code not in ('TR1', 'BR2', 'BR1', 'MX2') or not re.search(label, text.splitlines()[0]) or season[:4] not in text.splitlines()[0]:
        raise ValueError('Wrong competition/season')
    result, day, year, previous_month = [], None, int(season[:4]), 0
    months = {m: i+1 for i,m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
    for raw in text.splitlines()[1:]:
        line = raw.strip()
        date = re.fullmatch(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?', line)
        if date:
            month = months[date[1]]
            year = int(date[3]) if date[3] else int(season[:4]) + (len(season)>4 and month < 7)
            if code == 'BR2' and season == '2020' and month == 1 and not date[3]: year = 2021
            day = f'{year:04d}-{month:02d}-{int(date[2]):02d}'; previous_month=month
            continue
        if not line or line.startswith(('#', '▪', '(', ')', '=')) or not raw[:1].isspace(): continue
        line = re.sub(r'^\d{1,2}:\d{2}\s+', '', line)
        old = re.fullmatch(r'(.+?)\s+v\s+(.+?)(?:\s{2,}(\d+)-(\d+)(?:\s+\(\d+-\d+\))?)?', line)
        new = re.fullmatch(r'(.+?)\s{2,}(?:(\d+)-(\d+)(?:\s+\(\d+-\d+\))?|v)\s{2,}(.+)', line)
        if old:
            home, away = old[1].strip(), old[2].strip()
            score = [int(old[3]),int(old[4])] if old[3] else None
        elif new:
            home, away = new[1].strip(), new[4].strip()
            score = [int(new[2]),int(new[3])] if new[2] else None
        else:
            if re.search(r'\s(?:v|\d+-\d+)\s', line) and not re.search(r"\d+'", line):
                raise ValueError(f'Unparsed football fixture: {line}')
            continue
        if day is None: raise ValueError('Fixture without date')
        result.append(row(code, season, day, home, away, score, source, captured))
    if not result: raise ValueError('No football fixtures parsed')
    return result


def collect(first=2010, last=None, json_dir=None, europe_dir=None, root=ROOT, current_only=False):
    now = pd.Timestamp.now(tz='UTC'); active = now.year if now.month>=7 else now.year-1
    last = active if last is None else last
    if current_only: first=last=active
    if not 2010 <= first <= last <= active: raise ValueError('Invalid source years')
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    captured=now.isoformat(); files, errors, revisions = [], [], {}
    for repo, supplied in [('football.json', json_dir), ('europe', europe_dir)]:
        try:
            directory = Path(supplied) if supplied else git_source(repo)
            revision = subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'], text=True).strip()
            if not (directory/'LICENSE.md').read_text().startswith('CC0'): raise ValueError('Expected CC0 license')
            revisions[repo]=revision
            for year in range(first,last+1):
                season=f'{year}-{str(year+1)[-2:]}'
                candidates = [(c, directory/season/(token+'.json')) for c,token in JSON_CODES.items()] if repo=='football.json' else [('TR1', directory/'turkey'/(season+'_tr1.txt'))]
                for code,path in candidates:
                    if not path.exists():
                        if year==active: errors.append(dict(league=code,season=season,error='Source file unavailable'))
                        continue
                    relative=path.relative_to(directory).as_posix()
                    source=f'https://github.com/openfootball/{repo}/blob/{revision}/{relative}'
                    try:
                        raw=path.read_text('utf8')
                        rows = parse_json(json.loads(raw),code,season,source,captured) if repo=='football.json' else parse_turkey(raw,season,source,captured)
                        ids=[r['event_id'] for r in rows]
                        if len(ids)!=len(set(ids)): raise ValueError('Duplicate fixture identity')
                        # Per-source atomic validation: an invalid file never replaces prior data.
                        target=root/(code+'_'+season+'.json.gz')
                        if target.exists():
                            previous=json.loads(gzip.decompress(target.read_bytes()))['rows']
                            current={r['event_id']:r for r in rows}
                            for old in previous:
                                if old['status']!='final': continue
                                fresh=current.get(old['event_id'])
                                if fresh and fresh['status']=='final' and any(fresh[k]!=old[k] for k in ('home_goals','away_goals')):
                                    raise ValueError('Conflicting final score; retained previous snapshot for review')
                                if not fresh or fresh['status']!='final': current[old['event_id']]=old
                            rows=list(current.values())
                        payload=dict(league=code,season=season,source_url=source,captured_at_utc=captured,rows=rows)
                        temp=target.with_suffix('.part')
                        temp.write_bytes(gzip.compress(json.dumps(payload,ensure_ascii=False,allow_nan=False).encode(),mtime=0))
                        temp.replace(target)
                        files.append(dict(league=code,season=season,rows=len(rows),finals=sum(r['status']=='final' for r in rows),sha256=hashlib.sha256(raw.encode()).hexdigest()))
                    except Exception as exc: errors.append(dict(league=code,season=season,error=str(exc),retained_previous=True))
        except Exception as exc: errors.append(dict(repository=repo,error=str(exc),retained_previous=True))
    frame=load(root)
    report=dict(checked_at_utc=captured,revisions=revisions,files=files,errors=errors,
                finals=int((frame.status=='final').sum()) if len(frame) else 0,
                fixtures=int((frame.status=='scheduled').sum()) if len(frame) else 0,
                leagues={c:int(((frame.league==c)&(frame.status=='final')).sum()) for c in LEAGUES} if len(frame) else {},
                note='CC0 community archive, not official results. Partial/stale seasons are possible. Day precision; no same-day finals.')
    write_json(root/'collection.json',report)
    if not files: raise RuntimeError('All football source imports failed; prior snapshots retained')
    return report


def load(root=ROOT):
    rows=[]
    for path in sorted(Path(root).glob('*_20*.json.gz')):
        rows.extend(json.loads(gzip.decompress(path.read_bytes()).decode('utf8'))['rows'])
    frame=pd.DataFrame(rows)
    if len(frame):
        if frame.event_id.duplicated().any(): raise ValueError('Duplicate archive fixtures')
        if frame.duplicated(['league','date','home','away']).any():
            raise ValueError('Duplicate natural fixture identity')
        if not set(frame.league) <= set(LEAGUES) or (frame.home == frame.away).any():
            raise ValueError('Invalid archive league or teams')
        finals=frame.loc[frame.status == 'final']
        values=finals[['home_goals','away_goals']].apply(pd.to_numeric,errors='coerce')
        if values.isna().any().any() or ((values < 0) | (values > 30) | (values % 1 != 0)).any().any():
            raise ValueError('Invalid archive regulation scores')
    return frame

