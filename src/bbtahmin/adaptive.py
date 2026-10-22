"""Experimental monthly refits, selected using only the preceding season."""
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import competition_model as base
from .ozellik import build_features,FEATURES

SPEC='competition-monthly-prior-gate-v1'


def _predictions(x,g,history,test,monthly):
    out=np.empty((int(test.sum()),2));indices=np.flatnonzero(test)
    months=g.tarih_utc.dt.strftime('%Y-%m')
    for month in months[test].unique():
        local=months.iloc[indices].to_numpy()==month
        chosen=indices[local]
        cutoff=pd.Timestamp(month+'-01',tz='UTC')
        fit=history.copy()
        if monthly:fit=fit | (test & (g.tarih_utc<cutoff).to_numpy())
        if fit.sum()<150:raise ValueError('Insufficient prior training games')
        for j,y in enumerate([(g.ev_skor-g.dep_skor).to_numpy(float),(g.ev_skor+g.dep_skor).to_numpy(float)]):
            estimator=make_pipeline(StandardScaler(),Ridge(alpha=10.))
            estimator.fit(x.loc[fit,FEATURES],y[fit])
            out[local,j]=estimator.predict(x.iloc[chosen][FEATURES])
    return out


def fold(x,g,season):
    earlier=sorted(s for s,n in g.groupby('sezon').size().items() if s<season and n>=100)
    if len(earlier)<2:raise ValueError('Need two earlier seasons for independent selection')
    previous=earlier[-1]
    train=(g.sezon<previous).to_numpy();val=(g.sezon==previous).to_numpy();test=(g.sezon==season).to_numpy()
    actual=np.column_stack([(g.ev_skor-g.dep_skor).to_numpy(float),(g.ev_skor+g.dep_skor).to_numpy(float)])
    fixed=_predictions(x,g,train,val,False);rolling=_predictions(x,g,train,val,True)
    fixed_mae=np.mean(abs(actual[val]-fixed),axis=0);rolling_mae=np.mean(abs(actual[val]-rolling),axis=0)
    y=actual[val,0]>0
    fixed_acc=float(((fixed[:,0]>0)==y).mean());rolling_acc=float(((rolling[:,0]>0)==y).mean())
    # Fixed in advance: require improvements in BOTH error targets without lower winner accuracy.
    selected=bool(np.all(rolling_mae<.99*fixed_mae) and rolling_acc>=fixed_acc)
    residual=actual[val]-(rolling if selected else fixed)
    sigma=np.maximum(np.std(residual,axis=0,ddof=1),1.)
    predicted=_predictions(x,g,train|val,test,selected)
    predicted[:,1]+=float(residual[:,1].mean())
    info=dict(selection_season=previous,monthly_selected=selected,
        validation_games=int(val.sum()),fixed_margin_mae=float(fixed_mae[0]),monthly_margin_mae=float(rolling_mae[0]),
        fixed_total_mae=float(fixed_mae[1]),monthly_total_mae=float(rolling_mae[1]),
        fixed_accuracy=fixed_acc,monthly_accuracy=rolling_acc,
        rule='Monthly must reduce both validation MAEs by more than 1%, with no lower winner accuracy.')
    return predicted,sigma,info


def walk_forward(code,g=None):
    g=base.load(code) if g is None else g
    if set(g.lig)!={code}:raise ValueError('Competition mixing is forbidden')
    x=build_features(g);rows=[];selections=[]
    for season in sorted(g.sezon.unique())[2:]:
        values,sigma,info=fold(x,g,season);selections.append(dict(league=code,season=season,**info))
        for i,r in enumerate(g[g.sezon==season].itertuples()):
            rows.append(dict(mac_id=r.mac_id,lig=code,sezon=season,p=float(norm.cdf(values[i,0]/sigma[0])),
                y=int(r.ev_skor>r.dep_skor),margin=float(r.ev_skor-r.dep_skor),margin_prediction=float(values[i,0]),
                total=float(r.ev_skor+r.dep_skor),total_prediction=float(values[i,1]),monthly_selected=info['monthly_selected']))
    return pd.DataFrame(rows),selections


def predict(code,home,away,when):
    result=base.predict(code,home,away,when)
    date=pd.Timestamp(when).tz_convert('UTC');cutoff=date.floor('D')
    g=base.load(code);g=g[g.tarih_utc<cutoff].copy()
    season=f'{date.year if date.month>=7 else date.year-1}-{str(date.year+1 if date.month>=7 else date.year)[-2:]}'
    query=dict(mac_id=f'{code}_ADAPTIVE_QUERY',lig=code,sezon=season,tarih_utc=cutoff,
        ev=home,dep=away,ev_skor=np.nan,dep_skor=np.nan,tarafsiz_saha=False)
    g=pd.concat([g,pd.DataFrame([query])],ignore_index=True)
    values,sigma,info=fold(build_features(g),g,season)
    # Query is last in the target season's chronological order; include prior-month outcomes only.
    margin,total=map(float,values[-1]);total=max(total,0.);margin=float(np.clip(margin,-total,total))
    p=float(norm.cdf(margin/sigma[0]));z=norm.ppf(.9)
    result.update(model=SPEC,ev_kazanir=p,ev_skor=(total+margin)/2,dep_skor=(total-margin)/2,
        fark=margin,fark_80=[margin-z*sigma[0],margin+z*sigma[0]],toplam=total,
        toplam_80=[max(0.,total-z*sigma[1]),total+z*sigma[1]],tum_modeller={SPEC:p},adaptive_selection=info)
    return result
