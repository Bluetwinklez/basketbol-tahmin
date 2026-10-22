"""Chronological winner research with explicit source history and prior-only selection."""
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss,brier_score_loss
from . import competition_model as base
from .ozellik import build_features,FEATURES

SPEC='winner-prior-selection-v1'


def women_history(g):
    """Share senior WOMEN organisation histories across two cups, never men's data."""
    elw=Path('data/competitions/ELW.parquet');early=Path('data/competitions/ECW_early.parquet')
    if not elw.exists() or not early.exists():raise ValueError('Run women-history collector first')
    old=pd.read_parquet(early);side=pd.read_parquet(elw)
    if set(g.lig)!={'ECW'} or set(old.lig)!={'ECW'} or set(side.lig)!={'ELW'}:
        raise ValueError('Senior women competition identity mismatch')
    if not (side.ev.str.startswith('ELW_').all() and side.dep.str.startswith('ELW_').all()):raise ValueError('Mixed team namespace')
    extended=pd.concat([old,g],ignore_index=True).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if extended.mac_id.duplicated().any():raise ValueError('Duplicate target history')
    side=side.copy()
    side['lig']='ECW';side['ev']=side.ev.str.replace('ELW_','ECW_',n=1);side['dep']=side.dep.str.replace('ELW_','ECW_',n=1)
    combined=pd.concat([extended,side],ignore_index=True).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if combined.mac_id.duplicated().any():raise ValueError('Duplicate cross-cup game')
    x=build_features(combined).set_index('mac_id').loc[extended.mac_id].reset_index()
    return extended,x,combined


def _masks(g,season,previous):
    return (g.sezon<previous).to_numpy(),(g.sezon==previous).to_numpy(),(g.sezon==season).to_numpy()


def _candidate(g,x,season,previous,kind):
    cols=[*FEATURES,*[c for c in x.columns if c.startswith('dom_')]]
    train,val,test=_masks(g,season,previous)
    if train.sum()<150 or val.sum()<100:raise ValueError('Insufficient chronological training/calibration data')
    target=(g.ev_skor-g.dep_skor).to_numpy(float);y=(target>0).astype(int)
    if kind=='elo':return x.loc[val,'elo_p'].to_numpy(),x.loc[test,'elo_p'].to_numpy()
    estimator=lambda:make_pipeline(StandardScaler(),Ridge(alpha=10.)) if kind=='ridge' else make_pipeline(StandardScaler(),LogisticRegression(C=1.,max_iter=1000))
    inner=estimator().fit(x.loc[train,cols],target[train] if kind=='ridge' else y[train])
    final=estimator().fit(x.loc[train|val,cols],target[train|val] if kind=='ridge' else y[train|val])
    if kind=='ridge':
        pv=inner.predict(x.loc[val,cols]);sigma=max(float(np.std(target[val]-pv,ddof=1)),1.)
        return norm.cdf(pv/sigma),norm.cdf(final.predict(x.loc[test,cols])/sigma)
    return inner.predict_proba(x.loc[val,cols])[:,1],final.predict_proba(x.loc[test,cols])[:,1]


def prepare(code,g=None):
    g=base.load(code) if g is None else g
    if set(g.lig)!={code}:raise ValueError('Competition mixing is forbidden')
    result=dict(base=(g,build_features(g)),exposure=g)
    if code=='ECW':
        extended,x,combined=women_history(g);result['women']=(extended,x);result['exposure']=combined
    domestic=Path('data/domestic/CZ_W_ZBL.parquet')
    if code=='ECW' and domestic.exists():
        from .domestic_features import features
        base_features=result['base'][1].reset_index(drop=True)
        extra=features(g,pd.read_parquet(domestic)).drop(columns='mac_id')
        result['domestic']=(g,pd.concat([base_features,extra],axis=1))
    return result


def _metrics(y,p):
    return dict(correct=int(((p>=.5)==y).sum()),accuracy=float(((p>=.5)==y).mean()),
                log_loss=float(log_loss(y,p,labels=[0,1])),brier=float(brier_score_loss(y,p)))


def fold(code,prepared,season):
    g,x=prepared['base'];previous=sorted(s for s in g.sezon.unique() if s<season)[-1]
    val=g.sezon==previous;test=g.sezon==season
    y=(g.loc[val,'ev_skor'].to_numpy()>g.loc[val,'dep_skor'].to_numpy()).astype(int)
    candidates={};validation={}
    specs=[('score','base','ridge'),('logistic','base','logistic'),('elo','base','elo')]
    if code=='ECW':specs += [('women_score','women','ridge'),('women_logistic','women','logistic')]
    if 'domestic' in prepared:specs += [('domestic_score','domestic','ridge'),('domestic_logistic','domestic','logistic')]
    for name,representation,kind in specs:
        data,features=prepared[representation]
        pv,pt=_candidate(data,features,season,previous,kind)
        # Validation and target season rows must be identical across representations.
        assert data.loc[data.sezon==previous,'mac_id'].tolist()==g.loc[val,'mac_id'].tolist()
        assert data.loc[data.sezon==season,'mac_id'].tolist()==g.loc[test,'mac_id'].tolist()
        candidates[name]=pt;validation[name]=_metrics(y,pv)
    if code=='ECW':
        from .club_strength import candidate
        pv,pt=candidate(prepared,season,previous)
        candidates['club_strength']=pt;validation['club_strength']=_metrics(y,pv)
    reference=validation['score'];minimum_gain=math.ceil(len(y)*.01)
    eligible=[name for name,m in validation.items() if name!='score' and
        m['correct']>=reference['correct']+minimum_gain and m['log_loss']<=reference['log_loss']-.005 and m['brier']<=reference['brier']]
    selected=min(eligible,key=lambda name:(-validation[name]['correct'],validation[name]['log_loss'],name)) if eligible else 'score'
    info=dict(league=code,season=season,selection_season=previous,validation_games=len(y),selected=selected,validation=validation,
        rule='At least ceil(1% of validation games) extra correct, log loss lower by >=0.005 and no worse Brier; select by correct then log loss. Earlier season only.')
    return candidates,info


def history_counts(exposure,home,away,when):
    cutoff=pd.Timestamp(when).tz_convert('UTC').floor('D')
    past=exposure[(exposure.tarih_utc<cutoff)&(exposure.tarih_utc>=cutoff-pd.Timedelta(days=400))]
    return {t:int(((past.ev==t)|(past.dep==t)).sum()) for t in [home,away]}


def walk_forward(code,g=None):
    prepared=prepare(code,g);g=prepared['base'][0];records=[];selections=[]
    for season in sorted(g.sezon.unique())[2:]:
        candidates,info=fold(code,prepared,season);selections.append(info)
        for j,r in enumerate(g[g.sezon==season].itertuples()):
            counts=history_counts(prepared['exposure'],r.ev,r.dep,r.tarih_utc)
            for name,values in {**candidates,'selected_policy':candidates[info['selected']]}.items():
                p=float(values[j]);eligible=min(counts.values())>=5 and max(p,1-p)>=.6
                records.append(dict(mac_id=r.mac_id,lig=code,sezon=season,variant=name,p=p,y=int(r.ev_skor>r.dep_skor),
                    min_recent_games=min(counts.values()),eligible=eligible))
    return pd.DataFrame(records),selections
