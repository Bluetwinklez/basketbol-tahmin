"""Chronological, separate-league research for KBL, Japanese divisions and PBA cups.

Fixed learners, previous-season calibration/selection, no odds inputs. Optional
cup eras and current team promotions are not assumed interchangeable evidence.
"""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .ozellik import build_features,FEATURES
from .veri.asia import CODES,NAMES

SPEC='asia-separate-prior-policy-v1'


def load(code):
    if code not in CODES:raise ValueError('Unsupported Asian league')
    path=Path(f'data/asia/{code}.parquet')
    if not path.exists():raise ValueError('No collected archive for '+code)
    g=pd.read_parquet(path).sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
    if (set(g.lig)!={code} or g.mac_id.duplicated().any() or (g.ev==g.dep).any()
            or not np.isfinite(g[['ev_skor','dep_skor']].to_numpy(float)).all()
            or (g[['ev_skor','dep_skor']]<=0).any().any() or (g.ev_skor==g.dep_skor).any()):
        raise ValueError('Invalid or mixed Asian league dataset')
    return g


def fit_fold(g,x,season):
    counts=g.groupby('sezon').size()
    earlier=sorted(s for s,n in counts.items() if s<season and n>=50)
    if len(earlier)<2:raise ValueError('Two earlier seasons are required')
    previous=earlier[-1];train=(g.sezon<previous).to_numpy();val=(g.sezon==previous).to_numpy();test=(g.sezon==season).to_numpy()
    final_train=(g.sezon<season).to_numpy()
    if train.sum()<150 or val.sum()<50:raise ValueError('Need 150 training and 50 previous-season calibration games')
    target=(g.ev_skor-g.dep_skor).to_numpy(float);total=(g.ev_skor+g.dep_skor).to_numpy(float)
    y=(target>0).astype(int);score_predictions=[];calibration=[];validation=[]
    for values in (target,total):
        make=lambda:make_pipeline(StandardScaler(),Ridge(alpha=10.))
        inner=make().fit(x.loc[train,FEATURES],values[train]);pv=inner.predict(x.loc[val,FEATURES])
        final=make().fit(x.loc[final_train,FEATURES],values[final_train]);pt=final.predict(x.loc[test,FEATURES])
        residual=values[val]-pv;validation.append(pv);score_predictions.append(pt)
        calibration.append(dict(sigma=max(float(np.std(residual,ddof=1)),1.),bias=float(np.mean(residual))))
    days=g.loc[val,'tarih_utc'].dt.floor('D');unique=sorted(days.unique());boundary=unique[len(unique)//2]
    cal=(days<boundary).to_numpy();selection=~cal
    if min(cal.sum(),selection.sum())<20:raise ValueError('Need 20 games in disjoint calibration/selection halves')
    selection_sigma=max(float(np.std((target[val]-validation[0])[cal],ddof=1)),1.)
    clf=lambda:make_pipeline(StandardScaler(),LogisticRegression(C=1.,max_iter=1000))
    inner=clf().fit(x.loc[train,FEATURES],y[train]);final=clf().fit(x.loc[final_train,FEATURES],y[final_train])
    pv={'score':norm.cdf(validation[0]/selection_sigma),'logistic':inner.predict_proba(x.loc[val,FEATURES])[:,1],
        'elo':x.loc[val,'elo_p'].to_numpy()}
    pt={'score':norm.cdf(score_predictions[0]/calibration[0]['sigma']),
        'logistic':final.predict_proba(x.loc[test,FEATURES])[:,1],'elo':x.loc[test,'elo_p'].to_numpy()}
    pv['ensemble']=np.mean(list(pv.values()),axis=0);pt['ensemble']=np.mean(list(pt.values()),axis=0)
    def loss(p):
        p=np.clip(p[selection],1e-12,1-1e-12);labels=y[val][selection]
        return float(-np.mean(labels*np.log(p)+(1-labels)*np.log(1-p)))
    losses={name:loss(values) for name,values in pv.items()}
    # Fixed policy; no test-season winner or loss chooses the runtime model.
    selected=min(losses,key=lambda name:(losses[name],name))
    info=dict(season=season,previous_season=previous,training_games=int(train.sum()),calibration_games=int(cal.sum()),
        final_training_games=int(final_train.sum()),calibration_season_gap=int(season[:4])-int(previous[:4]),
        selection_games=int(selection.sum()),selection_window_start_utc=boundary.isoformat(),selected=selected,
        selection_log_loss=losses,rule='Lowest log loss on the second UTC-day half of the preceding season. Score probabilities calibrate on its first half. Fixed learners; test outcomes never select a candidate.')
    return pt,score_predictions,calibration,info


def walk_forward(code,g=None):
    g=load(code) if g is None else g
    if set(g.lig)!={code}:raise ValueError('League mixing forbidden')
    x=build_features(g);records=[];folds=[];skipped=[]
    for season in sorted(g.sezon.unique())[2:]:
        try:probs,scores,errors,info=fit_fold(g,x,season)
        except ValueError as e:
            skipped.append(dict(season=season,reason=str(e)));continue
        folds.append(info)
        for i,r in enumerate(g[g.sezon==season].itertuples()):
            margin=float(scores[0][i]);total=max(0.,float(scores[1][i]+errors[1]['bias']));margin=float(np.clip(margin,-total,total))
            past=g[g.tarih_utc<r.tarih_utc.floor('D')];recent=past[past.tarih_utc>=r.tarih_utc.floor('D')-pd.Timedelta(days=400)]
            counts=[int(((recent.ev==t)|(recent.dep==t)).sum()) for t in (r.ev,r.dep)]
            for name,p in {**probs,'selected_policy':probs[info['selected']]}.items():
                z=norm.ppf(.9);actual_total=float(r.ev_skor+r.dep_skor)
                records.append(dict(mac_id=r.mac_id,lig=code,sezon=season,tarih_utc=r.tarih_utc,variant=name,
                    p=float(p[i]),y=int(r.ev_skor>r.dep_skor),home_prediction=(total+margin)/2,away_prediction=(total-margin)/2,
                    actual_home=r.ev_skor,actual_away=r.dep_skor,margin_prediction=margin,total_prediction=total,
                    score_mae=(abs((total+margin)/2-r.ev_skor)+abs((total-margin)/2-r.dep_skor))/2,
                    total_absolute_error=abs(total-actual_total),margin_absolute_error=abs(margin-(r.ev_skor-r.dep_skor)),
                    total_in_80=bool(total-z*errors[1]['sigma']<=actual_total<=total+z*errors[1]['sigma']),
                    min_recent_games=min(counts),eligible=(min(counts)>=5 and max(p[i],1-p[i])>=.6 and info['calibration_season_gap']==1
                        and ((p[i]-.5)*margin>=0) and all(
                            len(past[(past.ev==t)|(past.dep==t)])>0 and
                            (r.tarih_utc.floor('D')-past.loc[(past.ev==t)|(past.dep==t),'tarih_utc'].max()).total_seconds()/86400<=60
                            for t in (r.ev,r.dep)))))
    return pd.DataFrame(records),folds,skipped


def predict(code,home,away,when):
    date=pd.Timestamp(when)
    if date.tzinfo is None:raise ValueError('Timezone-aware fixture required')
    date=date.tz_convert('UTC');cutoff=date.floor('D');g=load(code);g=g[g.tarih_utc<cutoff]
    catalog=json.loads(Path(f'data/asia/{code}_teams.json').read_text())
    if home==away or home not in catalog or away not in catalog:raise ValueError('Unknown or identical Asian team identity')
    year=date.year if date.month>=7 else date.year-1;season=f'{year}-{str(year+1)[-2:]}'
    if code.startswith('PBA_'):
        path=Path(f'data/asia/{code}_fixtures.parquet')
        fixtures=pd.read_parquet(path) if path.exists() else pd.DataFrame()
        matches=(fixtures[(fixtures.ev==home)&(fixtures.dep==away)&(pd.to_datetime(fixtures.tarih_utc,utc=True)==date)]
                 if not fixtures.empty else fixtures)
        if len(matches)!=1:raise ValueError('PBA predictions require an exact observed conference fixture; calendar July is not a season boundary')
        season=matches.iloc[0].sezon
    query=dict(mac_id=code+'_QUERY',lig=code,sezon=season,tarih_utc=date,ev=home,dep=away,ev_skor=np.nan,dep_skor=np.nan,
        tarafsiz_saha=code.startswith('PBA_'))
    all_g=pd.concat([g,pd.DataFrame([query])],ignore_index=True);x=build_features(all_g)
    probs,scores,errors,info=fit_fold(all_g,x,season)
    # fit_fold includes already completed target-season rows; select only QUERY.
    target=all_g[all_g.sezon==season];index=target.mac_id.tolist().index(query['mac_id'])
    margin=float(scores[0][index]);total=max(0.,float(scores[1][index]+errors[1]['bias']));margin=float(np.clip(margin,-total,total))
    p=float(probs[info['selected']][index]);z=norm.ppf(.9)
    recent=g[g.tarih_utc>=cutoff-pd.Timedelta(days=400)];counts={t:int(((recent.ev==t)|(recent.dep==t)).sum()) for t in (home,away)}
    return dict(lig=code,ev=home,dep=away,tarih_utc=date.isoformat(),model=SPEC+'/'+info['selected'],ev_kazanir=p,
        ev_skor=(total+margin)/2,dep_skor=(total-margin)/2,fark=margin,toplam=total,
        fark_80=[margin-z*errors[0]['sigma'],margin+z*errors[0]['sigma']],
        toplam_80=[max(0.,total-z*errors[1]['sigma']),total+z*errors[1]['sigma']],
        tum_modeller={k:float(v[index]) for k,v in probs.items()},az_veri=[t for t,n in counts.items() if n<5],
        recent_games=counts,uzatma=None,experimental=True,training_cutoff=cutoff.isoformat(),selection=info,
        dataset_sha256=hashlib.sha256(Path(f'data/asia/{code}.parquet').read_bytes()).hexdigest(),
        calibration_regime_gap=info['calibration_season_gap']>1,
        note='Separate-league pregame research, not validated live/score certainty. Models fit on earlier seasons, features withhold the entire UTC day. Cup rules, promotions, historical publication and neutral venues are not fully modeled.')
