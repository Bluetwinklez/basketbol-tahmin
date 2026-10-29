"""Derive signed reports from existing verified predictions, without refitting.

Run after backtest and before committing evidence. Raw odds remain local.
"""
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from bbtahmin.artifacts import verified_manifest
from bbtahmin.backtest import harman_katsayilari, market_and_betting
from confidence_report import confidence_table


def refresh(root=Path('docs/kanit/pregame_verified'), odds_path=Path('data/oranlar.parquet')):
    root=Path(root);odds_path=Path(odds_path)
    meta=verified_manifest(root)
    if meta is None: raise ValueError('Invalid source benchmark')
    source=root/'tahminler.csv'
    if source.exists():
        raw=source.read_bytes()
    else:
        source=root/'tahminler.csv.gz'
        raw=gzip.decompress(source.read_bytes())
    # Existing manifests sign the uncompressed prediction stream separately.
    variants=(raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
    if meta['prediction_sha256'] not in {hashlib.sha256(v).hexdigest() for v in variants}:
        raise ValueError('Prediction fingerprint mismatch')
    odds=pd.read_parquet(odds_path)
    predictions=pd.read_csv(source)
    # Keep the committed stream in sync after a full backtest as well.
    (root/'tahminler.csv.gz').write_bytes(gzip.compress(raw,mtime=0))
    market,bets=market_and_betting(predictions,odds)
    market.to_csv(root/'piyasa.csv',index=False)
    bets.to_csv(root/'bahis.csv',index=False)
    (root/'harman.json').write_text(json.dumps(dict(NBA=harman_katsayilari(predictions,odds)),indent=2),'utf8')
    # Compare every variant on precisely the seasons available for all blends.
    models=['skor','topluluk','piyasa_vigsiz','harman_skor','harman_topluluk']
    common=set.intersection(*(set(market.loc[market.model==m,'sezon']) for m in models))
    rows=[]
    for model in models:
        part=market[(market.model==model)&market.sezon.isin(common)]
        if not part.empty:
            rows.append(dict(model=model,n=int(part.n.sum()),seasons=','.join(sorted(common)),
                **{key:float((part[key]*part.n).sum()/part.n.sum()) for key in ('accuracy','log_loss','brier')}))
    pd.DataFrame(rows).to_csv(root/'piyasa_ozet.csv',index=False)
    year=int(max(predictions.sezon).split('-')[0])
    completed=predictions[predictions.sezon.str[:4].astype(int)<year]
    confidence_table(completed).to_csv(root/'confidence.csv',index=False)
    meta['derived_reports']=dict(timestamp=datetime.now(timezone.utc).isoformat(),
        method='Existing signed predictions; no model refit. Market summary uses common blend seasons.',
        odds_dataset_sha256=hashlib.sha256(odds_path.read_bytes()).hexdigest(),
        command='python scripts/refresh_verified_evidence.py')
    # Include the compressed, distributable predictions as well as all reports.
    # The raw CSV is gitignored; signing it would invalidate a clean checkout.
    meta['files'].pop('tahminler.csv',None)
    for path in sorted(root.iterdir()):
        if path.suffix in ('.csv','.json','.gz') and path.name not in ('manifest.json','tahminler.csv'):
            meta['files'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (root/'manifest.json').write_text(json.dumps(meta,indent=2),'utf8')
    if verified_manifest(root) is None: raise ValueError('Derived evidence verification failed')
    return pd.DataFrame(rows)


if __name__=='__main__':
    print(refresh().to_string(index=False))
