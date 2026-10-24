"""Attribution-licensed historical requested leagues; never current-season evidence."""
from pathlib import Path
import subprocess,hashlib
import pandas as pd
from .data import ROOT,row,write_json,key
from .screenshots import save

CODES={'uruguay':'UY1','venezuela':'VE1','el-salvador':'SV1','honduras':'HN1','bolivia':'BO1'}

def normalize(frame,source,captured):
    rows=[]
    for m in frame.to_dict('records'):
        if m['competition'] not in CODES or m['full_time']!='F' or m['level']!='national':continue
        if pd.isna(m['date']):continue
        day=pd.Timestamp(m['date']).strftime('%Y-%m-%d')
        if not '2018-01-01'<=day<='2023-12-31':continue
        if any(not isinstance(m[t],str) or not m[t].strip() for t in ('home','away')):continue
        if key(m['home'])==key(m['away']):continue
        values=[m['gh'],m['ga']]
        if any(pd.isna(x) or not float(x).is_integer() for x in values):continue
        r=row(CODES[m['competition']],day[:4],day,m['home'],m['away'],list(map(int,values)),source,captured)
        r.update(source_kind='publisher_ODC_BY_not_official',license='ODC-By-1.0',attribution='David Schoch / schochastics/football-data',source_home_ident=m['home_ident'],source_away_ident=m['away_ident'])
        rows.append(r)
    return rows

def collect(directory,root=ROOT):
    directory=Path(directory)
    if 'Open Data Commons Attribution License' not in (directory/'README.md').read_text():raise ValueError('Source attribution license missing')
    rev=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    p=directory/'data/results/games.parquet';source=f'https://github.com/schochastics/football-data/blob/{rev}/data/results/games.parquet'
    captured=pd.Timestamp.now(tz='UTC').isoformat();rows=normalize(pd.read_parquet(p),source,captured)
    groups={}
    for r in rows:groups.setdefault((r['league'],r['season']),[]).append(r)
    files=[];errors=[]
    for (code,season),items in groups.items():
        # Reject ambiguous duplicate records atomically; never count the same match twice.
        try:files.append(dict(league=code,season=season,rows=save(items,code,season,root)))
        except ValueError as e:errors.append(dict(league=code,season=season,error=str(e)))
    result=dict(revision=rev,source_url=source,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),files=files,errors=errors,license='ODC-By-1.0',attribution='David Schoch / schochastics/football-data',license_url='https://opendatacommons.org/licenses/by/1-0/',checked_at_utc=captured,note='2018–2023 only; historical publisher data, not official verification or current coverage. Full-time F only; E/P excluded.')
    write_json(Path(root)/'regional_collection.json',result);return result
