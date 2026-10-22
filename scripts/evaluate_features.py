"""Chronological matched-game ablation for lagged four-factor profiles.

No same-game participants, injuries, market quotes or shots enter these models.
All variants use the same fold-specific recorded Elo/EWMA parameters and games.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import accuracy_score,brier_score_loss,log_loss,mean_absolute_error
from threadpoolctl import threadpool_limits

from bbtahmin.four_factors import build_factors,load_boxes,FACTOR_FEATURES
from bbtahmin.model import regression,fit_predict
from bbtahmin.ozellik import build_features,FEATURES


def run(leagues=('NBA','E','U'),first=2021,output='docs/kanit/feature_research'):
    games=pd.read_parquet('data/maclar.parquet')
    games=games[(games.ev_skor>0)&(games.dep_skor>0)]
    parameters=json.loads(Path('docs/kanit/parametreler.json').read_text('utf8'))
    boxes=load_boxes();rows=[]
    now=pd.Timestamp.now(tz='UTC');current=now.year if now.month>=7 else now.year-1
    for league in leagues:
        g=games[games.lig==league].sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
        factors=build_factors(g,boxes)[FACTOR_FEATURES]
        margin=(g.ev_skor-g.dep_skor).to_numpy(dtype=float)
        total=(g.ev_skor+g.dep_skor).to_numpy(dtype=float)
        y=(margin>0).astype(int)
        seasons=sorted(g.sezon.unique())
        for season in seasons:
            if not first<=int(season[:4])<current:
                continue
            recorded=[p for p in parameters if p.get('lig')==league and p.get('sezon')==season]
            mov=next((p for p in recorded if p.get('model')=='mov'),None)
            if mov is None:
                continue
            alpha=next((p['alpha'] for p in recorded if p.get('model')=='ewma'),.2)
            prior=seasons[seasons.index(season)-1]
            train=(g.sezon<prior).to_numpy();val=(g.sezon==prior).to_numpy();test=(g.sezon==season).to_numpy()
            x=build_features(g,k=mov['k'],advantage=mov['home_advantage'],shrink=mov['shrink'],alpha=alpha,mov=True)
            x=pd.concat([x,factors],axis=1)
            for extra in [False,True]:
                cols=FEATURES+(FACTOR_FEATURES if extra else [])
                pm,rm=regression(x,margin,train,val,test,cols)
                pt,rt=regression(x,total,train,val,test,cols);pt+=rt['residual_mean']
                probabilities={'score':norm.cdf(pm/max(rm['residual_sigma'],1e-6)),
                               'logistic':fit_predict('logistic',x,y,train,val,test,cols)[0]}
                for model,p in probabilities.items():
                    rows.append(dict(lig=league,sezon=season,variant=model+('_factors' if extra else ''),n=int(test.sum()),
                        log_loss=log_loss(y[test],np.clip(p,1e-6,1-1e-6),labels=[0,1]),
                        brier=brier_score_loss(y[test],p),accuracy=accuracy_score(y[test],p>=.5),
                        margin_mae=mean_absolute_error(margin[test],pm),total_mae=mean_absolute_error(total[test],pt)))
            print(league,season,int(test.sum()),flush=True)
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    folds=pd.DataFrame(rows);folds.to_csv(path/'folds.csv',index=False)
    summary=[]
    for (league,variant),part in folds.groupby(['lig','variant']):
        summary.append(dict(lig=league,variant=variant,n=int(part.n.sum()),
            **{c:float(np.average(part[c],weights=part.n)) for c in ['log_loss','brier','accuracy','margin_mae','total_mae']}))
    table=pd.DataFrame(summary);table.to_csv(path/'summary.csv',index=False)
    meta=dict(timestamp=now.isoformat(),dataset_sha256=hashlib.sha256(Path('data/maclar.parquet').read_bytes()).hexdigest(),
        features=FACTOR_FEATURES,alpha=.15,rule='All UTC-day profiles are emitted before any same-day box updates.',
        evaluation='Identical games, prior-season validation; current incomplete season excluded.',
        exclusions='No retrospective participant labels or market odds. No selection on test labels.',
        limitation='Exploratory ablation; no confidence interval or prospective performance claim.')
    (path/'method.json').write_text(json.dumps(meta,indent=2),'utf8')
    print(table.to_string(index=False))
    return table


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ligler',nargs='+',default=['NBA','E','U'])
    p.add_argument('--ilk-test',type=int,default=2021)
    p.add_argument('--cikti',default='docs/kanit/feature_research')
    args=p.parse_args()
    with threadpool_limits(limits=1):
        run(args.ligler,args.ilk_test,args.cikti)
