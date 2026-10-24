"""Pinned CC0 calendar-year Série B imports, independent of European seasons."""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
import pandas as pd
from .data import ROOT, git_source, parse_text, parse_json, write_json


def collect(first=2018, last=None, directory=None, root=ROOT, current_only=False, json_directory=None):
    now=pd.Timestamp.now(tz='UTC'); last=now.year if last is None else last
    if current_only: first=last=now.year
    if not 2018 <= first <= last <= now.year: raise ValueError('Invalid calendar years')
    directory=Path(directory) if directory else git_source('south-america')
    if not (directory/'LICENSE.md').read_text().startswith('CC0'): raise ValueError('Expected CC0 license')
    revision=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    json_directory=Path(json_directory) if json_directory else git_source('football.json', refresh=False)
    if not (json_directory/'LICENSE.md').read_text().startswith('CC0'): raise ValueError('Expected CC0 license')
    json_revision=subprocess.check_output(['git','-C',str(json_directory),'rev-parse','HEAD'],text=True).strip()
    root=Path(root); root.mkdir(parents=True,exist_ok=True); files=[]; errors=[]
    for year in range(first,last+1):
        source=directory/'brazil'/f'{year}_br2.txt'
        json_source=json_directory/str(year)/'br.2.json'
        if json_source.exists(): source=json_source
        if not source.exists():
            errors.append(dict(league='BR2',season=str(year),error='Source file unavailable; historical data is not current coverage'))
            continue
        url=(f'https://github.com/openfootball/football.json/blob/{json_revision}/{year}/br.2.json' if source==json_source else f'https://github.com/openfootball/south-america/blob/{revision}/brazil/{source.name}')
        try:
            raw=source.read_text('utf8'); rows=(parse_json(json.loads(raw),'BR2',str(year),url,now.isoformat()) if source==json_source else parse_text(raw,'BR2',str(year),url,now.isoformat()))
            ids=[r['event_id'] for r in rows]
            if len(ids)!=len(set(ids)): raise ValueError('Duplicate fixture identity')
            target=root/f'BR2_{year}.json.gz'
            if target.exists():
                old=json.loads(gzip.decompress(target.read_bytes()))['rows']; merged={r['event_id']:r for r in rows}
                for r in old:
                    fresh=merged.get(r['event_id'])
                    if r['status']=='final':
                        if fresh and fresh['status']=='final' and any(r[k]!=fresh[k] for k in ('home_goals','away_goals')):
                            raise ValueError('Conflicting final score; retained previous snapshot')
                        if not fresh or fresh['status']!='final': merged[r['event_id']]=r
                rows=list(merged.values())
            payload=dict(league='BR2',season=str(year),source_url=url,captured_at_utc=now.isoformat(),rows=rows)
            temp=target.with_suffix('.part');temp.write_bytes(gzip.compress(json.dumps(payload,ensure_ascii=False,allow_nan=False).encode(),mtime=0));temp.replace(target)
            files.append(dict(season=str(year),rows=len(rows),finals=sum(r['status']=='final' for r in rows),source_sha256=hashlib.sha256(raw.encode()).hexdigest(),source_url=url))
        except Exception as exc: errors.append(dict(league='BR2',season=str(year),error=str(exc),retained_previous=True))
    report=dict(checked_at_utc=now.isoformat(),revision=revision,license='CC0-1.0',files=files,errors=errors,note='Community results, not official verification; day precision. No inferred current season.')
    write_json(root/'calendar_collection.json',report)
    return report
