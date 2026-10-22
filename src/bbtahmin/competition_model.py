"""Independent fixed-specification models for ECW women, FEC men and VTB men."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .ozellik import build_features,FEATURES

CODES=('ECW','FEC','VTB')
NAMES={'ECW':'EuroCup Women','FEC':'FIBA Europe Cup','VTB':'VTB United League'}
SPEC='separate-competition-ridge-v1'


def load(code):
    if code not in CODES:raise ValueError('Unsupported competition')
    path=Path(f'data/competitions/{code}.parquet')
    if not path.exists():raise ValueError('Run python -m bbtahmin lig-topla')
    g=pd.read_parquet(path).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if set(g.lig)!={code} or g.mac_id.duplicated().any():raise ValueError('Mixed or duplicate competition data')
    return g


def fit(x,g,train,val,test):
    if train.sum()<150 or val.sum()<100:raise ValueError('Need at least 150 training and 100 calibration games')
    predictions=[];errors=[]
    for target in [(g.ev_skor-g.dep_skor).to_numpy(float),(g.ev_skor+g.dep_skor).to_numpy(float)]:
        def estimator():return make_pipeline(StandardScaler(),Ridge(alpha=10.))
        inner=estimator().fit(x.loc[train,FEATURES],target[train])
        residual=target[val]-inner.predict(x.loc[val,FEATURES])
        final=estimator().fit(x.loc[train|val,FEATURES],target[train|val])
        predictions.append(final.predict(x.loc[test,FEATURES]))
        errors.append(dict(sigma=max(float(np.std(residual,ddof=1)),1.),bias=float(np.mean(residual))))
    return predictions,errors


def predict(code,home,away,when):
    date=pd.Timestamp(when)
    if pd.isna(date) or date.tzinfo is None:raise ValueError('Timezone-aware fixture time required')
    cutoff=date.tz_convert('UTC').floor('D')
    g=load(code);g=g[g.tarih_utc<cutoff].copy()
    catalog=json.loads(Path(f'data/competitions/{code}_teams.json').read_text())
    if home==away or home not in catalog or away not in catalog:raise ValueError('Unknown or identical team identity')
    year=date.year if date.month>=7 else date.year-1;season=f'{year}-{str(year+1)[-2:]}'
    earlier=sorted(s for s,n in g.groupby('sezon').size().items() if s<season and n>=100)
    if not earlier:raise ValueError('No completed calibration season')
    query=dict(mac_id=f'{code}_QUERY',lig=code,sezon=season,tarih_utc=cutoff,
               ev=home,dep=away,ev_skor=np.nan,dep_skor=np.nan,tarafsiz_saha=False)
    all_g=pd.concat([g,pd.DataFrame([query])],ignore_index=True)
    x=build_features(all_g)
    train=(all_g.sezon<earlier[-1]).to_numpy();val=(all_g.sezon==earlier[-1]).to_numpy()
    test=(all_g.mac_id==query['mac_id']).to_numpy()
    values,errors=fit(x,all_g,train,val,test)
    margin=float(values[0][0]);total=float(values[1][0]+errors[1]['bias']);z=norm.ppf(.9)
    recent=g[g.tarih_utc>=cutoff-pd.Timedelta(days=400)]
    counts={t:int(((recent.ev==t)|(recent.dep==t)).sum()) for t in [home,away]}
    low=[t for t,n in counts.items() if n<5]
    # Cold-start estimates remain visible and explicitly marked; never invent history.
    sm=errors[0]['sigma'];st=errors[1]['sigma']
    margin=float(np.clip(margin,-max(total,0.),max(total,0.)));total=max(0.,total)
    p=float(norm.cdf(margin/sm));path=Path(f'data/competitions/{code}.parquet')
    return dict(lig=code,ev=home,dep=away,tarih_utc=date.tz_convert('UTC').isoformat(),
        model=SPEC,ev_kazanir=p,ev_skor=max(0.,(total+margin)/2),dep_skor=max(0.,(total-margin)/2),
        fark=margin,fark_80=[margin-z*sm,margin+z*sm],toplam=total,toplam_80=[max(0.,total-z*st),total+z*st],
        tum_modeller={SPEC:p},uzatma=None,az_veri=low,recent_games=counts,
        training_cutoff=cutoff.isoformat(),calibration_season=earlier[-1],experimental=True,
        dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        note='Independent competition/gender model. Low-history forecasts rely heavily on league priors; their intervals are not separately validated. Historical scores may include overtime; ties excluded from binary winner evaluation.')


def walk_forward(code,g=None):
    g=load(code) if g is None else g
    if set(g.lig)!={code}:raise ValueError('Competition mixing is forbidden')
    x=build_features(g);rows=[];seasons=sorted(g.sezon.unique())
    for i,season in enumerate(seasons):
        if i<2:continue
        train=(g.sezon<seasons[i-1]).to_numpy();val=(g.sezon==seasons[i-1]).to_numpy();test=(g.sezon==season).to_numpy()
        if train.sum()<150 or val.sum()<100:continue
        values,errors=fit(x,g,train,val,test)
        history=g[g.tarih_utc<g[test].tarih_utc.max().floor('D')]
        for j,row in enumerate(g[test].itertuples()):
            recent=history[(history.tarih_utc>=row.tarih_utc.floor('D')-pd.Timedelta(days=400))&(history.tarih_utc<row.tarih_utc.floor('D'))]
            low=any(((recent.ev==t)|(recent.dep==t)).sum()<5 for t in [row.ev,row.dep])
            sm=errors[0]['sigma']
            rows.append(dict(mac_id=row.mac_id,lig=code,sezon=season,
                p=float(norm.cdf(values[0][j]/sm)),y=int(row.ev_skor>row.dep_skor),
                margin=float(row.ev_skor-row.dep_skor),margin_prediction=float(values[0][j]),
                total=float(row.ev_skor+row.dep_skor),total_prediction=float(values[1][j]+errors[1]['bias']),low_history=bool(low)))
    return pd.DataFrame(rows)
