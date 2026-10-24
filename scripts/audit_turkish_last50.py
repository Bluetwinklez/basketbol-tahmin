"""Export reproducible team-level history coverage with source provenance."""
import pandas as pd
import gzip,json
from pathlib import Path
from bbtahmin.football.data import load,write_json
from bbtahmin.football.coverage import last_matches

def main():
    f=load(); g=f[f.league=='TR1'];cutoff=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d')
    teams=sorted(set(g.home)|set(g.away))
    rows=[last_matches(f,'TR1',t,cutoff) for t in teams]
    target=Path('docs/kanit/turkish_last50/coverage.json.gz');target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(gzip.compress(json.dumps(dict(cutoff=cutoff,teams=rows,complete_all_competitions=False),ensure_ascii=False).encode(),mtime=0))
    print([(r['team'],r['available'],r['last_date']) for r in rows])
if __name__=='__main__':main()
