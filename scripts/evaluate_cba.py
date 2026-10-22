"""Reproduce separate CBA pregame and quarter-boundary live evaluations."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import accuracy_score,brier_score_loss,log_loss

from bbtahmin import cba_model,live


def main():
    root=Path('docs/kanit/cba');root.mkdir(parents=True,exist_ok=True)
    g=cba_model.load();prior=cba_model.walk_forward(g)
    prior.to_csv(root/'pregame_predictions.csv',index=False)
    now=pd.Timestamp.now(tz='UTC');current=now.year if now.month>=7 else now.year-1
    pre=[]
    for season,part in prior.groupby('sezon'):
        pre.append(dict(season=season,completed=int(season[:4])<current,n=len(part),
            correct=int(((part.p>=.5)==part.y).sum()),accuracy=float(accuracy_score(part.y,part.p>=.5)),
            home_baseline_accuracy=float(part.y.mean()),log_loss=float(log_loss(part.y,part.p,labels=[0,1])),
            margin_mae=float(np.mean(abs(part.margin-part.margin_prediction))),
            total_mae=float(np.mean(abs(part.total-part.total_prediction)))))
    (root/'pregame_summary.json').write_text(json.dumps(pre,indent=2))
    states=live.training_states(g);cols=[f'x{i}' for i in range(5)]
    results=[];records=[]
    indexed=prior.set_index('mac_id')
    for season in sorted(states.sezon.unique()):
        try:models,sigma,info=live.fit(states,season)
        except ValueError:continue
        test=states[states.sezon==season].copy();frac=1-test.period.to_numpy()/4
        rm=models[0].predict(test[cols]);rt=np.maximum(models[1].predict(test[cols]),0)
        rh=np.maximum((rt+rm)/2,0);ra=np.maximum((rt-rm)/2,0)
        pm=test.home.to_numpy()+rh-test.away.to_numpy()-ra
        pt=test.home.to_numpy()+rh+test.away.to_numpy()+ra
        actual_margin=test.home-test.away+test.remaining_margin
        actual_total=test.home+test.away+test.remaining_total
        p=norm.cdf(pm/(sigma[0]*np.sqrt(frac)))
        for i,row in enumerate(test.itertuples()):
            records.append(dict(mac_id=row.mac_id,season=season,period=row.period,
                predicted_margin=float(pm[i]),actual_margin=float(actual_margin.iloc[i]),
                predicted_total=float(pt[i]),actual_total=float(actual_total.iloc[i]),p=float(p[i]),
                total_sigma=float(sigma[1]*np.sqrt(frac[i])),
                frozen_prior_total=float(indexed.loc[row.mac_id,'total_prediction']),
                frozen_prior_p=float(indexed.loc[row.mac_id,'p']),
                regulation_tied=bool(row.regulation_tied)))
    evidence=pd.DataFrame(records);evidence.to_csv(root/'live_predictions.csv',index=False)
    for (season,period),part in evidence.groupby(['season','period']):
        decisive=part[~part.regulation_tied];y=(decisive.actual_margin>0).astype(int)
        results.append(dict(season=season,period=int(period),games=len(part),decisive_games=len(decisive),
            lead_accuracy=float(accuracy_score(y,decisive.p>=.5)),
            frozen_pregame_accuracy=float(accuracy_score(y,decisive.frozen_prior_p>=.5)),
            log_loss=float(log_loss(y,decisive.p,labels=[0,1])),
            brier=float(brier_score_loss(y,decisive.p)),
            total_mae=float(np.mean(abs(part.actual_total-part.predicted_total))),
            frozen_pregame_total_mae=float(np.mean(abs(part.actual_total-part.frozen_prior_total))),
            total_interval80_coverage=float((abs(part.actual_total-part.predicted_total)<=norm.ppf(.9)*part.total_sigma).mean())))
    (root/'live_summary.json').write_text(json.dumps(results,indent=2))
    (root/'manifest.json').write_text(json.dumps(dict(timestamp_utc=now.isoformat(),
        pregame_spec=cba_model.SPEC,live_spec='cba-remaining-ridge-v1',
        packages={name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn']},
        files={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [cba_model.DATA,Path('data/cba_quarters.parquet')]},
        source='RealGM public numeric schedule and quarter facts',
        live_method='Fixed Ridge alpha 10 on strictly earlier seasons; variance calibrated on preceding season. Same game never crosses season folds.',
        live_limitations='40 sampled test games in 2025-26, three correlated quarter-end observations per game; no within-quarter validation or automatic scoreboard feed. Regulation only.'),indent=2))
    print(json.dumps(dict(pregame=pre,live=results),indent=2))


if __name__=='__main__':main()
