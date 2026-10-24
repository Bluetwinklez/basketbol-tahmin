"""Same-cohort candidate evaluation with explicit probability reliability."""
import gzip
import json
from pathlib import Path
import numpy as np
from bbtahmin.football.data import load,write_json
from bbtahmin.football.challenger import compare,VARIANTS
from bbtahmin.football.model import metrics


def reliability(probabilities, outcomes):
    p=np.asarray(probabilities,float);y=np.asarray(outcomes,float)
    bins=[]
    for i in range(10):
        mask=(p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))
        if mask.any():bins.append(dict(lower=i/10,upper=(i+1)/10,n=int(mask.sum()),mean_probability=float(p[mask].mean()),observed_rate=float(y[mask].mean())))
    return dict(n=len(p),brier=float(np.mean((p-y)**2)),log_loss=float(-np.mean(y*np.log(np.clip(p,1e-15,1))+(1-y)*np.log(np.clip(1-p,1e-15,1)))),
                expected_calibration_error=sum(b['n']*abs(b['mean_probability']-b['observed_rate']) for b in bins)/len(p),bins=bins)


def main():
    r=compare(load(),'2025-26');rows=r.pop('predictions');summary={}
    for variant in VARIANTS:
        items=[x for x in rows if x['variant']==variant]
        markets={}
        for name in ('home','draw','away'):
            markets[name]=reliability([x['prediction']['probabilities'][name] for x in items],[x['result']['actual_outcome']==name for x in items])
        for line in ('1.5','2.5','3.5'):
            markets['over_'+line]=reliability([x['prediction']['over'][line] for x in items],[x['result']['actual_home']+x['result']['actual_away']>float(line) for x in items])
        markets['both_teams_score']=reliability([x['prediction']['both_teams_score'] for x in items],[min(x['result']['actual_home'],x['result']['actual_away'])>0 for x in items])
        summary[variant]=dict(metrics=metrics([x['result'] for x in items]),reliability=markets)
    r['pooled']=summary
    r['note']+=' Equal ensemble weights fixed at 0.5; calibration bins are measurement only, not fitted corrections. Partial archive coverage; no prospective claim.'
    target=Path('docs/kanit/football_ensemble');target.mkdir(parents=True,exist_ok=True)
    write_json(target/'comparison.json',r)
    compact=[dict(event_id=x['event_id'],league=x['league'],date=x['date'],variant=x['variant'],probabilities=x['prediction']['probabilities'],over=x['prediction']['over'],both_teams_score=x['prediction']['both_teams_score'],actual_home=x['result']['actual_home'],actual_away=x['result']['actual_away']) for x in rows]
    (target/'paired_results.json.gz').write_bytes(gzip.compress(json.dumps(compact,separators=(',',':')).encode(),mtime=0))
    print(json.dumps({v:summary[v]['metrics'] for v in VARIANTS},indent=2))


if __name__=='__main__':main()
