"""Regularized team-difference winner model on connected senior-women schedules.

L2 coefficients shrink sparse teams toward a zero population prior. This is not
an explicit Bayesian league hierarchy and does not identify absolute league strength.
"""
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression


def design(g,vocabulary):
    rows=[];columns=[];values=[]
    for i,r in enumerate(g.itertuples()):
        for team,value in [(r.ev,1.),(r.dep,-1.)]:
            if team in vocabulary:rows.append(i);columns.append(vocabulary[team]);values.append(value)
        rows.append(i);columns.append(len(vocabulary));values.append(0. if bool(r.tarafsiz_saha) else 1.)
    return csr_matrix((values,(rows,columns)),shape=(len(g),len(vocabulary)+1))


def predict(history,queries,cutoff):
    cutoff=pd.Timestamp(cutoff)
    history=history[history.tarih_utc<cutoff.floor('D')].copy()
    if len(history)<150:raise ValueError('Insufficient past club-strength observations')
    vocabulary={t:i for i,t in enumerate(sorted(set(history.ev)|set(history.dep)))}
    x=design(history,vocabulary);y=(history.ev_skor>history.dep_skor).astype(int)
    age=(cutoff-history.tarih_utc).dt.total_seconds()/86400
    weights=np.exp(-np.log(2)*age/365)
    model=LogisticRegression(C=1.,fit_intercept=False,max_iter=1000).fit(x,y,sample_weight=weights)
    return model.predict_proba(design(queries,vocabulary))[:,1]


def candidate(prepared,season,previous):
    from pathlib import Path
    g=prepared['base'][0];exposure=prepared['exposure'].copy()
    path=Path('data/domestic/CZ_W_ZBL.parquet')
    if path.exists():
        domestic=pd.read_parquet(path)
        if set(domestic.gender)!={'Women'}:raise ValueError('Only senior women domestic observations allowed')
        exposure=pd.concat([exposure,domestic],ignore_index=True)
    if exposure.mac_id.duplicated().any():raise ValueError('Duplicate strength observations')
    validation=g[g.sezon==previous];test=g[g.sezon==season]
    train=exposure[exposure.sezon<previous];final=exposure[exposure.sezon<season]
    return (predict(train,validation,validation.tarih_utc.min().floor('D')),
            predict(final,test,test.tarih_utc.min().floor('D')))
