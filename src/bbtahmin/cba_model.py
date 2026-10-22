"""CBA-only fixed-specification pregame score model, with chronological checks.

Historical scores are standardized to 40 regulation minutes before feature
construction. The factual archive is never rescaled on disk.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .ozellik import FEATURES,build_features

DATA=Path('data/cba_games.parquet')
SPEC='cba-ridge-per40-v1'


def load():
    if not DATA.exists():raise ValueError('Collect CBA data first: python -m bbtahmin cba-topla')
    g=pd.read_parquet(DATA).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    return g


def prepare(g):
    g=g.copy()
    for col in ['ev_skor','dep_skor']:
        g[col]=g[col].astype(float)*40/g.regulation_minutes
    return build_features(g),g


def fit(x,g,train,calibration,test):
    if train.sum()<200 or calibration.sum()<100:raise ValueError('Insufficient CBA training/calibration history')
    models=[];details=[]
    for target in [(g.ev_skor-g.dep_skor).to_numpy(),(g.ev_skor+g.dep_skor).to_numpy()]:
        def estimator():return make_pipeline(StandardScaler(),Ridge(alpha=10.))
        inner=estimator().fit(x.loc[train,FEATURES],target[train])
        residual=target[calibration]-inner.predict(x.loc[calibration,FEATURES])
        final=estimator().fit(x.loc[train|calibration,FEATURES],target[train|calibration])
        models.append(final.predict(x.loc[test,FEATURES]))
        details.append(dict(sigma=max(float(np.std(residual,ddof=1)),1.),bias=float(np.mean(residual))))
    return models,details


def predict(home,away,when):
    date=pd.Timestamp(when)
    if date.tzinfo is None:raise ValueError('CBA prediction time needs an explicit timezone')
    cutoff=pd.Timestamp(date.tz_convert('Asia/Shanghai').date(),tz='UTC')
    g=load();g=g[g.tarih_utc<cutoff].copy()
    if home==away:raise ValueError('Teams must differ')
    for team in [home,away]:
        recent=g[(g.tarih_utc>=cutoff-pd.Timedelta(days=400))&((g.ev==team)|(g.dep==team))]
        if len(recent)<5:raise ValueError(f'Insufficient recent CBA history: {team}')
    year=date.year if date.month>=7 else date.year-1
    season=f'{year}-{str(year+1)[-2:]}'
    query=dict(mac_id='CBA_QUERY',lig='CBA',sezon=season,tarih_utc=cutoff,
               ev=home,dep=away,ev_skor=np.nan,dep_skor=np.nan,regulation_minutes=40,tarafsiz_saha=False)
    all_g=pd.concat([g,pd.DataFrame([query])],ignore_index=True)
    x,scaled=prepare(all_g)
    past=sorted(s for s,n in g.groupby('sezon').size().items() if s<season and n>=100)
    if not past:raise ValueError('No completed CBA calibration season')
    val=(scaled.sezon==past[-1]).to_numpy()
    train=(scaled.sezon<past[-1]).to_numpy();test=(scaled.mac_id=='CBA_QUERY').to_numpy()
    values,errors=fit(x,scaled,train,val,test)
    margin=float(values[0][0]);total=float(values[1][0]+errors[1]['bias'])
    minutes=40 if year>=2025 else 48;factor=minutes/40
    margin*=factor;total*=factor;sm=errors[0]['sigma']*factor;st=errors[1]['sigma']*factor
    p=float(norm.cdf(margin/sm));z=norm.ppf(.9)
    fingerprint=hashlib.sha256(DATA.read_bytes()).hexdigest()
    evidence=Path('docs/kanit/cba/manifest.json')
    manifest=json.loads(evidence.read_text()) if evidence.exists() else {}
    return dict(lig='CBA',ev=home,dep=away,tarih_utc=date.tz_convert('UTC').isoformat(),model=SPEC,
        ev_kazanir=p,ev_skor=(total+margin)/2,dep_skor=(total-margin)/2,
        fark=margin,fark_80=[margin-z*sm,margin+z*sm],toplam=total,toplam_80=[total-z*st,total+z*st],
        tum_modeller={SPEC:p},uzatma=None,az_veri=[],regulation_minutes=minutes,
        training_cutoff=cutoff.isoformat(),calibration_season=past[-1],experimental=True,
        dataset_sha256=fingerprint,dataset_matches_evaluation=manifest.get('files',{}).get(str(DATA))==fingerprint,
        note='CBA-only research model. Historical overtime totals may be included; live projections target regulation.')


def walk_forward(g=None):
    g=load() if g is None else g
    x,scaled=prepare(g);records=[]
    seasons=sorted(g.sezon.unique())
    for i,season in enumerate(seasons):
        if i<2:continue
        train=(scaled.sezon<seasons[i-1]).to_numpy();val=(scaled.sezon==seasons[i-1]).to_numpy();test=(scaled.sezon==season).to_numpy()
        if train.sum()<200 or val.sum()<100:continue
        values,errors=fit(x,scaled,train,val,test)
        for j,row in enumerate(g[test].itertuples()):
            factor=row.regulation_minutes/40
            records.append(dict(mac_id=row.mac_id,sezon=season,tarih_utc=row.tarih_utc,
                margin_prediction=float(values[0][j]*factor),total_prediction=float((values[1][j]+errors[1]['bias'])*factor),
                p=float(norm.cdf(values[0][j]/errors[0]['sigma'])),
                y=int(row.ev_skor>row.dep_skor),margin=float(row.ev_skor-row.dep_skor),
                total=float(row.ev_skor+row.dep_skor)))
    return pd.DataFrame(records)
