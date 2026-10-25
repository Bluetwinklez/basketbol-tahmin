"""Licensed sources for screenshot competitions, with explicit source boundaries."""
import gzip,json,subprocess,hashlib
from pathlib import Path
import pandas as pd
from .data import ROOT,load,row,parse_text,write_json,key


def save(rows,code,season,root):
    from .storage import save as save_snapshot
    return len(save_snapshot(rows, code, season, root))


def argentina(directory,root=ROOT,first=2023):
    directory=Path(directory);license_text=(directory/'LICENSE-DATOS.md').read_text()
    if 'CC BY-SA 4.0' not in license_text:raise ValueError('Expected share-alike data license')
    revision=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    captured=pd.Timestamp.now(tz='UTC').isoformat();report=[]
    for year in range(first,pd.Timestamp.now(tz='UTC').year+1):
        path=directory/'data'/f'partidos-{year}.csv'
        if not path.exists():continue
        f=pd.read_csv(path).fillna('');groups={}
        for m in f.to_dict('records'):
            # Only direct Wikipedia attribution; exclude mixed/noncommercial sources,
            # elimination rounds, penalties, neutral venues and undated records.
            if not m['source'].startswith('https://es.wikipedia.org/wiki/') or ' + ' in m['source']:continue
            code='AR2' if m['tournament']=='Primera Nacional' else ('AR1' if str(m['tournament']).startswith('Primera Division') and year==2026 else None)
            if not code or m['phase']!='zonas' or m['neutral'] is True or m['date']=='':continue
            if m['home_pens']!='' or m['away_pens']!='':continue
            if m['home_score']=='' or m['away_score']=='':continue
            scores=[float(m['home_score']),float(m['away_score'])]
            if any(not n.is_integer() for n in scores):raise ValueError('Non-integer source score')
            r=row(code,str(year),m['date'],m['home_team'],m['away_team'],list(map(int,scores)),m['source'],captured)
            r.update(source_kind='publisher_CC_BY_SA_not_official',license='CC-BY-SA-4.0',attribution='Wikipedia contributors; rhinoah/futbol-argentino-data',publisher_url=f'https://github.com/rhinoah/futbol-argentino-data/blob/{revision}/data/{path.name}')
            groups.setdefault(code,[]).append(r)
        for code,rows in groups.items():report.append(dict(league=code,season=str(year),rows=save(rows,code,str(year),root),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    result=dict(revision=revision,files=report,license='CC-BY-SA-4.0',checked_at_utc=captured,note='Wikipedia-only regular stages; transformed data retains CC BY-SA 4.0. Not official verification.')
    write_json(Path(root)/'screenshot_argentina_collection.json',result);return result


def mexico(directory,root=ROOT):
    directory=Path(directory)
    if not (directory/'LICENSE.md').read_text().startswith('CC0'):raise ValueError('Expected CC0')
    rev=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip();files=[];errors=[]
    for p in sorted((directory/'north-america/mexico').glob('*_mx2*.txt')):
        season=p.name[:7];url=f'https://github.com/openfootball/world/blob/{rev}/{p.relative_to(directory).as_posix()}'
        try:
            rows=parse_text(p.read_text(),'MX2',season,url,pd.Timestamp.now(tz='UTC').isoformat());files.append(dict(season=season,rows=save(rows,'MX2',season,root),source_url=url))
        except Exception as e:errors.append(dict(season=season,error=str(e)))
    r=dict(revision=rev,files=files,errors=errors,note='CC0 community records; missing 2025/26 and 2026/27 are not inferred.');write_json(Path(root)/'screenshot_mexico_collection.json',r);return r
