"""Manual historical backfill; intentionally excluded from daily downloads."""
import subprocess
import pandas as pd
from bbtahmin.football.data import git_source, ROOT
from bbtahmin.football.turkey_second import import_2019

if __name__ == '__main__':
    directory=git_source('europe',refresh=False)
    if not (directory/'LICENSE.md').read_text().startswith('CC0'):
        raise ValueError('Expected CC0 license')
    revision=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    relative='turkey/2019-20_tr2.txt'
    rows=import_2019((directory/relative).read_text(),
        f'https://github.com/openfootball/europe/blob/{revision}/{relative}',
        pd.Timestamp.now(tz='UTC').isoformat(),ROOT)
    print(f'Available TR2 regular-season finals: {len(rows)}')
