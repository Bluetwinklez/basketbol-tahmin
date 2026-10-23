"""Compare broader Japanese history with the unchanged default on identical games.

The established 2021+ policy is the control. Older results are a challenger,
never an automatic reason to replace the production training cohort.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from bbtahmin.asia_model import load, walk_forward
from bbtahmin.evaluation import metrics
from bbtahmin.prospective import fingerprint


def paired(control, challenger):
    merged=control.merge(challenger,on='mac_id',suffixes=('_control','_expanded'),validate='one_to_one')
    if len(merged)!=len(control):raise ValueError('Expanded history lost baseline evaluation games')
    for key in ('y','actual_home','actual_away','sezon','tarih_utc'):
        if not (merged[key+'_control']==merged[key+'_expanded']).all():raise ValueError('Evaluation identities/outcomes differ')
    complete=merged[merged.sezon_control<'2026-27'].copy()
    current=merged[merged.sezon_control=='2026-27'].copy()
    reports={}
    for label,g in [('completed_matched_cohort',complete),('partial_2026_27',current)]:
        if g.empty:continue
        values={}
        for suffix in ('control','expanded'):
            values[suffix]=dict(correct=int(((g['p_'+suffix]>=.5)==g['y_'+suffix]).sum()),
                **metrics(g['y_'+suffix],g['p_'+suffix]),
                score_mae=float(g['score_mae_'+suffix].mean()),
                total_mae=float(g['total_absolute_error_'+suffix].mean()),
                margin_mae=float(g['margin_absolute_error_'+suffix].mean()))
        # Resample days together, preserving shared shocks across games. Negative
        # log-loss delta favors expansion. This is exploratory, not a promotion gate.
        y=g.y_control.to_numpy();a=np.clip(g.p_control.to_numpy(),1e-12,1-1e-12)
        b=np.clip(g.p_expanded.to_numpy(),1e-12,1-1e-12)
        g['loss_delta']=-(y*np.log(b)+(1-y)*np.log(1-b))+(y*np.log(a)+(1-y)*np.log(1-a))
        g['day']=pd.to_datetime(g.tarih_utc_control,utc=True).dt.floor('D')
        blocks=g.groupby('day').loss_delta.agg(['sum','count']).to_numpy()
        rng=np.random.default_rng(20261023);draws=[]
        for _ in range(2000):
            selected=blocks[rng.integers(0,len(blocks),size=len(blocks))]
            draws.append(selected[:,0].sum()/selected[:,1].sum())
        values['log_loss_delta_expanded_minus_control']=float(g.loss_delta.mean())
        values['paired_day_bootstrap_95_interval']=np.quantile(draws,[.025,.975]).tolist()
        reports[label]=values
    return reports,merged


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='docs/kanit/history_expansion')
    parser.add_argument('--ligler',nargs='+',choices=['JP_B1','JP_B2'],default=['JP_B1','JP_B2'])
    args=parser.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    before=fingerprint();hashes={};report={}
    for code in args.ligler:
        path=Path(f'data/asia/{code}.parquet');hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        control=load(code);expanded=load(code,expanded_history=True)
        with threadpool_limits(limits=1):
            a,_,_=walk_forward(code,control)
            b,folds,skipped=walk_forward(code,expanded)
        results={}
        for variant in ('selected_policy','score'):
            result,rows=paired(a[a.variant==variant],b[b.variant==variant])
            results[variant]=result
            rows.to_csv(root/f'{code}_{variant}_matched.csv',index=False)
        report[code]=dict(default_games=len(control),expanded_games=len(expanded),added_games=len(expanded)-len(control),
                          added_seasons=sorted(set(expanded.sezon)-set(control.sezon)),comparison=results,
                          expanded_folds=folds,skipped_folds=skipped,default_changed=False)
        print(code,json.dumps(results['selected_policy']),flush=True)
    if before!=fingerprint() or any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):
        raise ValueError('Source/data changed during experiment; rerun stable inputs')
    report=dict(generated_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),source_sha256=before,datasets=hashes,leagues=report,
                method='Same fixed learners and preceding-season selection; compare 2021+ control against older-history challenger on identical fixture IDs. Earlier outcomes only. Completed matched and partial current cohorts separate. 2000 paired day-block bootstrap draws, fixed seed.',
                decision='Keep the established 2021+ default. Expanded history is exploratory; retrospective comparisons do not establish prospective improvement.')
    (root/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':main()
