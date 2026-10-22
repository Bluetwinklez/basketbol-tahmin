"""Fresh official results overlay; frozen historical benchmark archives stay intact."""
import hashlib,json
from pathlib import Path
import pandas as pd

PATH=Path('data/recent/E.parquet')


def merge(base,extra):
    all_games=pd.concat([base,extra],ignore_index=True)
    for _,part in all_games[all_games.mac_id.duplicated(False)].groupby('mac_id'):
        if len(part[['lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor']].drop_duplicates())!=1:
            raise ValueError('Fresh official result conflicts with frozen archive; explicit review required')
    return all_games.drop_duplicates('mac_id').sort_values(['tarih_utc','mac_id']).reset_index(drop=True)


def load(path='data/maclar.parquet'):
    g=pd.read_parquet(path)
    if str(path)=='data/maclar.parquet' and PATH.exists():g=merge(g,pd.read_parquet(PATH))
    return g


def refresh_europe(payload,captured_at):
    from .veri.euroleague import collect
    class Response:
        def get(self,url,**kwargs):return json.dumps(payload).encode()
    rows,_=collect(Response(),'E',2026)
    g=pd.DataFrame(rows);g['tarih_utc']=pd.to_datetime(g.tarih_utc,utc=True)
    captured=pd.Timestamp(captured_at)
    if g.empty or (g.tarih_utc>=captured).any() or (g.ev_skor<=0).any() or (g.dep_skor<=0).any():raise ValueError('Invalid official finished result overlay')
    g['captured_at_utc']=captured;g['date_precision']='timestamp'
    base=pd.read_parquet('data/maclar.parquet');merge(base,g)
    if PATH.exists():g=merge(pd.read_parquet(PATH),g)
    PATH.parent.mkdir(parents=True,exist_ok=True);temp=PATH.with_suffix('.part');g.to_parquet(temp,index=False);temp.replace(PATH)
    report=dict(source='https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games',
        captured_at_utc=captured.isoformat(),games=len(g),new_relative_to_frozen_archive=int((~g.mac_id.isin(base.mac_id)).sum()),
        sha256=hashlib.sha256(PATH.read_bytes()).hexdigest(),benchmark_archive_unchanged=True,
        note='Runtime feature updates use fresh results. Historical benchmark is not rerun or claimed for the modified runtime dataset.')
    PATH.with_suffix('.json').write_text(json.dumps(report,indent=2));return report
