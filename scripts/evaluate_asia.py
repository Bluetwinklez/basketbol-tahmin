"""Fit fixed Asian-league learners and score expanding, preceding-season folds."""
import argparse,hashlib,json,importlib.metadata
from pathlib import Path
import numpy as np
import pandas as pd
from bbtahmin import asia_model as model
from bbtahmin.evaluation import metrics
from bbtahmin.prospective import fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ligler',nargs='+',choices=model.CODES)
    args=parser.parse_args();codes=args.ligler or [c for c in model.CODES if Path(f'data/asia/{c}.parquet').exists()]
    if not codes:raise ValueError('No collected Asian league datasets')
    root=Path('docs/kanit/asia_models');root.mkdir(parents=True,exist_ok=True)
    paths={c:Path(f'data/asia/{c}.parquet') for c in codes}
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths.values()};source=fingerprint()
    now=pd.Timestamp.now(tz='UTC');current=now.year if now.month>=7 else now.year-1
    summaries=[];folds={};skipped={};outputs={}
    for code in codes:
        records,folds[code],skipped[code]=model.walk_forward(code);outputs[code]=records
        collection=Path(f'docs/kanit/asia_data/{code}_collection.json')
        campaign=json.loads(collection.read_text()).get('current_model_season') if collection.exists() else None
        if records.empty:continue
        for (season,variant),p in records.groupby(['sezon','variant']):
            result=metrics(p.y,p.p);rate=result['accuracy'];n=result['n'];z=1.959963984540054
            center=(rate+z*z/(2*n))/(1+z*z/n);half=z*np.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
            subset=p[p.eligible]
            summaries.append(dict(league=code,season=season,completed=(season!=campaign and int(season[:4])<current),variant=variant,
                correct=int(((p.p>=.5)==p.y).sum()),**result,accuracy_wilson_95_low=center-half,accuracy_wilson_95_high=center+half,
                designated_home_baseline_accuracy=float(p.y.mean()),score_mae=float(p.score_mae.mean()),
                total_mae=float(p.total_absolute_error.mean()),margin_mae=float(p.margin_absolute_error.mean()),
                total_80_coverage=float(p.total_in_80.mean()),selected_games=len(subset),coverage=len(subset)/len(p),
                selected_accuracy=float(((subset.p>=.5)==subset.y).mean()) if len(subset) else None))
        print('Evaluated',code,len(records),'variant rows',flush=True)
    if source!=fingerprint() or any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):
        raise ValueError('Evaluation data/code changed during run; rerun stable snapshot')
    for code,records in outputs.items():records.to_csv(root/f'{code}_predictions.csv',index=False)
    pd.DataFrame(summaries).to_csv(root/'summary.csv',index=False)
    (root/'folds.json').write_text(json.dumps(dict(folds=folds,skipped=skipped),indent=2))
    (root/'manifest.json').write_text(json.dumps(dict(spec=model.SPEC,generated_at_utc=now.isoformat(),files=hashes,
        source_code_sha256=source,packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn']},
        default_history_start=model.DEFAULT_HISTORY_START,
        method='Independent divisions/conferences. Fixed Ridge alpha=10 and logistic C=1; Elo and equal ensemble. Earlier seasons train, preceding season first UTC-day half calibrates score scale, second half selects by log loss, refit on all preceding seasons. No target-season tuning; same-day features withheld.',
        limitations='Retrospectively collected numeric results; publication-time history and independently complete coverage unavailable. PBA nominal sides are not verified home court. League reorganisation, imports and rule changes are not fully modeled. Historical accuracy is not a prospective or guaranteed rate. Intervals are not conditional coverage guarantees. Small/partial seasons and selected coverage are separate.'),indent=2))
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__=='__main__':main()
