import json
import hashlib
import importlib.metadata
import sys
from itertools import product
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import log_loss,brier_score_loss,accuracy_score,mean_absolute_error
from .ozellik import build_features,FEATURES
from .kutu_ozellik import kutu_ozellikleri,yukle,KUTU_FEATURES,KUTU_LIGLERI
from .eksik_ozellik import eksik_ozellikleri,EKSIK_FEATURES,EKSIK_LIGLERI,yukle as eksik_yukle
from .model import fit_predict,regression
from .odds import american_decimal,no_vig,simulate

# Elo arama ızgarası (değerler her pencerede yalnız eğitim/doğrulama sezonlarıyla seçilir).
ELO_K=[10.,20.,30.]
ELO_HOME=[0.,50.,100.]
ELO_SHRINK=[0.,.25,.5]

def scores(y,p):
    return dict(log_loss=float(log_loss(y,np.clip(p,1e-6,1-1e-6),labels=[0,1])),
        brier=float(brier_score_loss(y,p)),accuracy=float(accuracy_score(y,p>=.5)))
def run(ligler=None,cikti='docs/kanit',first_test=None):
    """ligler verilirse yalnız onlar; cikti başka klasörse rapor/grafik/EDA üretilmez (deneme koşusu)."""
    output=Path(cikti); output.mkdir(parents=True,exist_ok=True)
    deneme=cikti!='docs/kanit'
    all_games=pd.read_parquet('data/maclar.parquet')
    all_games=all_games[(all_games.ev_skor>0) & (all_games.dep_skor>0)]
    rows,params,predictions=[],[],[]
    kutu,oyuncular=yukle()
    oyuncu_mac=eksik_yukle()
    if ligler: all_games=all_games[all_games.lig.isin(ligler)]
    for league,g in all_games.groupby('lig'):
        g=g.sort_values(['tarih_utc','mac_id']).reset_index(drop=True)
        y=(g.ev_skor>g.dep_skor).to_numpy(dtype=int)
        margin=(g.ev_skor-g.dep_skor).to_numpy(dtype=float)
        total=(g.ev_skor+g.dep_skor).to_numpy(dtype=float)
        seasons=sorted(g.sezon.unique())
        # Kutu skor özellikleri Elo parametresine bağlı değil: lig başına bir kez hesaplanır.
        cols=list(FEATURES); ekler=[]
        if kutu is not None and league in KUTU_LIGLERI and kutu.mac_id.str.startswith(league).any():
            ekler.append(kutu_ozellikleri(g,kutu,oyuncular).set_index('mac_id').loc[g.mac_id].reset_index(drop=True)[KUTU_FEATURES])
            cols+=KUTU_FEATURES
        if oyuncu_mac is not None and league in EKSIK_LIGLERI:
            ekler.append(eksik_ozellikleri(g,oyuncu_mac).set_index('mac_id').loc[g.mac_id].reset_index(drop=True)[EKSIK_FEATURES])
            cols+=EKSIK_FEATURES
        cache={}
        # Feature parameters are selected using only preceding-season validation.
        for mov in [False,True]:
            for k,h,s in product(ELO_K,ELO_HOME,ELO_SHRINK):
                key=(mov,k,h,s)
                cache[key]=build_features(g,k=k,advantage=h,shrink=s,mov=mov)
        ewma_cache={}
        for i,season in enumerate(seasons):
            if first_test is not None and int(season[:4])<first_test:
                continue
            if i<2:
                params.append(dict(lig=league,sezon=season,status='yapılmadı: iki geçmiş sezon gerekli'))
                continue
            train=(g.sezon<seasons[i-1]).to_numpy()
            val=(g.sezon==seasons[i-1]).to_numpy()
            test=(g.sezon==season).to_numpy()
            selected={}
            for mov,name in [(False,'elo'),(True,'mov')]:
                keys=[key for key in cache if key[0]==mov]
                losses=[scores(y[val],cache[key].loc[val,'elo_p'].to_numpy())['log_loss'] for key in keys]
                best=keys[int(np.argmin(losses))]
                selected[name]=best
                params.append(dict(lig=league,sezon=season,model=name,k=best[1],home_advantage=best[2],
                    shrink=best[3],ewma_alpha=.2,validation_season=seasons[i-1],candidates=[
                        dict(k=key[1],home=key[2],shrink=key[3],log_loss=loss) for key,loss in zip(keys,losses)]))
            x=cache[selected['mov']]
            # Learn EWMA decay on the training holdout, keeping Elo selection frozen.
            alpha_losses=[]; alpha_features=[]
            for alpha in [.1,.3]:
                key=selected['mov']
                if (key,alpha) not in ewma_cache:
                    ewma_cache[key,alpha]=build_features(g,k=key[1],advantage=key[2],shrink=key[3],alpha=alpha,mov=True)
                f=ewma_cache[key,alpha]
                from .model import estimator
                m=estimator('logistic',1.).fit(f.loc[train,FEATURES],y[train])
                pp=m.predict_proba(f.loc[val,FEATURES])[:,1]
                alpha_losses.append(scores(y[val],pp)['log_loss']);alpha_features.append(f)
            alpha_index=int(np.argmin(alpha_losses));x=alpha_features[alpha_index]
            if ekler:
                x=pd.concat([x,*ekler],axis=1)
            params.append(dict(lig=league,sezon=season,model='ewma',alpha=[.1,.3][alpha_index],validation_losses=alpha_losses))
            pm,rm=regression(x,margin,train,val,test,cols)
            pt,rt=regression(x,total,train,val,test,cols)
            # Skorlar yıllar içinde arttığı için toplam her sezon 2-5 sayı düşük kalıyordu; doğrulama
            # sezonundaki ortalama artık eklenir. (Lig seviyesinden sapma hedefi denendi, MAE'yi kötüleştirdi.)
            pt=pt+rt['residual_mean']
            params.extend([dict(lig=league,sezon=season,model='margin_ridge',**rm),
                           dict(lig=league,sezon=season,model='total_ridge',**rt)])
            # "Ev sahibi kazanır": her maçta ev sahibini seçer; olasılığı eğitim penceresindeki ev galibiyet oranıdır.
            home_rate=float(y[train|val].mean())
            params.append(dict(lig=league,sezon=season,model='home',home_win_rate=home_rate))
            probabilities={'home':np.full(test.sum(),home_rate),'elo':cache[selected['elo']].loc[test,'elo_p'].to_numpy(),
                           'mov_elo':cache[selected['mov']].loc[test,'elo_p'].to_numpy()}
            for kind in ['logistic','hist_gradient_boosting']:
                probabilities[kind],details=fit_predict(kind,x,y,train,val,test,cols)
                params.append(dict(lig=league,sezon=season,model=kind,**details))
            # Skor modeli: Ridge fark tahmini ve doğrulama sezonundaki artık sapmasıyla normal dağılım.
            probabilities['skor']=norm.cdf(pm/max(rm['residual_sigma'],1e-6))
            # Topluluk: birbirinden farklı hata yapan üç modelin olasılık ortalaması (ağırlık ayarlanmıyor).
            probabilities['topluluk']=np.mean([probabilities['logistic'],probabilities['mov_elo'],probabilities['skor']],axis=0)
            margins={'home':np.full(test.sum(),margin[train|val].mean()),'logistic':pm,'hist_gradient_boosting':pm,
                     'skor':pm,'topluluk':pm}
            totals={'home':np.full(test.sum(),total[train|val].mean()),'logistic':pt,'hist_gradient_boosting':pt,
                    'skor':pt,'topluluk':pt}
            for baseline,key in [('elo',selected['elo']),('mov_elo',selected['mov'])]:
                from sklearn.linear_model import LinearRegression
                f=cache[key]
                columns=['elo_diff','home']
                fit=LinearRegression().fit(f.loc[train|val,columns],margin[train|val])
                margins[baseline]=fit.predict(f.loc[test,columns])
                totals[baseline]=np.full(test.sum(),total[train|val].mean())
            for name,p in probabilities.items():
                result=dict(lig=league,sezon=season,model=name,n=int(test.sum()),**scores(y[test],p),
                    margin_mae=float(mean_absolute_error(margin[test],margins[name])),
                    total_mae=float(mean_absolute_error(total[test],totals[name])))
                rows.append(result)
                for pos,(j,r) in enumerate(g.loc[test].iterrows()):
                    predictions.append(dict(mac_id=r.mac_id,lig=league,sezon=season,model=name,y=int(y[j]),
                        p=float(p[pos]),margin=float(margin[j]),margin_prediction=float(margins[name][pos]),
                        total=float(total[j]),total_prediction=float(totals[name][pos]),
                        ridge_handicap0_probability=float(norm.cdf(pm[pos]/max(rm['residual_sigma'],1e-6))),
                        total_over_prediction=None))
            pd.DataFrame(rows).to_csv(output/'metrikler.csv',index=False)
            (output/'parametreler.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),'utf8')
            print(f'{league} {season}: {int(test.sum())} maç değerlendirildi',flush=True)
    pred=pd.DataFrame(predictions)
    metrics=pd.DataFrame(rows)
    metrics.to_csv(output/'metrikler.csv',index=False)
    pred.to_csv(output/'tahminler.csv',index=False)
    (output/'parametreler.json').write_text(json.dumps(params,ensure_ascii=False,indent=2),'utf8')
    aggregate=[]
    calibration=[]
    if not pred.empty:
        for (league,model),part in pred.groupby(['lig','model']):
            aggregate.append(dict(lig=league,model=model,n=len(part),**scores(part.y,part.p),
                margin_mae=float(np.mean(abs(part.margin-part.margin_prediction)))))
        for (league,season,model),part in pred.groupby(['lig','sezon','model']):
            bins=np.minimum((part.p*10).astype(int),9)
            for b in range(10):
                group=part[bins==b]
                calibration.append(dict(lig=league,sezon=season,model=model,bin=b,n=len(group),
                    predicted=float(group.p.mean()) if len(group) else None,
                    observed=float(group.y.mean()) if len(group) else None))
    pd.DataFrame(aggregate).to_csv(output/'toplam.csv',index=False)
    for name in ['piyasa.csv','bahis.csv','harman.json']:
        if (output/name).exists(): (output/name).unlink()
    if Path('data/oranlar.parquet').exists() and not pred.empty:
        market,bets=market_and_betting(pred,pd.read_parquet('data/oranlar.parquet'))
        market.to_csv(output/'piyasa.csv',index=False)
        bets.to_csv(output/'bahis.csv',index=False)
        harman=dict(NBA=harman_katsayilari(pred,pd.read_parquet('data/oranlar.parquet')))
        (output/'harman.json').write_text(json.dumps(harman,ensure_ascii=False,indent=2),'utf8')
    pd.DataFrame(calibration).to_csv(output/'kalibrasyon.csv',index=False)
    all_games.groupby(['lig','sezon']).size().rename('mac_sayisi').to_csv(output/'mac_sayilari.csv')
    profile=dict(rows=len(all_games),missing=all_games.isna().sum().to_dict(),
        duplicates=int(all_games.mac_id.duplicated().sum()),timestamp=datetime.now(timezone.utc).isoformat())
    (output/'profil.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2),'utf8')
    manifest=dict(timestamp=datetime.now(timezone.utc).isoformat(),first_test=first_test,
        python=sys.version,packages={name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn']},
        prediction_sha256=hashlib.sha256((output/'tahminler.csv').read_bytes()).hexdigest(),
        dataset_sha256=hashlib.sha256(Path('data/maclar.parquet').read_bytes()).hexdigest(),
        absence_leagues=sorted(EKSIK_LIGLERI),box_leagues=sorted(KUTU_LIGLERI),base_features=FEATURES,
        files={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ['parametreler.json','metrikler.csv']})
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),'utf8')
    if deneme: return metrics
    plot_calibration(pred)
    from .eda import run_eda
    run_eda()
    from .report import write_report
    write_report()
    return metrics

THRESHOLDS=[.01,.02,.03,.05,.075,.1]
BET_MODELS=['logistic','hist_gradient_boosting','mov_elo']
HARMAN_MODELS=['skor','topluluk','logistic']

def _logit(p):
    p=np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6)
    return np.log(p/(1-p))

