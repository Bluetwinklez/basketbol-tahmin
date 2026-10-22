"""Additional official senior women's history, separate from frozen baseline archives."""
import json,hashlib
from pathlib import Path
import pandas as pd
from .competitions import fetch,fiba_games,normalize_fiba,collect_fiba

EARLY_URL='https://www.fiba.basketball/en/history/165-fiba-womens-european-club-competitions-tier-2/208498/games'
EARLY=Path('data/competitions/ECW_early.parquet')


def collect():
    rows=fiba_games(fetch(EARLY_URL),'ECW',2023)
    games,_,_=normalize_fiba(rows,'ECW',2023)
    g=pd.DataFrame(games).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if g.empty or g.mac_id.duplicated().any():raise ValueError('Invalid early ECW archive')
    if EARLY.exists():
        old=pd.read_parquet(EARLY);both=pd.concat([old,g],ignore_index=True)
        for _,p in both.groupby('mac_id'):
            if len(p[['tarih_utc','ev','dep','ev_skor','dep_skor']].drop_duplicates())!=1:raise ValueError('Historical score conflict')
        g=both.drop_duplicates('mac_id').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    EARLY.parent.mkdir(parents=True,exist_ok=True);temporary=EARLY.with_suffix('.part');g.to_parquet(temporary,index=False);temporary.replace(EARLY)
    root=Path('docs/kanit/winner');root.mkdir(parents=True,exist_ok=True)
    (root/'early_collection.json').write_text(json.dumps(dict(games=len(g),seasons=g.groupby('sezon').size().to_dict(),
      source=EARLY_URL,gender='Women',sha256=hashlib.sha256(EARLY.read_bytes()).hexdigest(),
      note='Public source numeric facts. Positive finished non-tied games only; not a completeness guarantee. Captured retrospectively.'),indent=2))
    print('Added early ECW games:',len(g),flush=True)


if __name__=='__main__':collect()
