"""Pinned CC0 calendar-year Série B imports, independent of European seasons."""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
import pandas as pd
from .data import ROOT, git_source, parse_text, parse_json, write_json


def collect(first=2018, last=None, directory=None, root=ROOT, current_only=False, json_directory=None, code="BR2"):
    if code not in ("BR2", "BR1", "AR1", "CO1", "US1", "JP1", "CN1"): raise ValueError("Unsupported calendar league")
    now=pd.Timestamp.now(tz='UTC'); last=now.year if last is None else last
    if current_only: first=last=now.year
    if not 2018 <= first <= last <= now.year: raise ValueError('Invalid calendar years')
    directory=Path(directory) if directory else git_source('south-america', refresh=True)
    if not (directory/'LICENSE.md').read_text().startswith('CC0'): raise ValueError('Expected CC0 license')
    revision=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    json_directory=Path(json_directory) if json_directory else git_source('football.json', refresh=True)
    if not (json_directory/'LICENSE.md').read_text().startswith('CC0'): raise ValueError('Expected CC0 license')
    json_revision=subprocess.check_output(['git','-C',str(json_directory),'rev-parse','HEAD'],text=True).strip()
    root=Path(root); root.mkdir(parents=True,exist_ok=True); files=[]; errors=[]
    for year in range(first,last+1):
        source=directory/'brazil'/f'{year}_{code.lower()}.txt'
        json_source=json_directory/str(year)/('mls.json' if code=='US1' else code[:2].lower()+'.'+code[2:]+'.json')
        if json_source.exists(): source=json_source
        if not source.exists():
            errors.append(dict(league=code,season=str(year),error='Source file unavailable; historical data is not current coverage'))
            continue
        url=(f'https://github.com/openfootball/football.json/blob/{json_revision}/{year}/{json_source.name}' if source==json_source else f'https://github.com/openfootball/south-america/blob/{revision}/brazil/{source.name}')
        try:
            raw=source.read_text('utf8'); rows=(parse_json(json.loads(raw),code,str(year),url,now.isoformat()) if source==json_source else parse_text(raw,code,str(year),url,now.isoformat()))
            from .storage import save as save_snapshot
            rows = save_snapshot(rows, code, str(year), root, dict(
                league=code, season=str(year), source_url=url, captured_at_utc=now.isoformat()))
            files.append(dict(season=str(year),rows=len(rows),finals=sum(r['status']=='final' for r in rows),source_sha256=hashlib.sha256(raw.encode()).hexdigest(),source_url=url))
        except Exception as exc: errors.append(dict(league=code,season=str(year),error=str(exc),retained_previous=True))
    report=dict(checked_at_utc=now.isoformat(),revision=revision,license='CC0-1.0',files=files,errors=errors,note='Community results, not official verification; day precision. No inferred current season.')
    write_json(root/('calendar_collection.json' if code=='BR2' else f'{code}_collection.json'),report)
    return report
