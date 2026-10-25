"""Finite, predeclared football ablations and prior-only temperature calibration.

Already inspected historical seasons are exploratory evidence. No production
policy is selected on the reported target outcomes and no default is promoted.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import softmax

from bbtahmin.experiment_metrics import metrics, paired
from bbtahmin.football.challenger import fit
from bbtahmin.football.data import load, write_json
from bbtahmin.football.model import GoalModel, score
from bbtahmin.prospective import fingerprint

VARIANTS=('baseline','recency90','shrinkage16','opponent','opponent_dc','ensemble')
TEMPERATURES=(.75,1.,1.25,1.5,2.)


def temperature(p,value):
    return softmax(np.log(np.clip(np.asarray(p),1e-15,1))/value,axis=-1)


def model(frame,league,cutoff,variant):
    if variant=='recency90': return GoalModel(frame,league,cutoff,half_life=90.)
    if variant=='shrinkage16': return GoalModel(frame,league,cutoff,shrinkage=16.)
    return fit(frame,league,cutoff,variant)


def season_predictions(frame,league,season):
    target=frame.loc[(frame.league==league)&(frame.season==season)&(frame.status=='final')]
    rows=[];skipped=[]
    for month,games in target.sort_values(['date','event_id']).groupby(target.date.str[:7]):
        cutoff=month+'-01'
        try: models={v:model(frame,league,cutoff,v) for v in VARIANTS}
        except ValueError as exc:
            skipped.append(dict(month=month,games=len(games),reason=str(exc)));continue
        for game in games.to_dict('records'):
            for variant,estimator in models.items():
                prediction=estimator.predict(game['home'],game['away'])
                result=score(prediction,int(game['home_goals']),int(game['away_goals']))
                probs=[prediction['probabilities'][k] for k in ('home','draw','away')]
                rows.append(dict(event_id=game['event_id'],day=game['date'],league=league,season=season,
                                 variant=variant,p=probs,y=('home','draw','away').index(result['actual_outcome']),
                                 data_gate_passed=not prediction['issues'],result=result))
    return rows,skipped


def summarize(rows):
    return metrics([r['y'] for r in rows],[r['p'] for r in rows],
                   [bool(r['data_gate_passed'] and max(r['p'])>=.65) for r in rows])


def compare(frame,league,target_season,development_season,bootstrap=1000):
    if development_season>=target_season: raise ValueError('Development must precede target')
    dev,dev_skipped=season_predictions(frame,league,development_season)
    target,skipped=season_predictions(frame,league,target_season)
    if not dev or not target: raise ValueError('Nonempty development and target periods required')
    days=sorted({r['day'] for r in dev});boundary=days[len(days)//2]
    calibration=[r for r in dev if r['day']<boundary]
    selection=[r for r in dev if r['day']>=boundary]
    if min(len({r['event_id'] for r in calibration}),len({r['event_id'] for r in selection}))<30:
        raise ValueError('At least 30 disjoint calibration and selection games required')
    settings={};validation={};transformed=[]
    for variant in VARIANTS:
        cal=[r for r in calibration if r['variant']==variant]
        # Temperature learned exclusively on the FIRST development day half.
        value=min(TEMPERATURES,key=lambda t:(metrics([r['y'] for r in cal],temperature([r['p'] for r in cal],t))['all']['log_loss'],abs(t-1)))
        settings[variant]=value
        sel=[dict(r,p=temperature(r['p'],value).tolist()) for r in selection if r['variant']==variant]
        validation[variant]=summarize(sel)['all']
        transformed.extend(dict(r,variant=variant+'_calibrated',p=temperature(r['p'],value).tolist())
                           for r in target if r['variant']==variant)
    # Candidate policy fixed using only the SECOND development day half.
    baseline=validation['baseline']
    eligible=[v for v in VARIANTS if v!='baseline' and
              validation[v]['accuracy']>=baseline['accuracy']+.01 and
              validation[v]['log_loss']<=baseline['log_loss']-.005 and
              validation[v]['brier']<=baseline['brier']]
    chosen=min(eligible,key=lambda v:(validation[v]['log_loss'],v)) if eligible else 'baseline'
    all_rows=target+transformed
    policy=[dict(r,variant='prior_selected_policy') for r in transformed if r['variant']==chosen+'_calibrated']
    all_rows+=policy
    names=[*VARIANTS,*[v+'_calibrated' for v in VARIANTS],'prior_selected_policy']
    summaries={v:summarize([r for r in all_rows if r['variant']==v]) for v in names}
    comparisons={v:paired(all_rows,'baseline',v,replicates=bootstrap) for v in names if v!='baseline'}
    errors={v:{key:float(np.mean([r['result'][key] for r in all_rows if r['variant']==v]))
               for key in ('home_absolute_error','away_absolute_error','total_absolute_error','margin_absolute_error','total_in_80')}
            for v in names}
    return dict(league=league,development_season=development_season,target_season=target_season,
                calibration_before_day=boundary,temperatures=settings,selection_metrics=validation,
                selected_using_prior_period=chosen,summaries=summaries,score_errors=errors,comparisons=comparisons,
                skipped=dict(development=dev_skipped,target=skipped),rows=all_rows,
                evidence_kind='exploratory_retrospective',production_default_changed=False,
                limitations='Historical publication times and full season coverage unverified. Target outcomes do not select policy. 1X2 calibration does not recalibrate goal markets or score intervals. Multiple experiments are not confirmatory evidence.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--leagues',nargs='+',default=['EN1','EN2','DE1','ES1','IT1','FR1','NL1','PT1','TR1'])
    parser.add_argument('--development',default='2024-25')
    parser.add_argument('--target',default='2025-26')
    parser.add_argument('--output',default='docs/kanit/improvement/football')
    args=parser.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    frame=load();code_hash=fingerprint()
    inputs={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('data/football').glob('*.json.gz'))}
    protocol=dict(spec='football-improvement-experiment-v1',variants=VARIANTS,temperature_grid=TEMPERATURES,
                  development=args.development,target=args.target,leagues=args.leagues,
                  calibration='First UTC-day half of development OOS predictions; selection on second half.',
                  retraining='Monthly expanding history; entire target month withheld.',
                  selection_threshold=.65,source_code_sha256=code_hash,input_hashes=inputs,
                  predeclared_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),default_promotion=False)
    protocol_path=root/'protocol.json'
    if protocol_path.exists():
        previous=json.loads(protocol_path.read_text())
        if any(previous.get(k)!=json.loads(json.dumps(v)) for k,v in protocol.items() if k!='predeclared_at_utc'):
            raise ValueError('Experiment inputs or policy changed; use a new output directory/version')
    else: write_json(protocol_path,protocol)
    reports=[]
    for league in args.leagues:
        report=compare(frame,league,args.target,args.development)
        if fingerprint()!=code_hash: raise ValueError('Code changed during experiment')
        reports.append({k:v for k,v in report.items() if k!='rows'})
        raw=json.dumps(report,ensure_ascii=False,allow_nan=False).encode()
        (root/(league+'.json.gz')).write_bytes(gzip.compress(raw,mtime=0))
        print(league,report['summaries']['baseline']['all'],report['summaries']['prior_selected_policy']['all'],flush=True)
    write_json(root/'summary.json',dict(protocol=protocol,reports=reports))


if __name__=='__main__': main()