def harman_fit(part):
    """Cezasız lojistik: y ~ logit(piyasa) + logit(model). (sabit, piyasa katsayısı, model katsayısı) döner."""
    from sklearn.linear_model import LogisticRegression
    c=LogisticRegression(penalty=None,max_iter=1000).fit(np.c_[_logit(part.market),_logit(part.p)],part.y)
    return [float(c.intercept_[0]),float(c.coef_[0,0]),float(c.coef_[0,1])]

def harman_p(fit,market,p):
    a,bm,bp=fit
    return 1/(1+np.exp(-(a+bm*_logit(market)+bp*_logit(p))))

def harman_katsayilari(pred,odds):
    """Tüm oranlı NBA sezonlarıyla model başına harman katsayıları (tahmin komutu kullanır)."""
    data=pred[pred.lig=='NBA'].merge(odds[['mac_id','ev_ml','dep_ml']],on='mac_id',how='inner')
    data['market']=[no_vig(american_decimal(h),american_decimal(a))[0] for h,a in zip(data.ev_ml,data.dep_ml)]
    return {model:dict(katsayi=harman_fit(part),n=len(part),sezonlar=sorted(part.sezon.unique()))
            for model,part in data.groupby('model') if len(part)>=500}

def market_and_betting(pred,odds,min_bets=20):
    """Vig'siz kapanış olasılığıyla kıyas ve bahis simülasyonu.

    Sezon S'nin eşiği yalnız S'den önceki sezonların walk-forward tahminlerinde (oranı olan maçlar)
    en yüksek ROI'ye göre seçilir; en az `min_bets` bahis yoksa aday elenir.
    """
    data=pred[pred.lig=='NBA'].merge(odds[['mac_id','ev_ml','dep_ml']],on='mac_id',how='inner')
    if data.empty: return pd.DataFrame(),pd.DataFrame()
    data['ev_dec']=[american_decimal(v) for v in data.ev_ml]
    data['dep_dec']=[american_decimal(v) for v in data.dep_ml]
    data['market']=[no_vig(h,a)[0] for h,a in zip(data.ev_dec,data.dep_dec)]
    market_rows=[]
    for (season,model),part in data.groupby(['sezon','model']):
        market_rows.append(dict(sezon=season,model=model,n=len(part),**scores(part.y,part.p)))
        if model=='elo':
            market_rows.append(dict(sezon=season,model='piyasa_vigsiz',n=len(part),**scores(part.y,part.market)))
    # Harman: sezon S için piyasa ve model logitleri üzerine lojistik, yalnız S'den önceki oranlı sezonlarla.
    for model in HARMAN_MODELS:
        m=data[data.model==model]
        for season in sorted(m.sezon.unique())[1:]:
            history,test=m[m.sezon<season],m[m.sezon==season]
            fit=harman_fit(history)
            market_rows.append(dict(sezon=season,model=f'harman_{model}',n=len(test),
                **scores(test.y,harman_p(fit,test.market,test.p))))
    bets=[]
    seasons=sorted(data.sezon.unique())
    for model in BET_MODELS:
        m=data[data.model==model]
        for season in seasons:
            history=m[m.sezon<season]
            test=m[m.sezon==season]
            for method in ['fixed','kelly']:
                record=dict(sezon=season,model=model,method=method)
                if history.empty:
                    bets.append(dict(record,status='eşik seçilemedi: önceki oranlı sezon yok'));continue
                trials=[(t,simulate(history.p,history.y,history.ev_dec,history.dep_dec,t,method)) for t in THRESHOLDS]
                eligible=[(t,r) for t,r in trials if r['bets']>=min_bets and r['roi'] is not None]
                if not eligible:
                    bets.append(dict(record,status=f'eşik seçilemedi: <{min_bets} geçmiş bahis'));continue
                threshold,train_result=max(eligible,key=lambda item:item[1]['roi'])
                result=simulate(test.p,test.y,test.ev_dec,test.dep_dec,threshold,method)
                bets.append(dict(record,status='ok',threshold=threshold,train_roi=train_result['roi'],
                    train_bets=train_result['bets'],**result))
    return pd.DataFrame(market_rows),pd.DataFrame(bets)

def plot_calibration(pred):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if pred.empty:return
    for league,part in pred.groupby('lig'):
        fig,ax=plt.subplots(figsize=(7,5))
        ax.plot([0,1],[0,1],'k--')
        for model,p in part.groupby('model'):
            bins=np.minimum((p.p*10).astype(int),9)
            grouped=p.groupby(bins).agg(probability=('p','mean'),frequency=('y','mean'))
            ax.plot(grouped.probability,grouped.frequency,'o-',label=model)
        ax.set(xlabel='Tahmin olasılığı',ylabel='Gerçekleşen ev galibiyeti',title=f'{league} — walk-forward kalibrasyon')
        ax.legend();fig.tight_layout();fig.savefig(f'docs/kalibrasyon_{league}.png',dpi=140);plt.close(fig)
