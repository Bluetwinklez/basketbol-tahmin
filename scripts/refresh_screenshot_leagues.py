"""Refresh only the explicitly requested additional source repositories."""
from pathlib import Path
import subprocess
from bbtahmin.football.data import git_source
from bbtahmin.football.screenshots import argentina,mexico


def run(backfill=False):
    errors=[]; files=[]
    p=Path('.runtime/futbol-argentino-data')
    try:
        if not p.exists(): subprocess.run(['git','clone','--depth','1','https://github.com/rhinoah/futbol-argentino-data.git',str(p)],check=True,timeout=180,capture_output=True)
        else: subprocess.run(['git','-C',str(p),'pull','--ff-only'],check=True,timeout=180,capture_output=True)
        import pandas as pd
        report=argentina(p,first=2023 if backfill else pd.Timestamp.now(tz='UTC').year)
        files.extend(report['files']); errors.extend(report.get('errors',[]))
    except Exception as exc:
        errors.append(dict(source='argentina',error=str(exc),retained_previous=True))
    # Static historical Mexico is independent of the current Argentina source.
    if backfill:
        try:
            report=mexico(git_source('world'))
            files.extend(report['files']); errors.extend(report['errors'])
        except Exception as exc:
            errors.append(dict(source='mexico',error=str(exc),retained_previous=True))
    return dict(files=files,errors=errors)
