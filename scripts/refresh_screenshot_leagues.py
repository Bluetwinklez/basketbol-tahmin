"""Refresh only the explicitly requested additional source repositories."""
from pathlib import Path
import subprocess
from bbtahmin.football.data import git_source
from bbtahmin.football.screenshots import argentina,mexico


def run(backfill=False):
    p=Path('.runtime/futbol-argentino-data')
    if not p.exists(): subprocess.run(['git','clone','--depth','1','https://github.com/rhinoah/futbol-argentino-data.git',str(p)],check=True,timeout=180,capture_output=True)
    else: subprocess.run(['git','-C',str(p),'pull','--ff-only'],check=True,timeout=180,capture_output=True)
    import pandas as pd
    argentina(p,first=2023 if backfill else pd.Timestamp.now(tz='UTC').year)
    # The archived Mexico seasons are fetched on backfill only.
    if backfill:mexico(git_source('world'))
