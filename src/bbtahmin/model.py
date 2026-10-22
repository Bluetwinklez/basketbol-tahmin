import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression,Ridge
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss
from .ozellik import FEATURES

def estimator(kind,value):
    if kind=='logistic':
        return make_pipeline(StandardScaler(),LogisticRegression(C=value,max_iter=1000,random_state=42))
    return HistGradientBoostingClassifier(**value,early_stopping=False,random_state=42)

def fit_predict(kind,x,y,train,validation,test,cols=None):
    cols=cols or FEATURES
    candidates=[.1,1.,10.] if kind=='logistic' else [
        dict(max_leaf_nodes=7,l2_regularization=1.,max_iter=50),
        dict(max_leaf_nodes=15,l2_regularization=10.,max_iter=100),
        dict(max_leaf_nodes=7,l2_regularization=10.,max_iter=100),
        dict(max_leaf_nodes=15,l2_regularization=1.,max_iter=50)]
    losses=[]
    for value in candidates:
        model=estimator(kind,value).fit(x.loc[train,cols],y[train])
        p=model.predict_proba(x.loc[validation,cols])[:,1]
        losses.append(log_loss(y[validation],p,labels=[0,1]))
    value=candidates[int(np.argmin(losses))]
    inner=estimator(kind,value).fit(x.loc[train,cols],y[train])
    pv=inner.predict_proba(x.loc[validation,cols])[:,1]
    logit=lambda p: np.log(np.clip(p,1e-6,1-1e-6)/np.clip(1-p,1e-6,1-1e-6)).reshape(-1,1)
    # Unpenalized Platt: both slope and intercept estimated, no hand-set regularizer.
    calibrator=LogisticRegression(penalty=None,max_iter=1000).fit(logit(pv),y[validation])
    final=estimator(kind,value).fit(x.loc[train|validation,cols],y[train|validation])
    raw=final.predict_proba(x.loc[test,cols])[:,1]
    return calibrator.predict_proba(logit(raw))[:,1],dict(parameter=value,
        candidates=candidates,validation_losses=losses,
        calibration='Unpenalized Platt on prior-season out-of-sample predictions',
        calibration_coefficient=float(calibrator.coef_[0,0]),calibration_intercept=float(calibrator.intercept_[0]))

def regression(x,target,train,validation,test,cols=None,seasons=None,objective='mae'):
    cols=cols or FEATURES
    values=[.1,10.,100.]
    # More history is not automatically more useful: rules, pace and rosters
    # change. Select the history length exclusively on the prior-season holdout.
    windows=[None] if seasons is None else [None,3,5,10]
    errors=[]; trials=[]
    for window in windows:
        mask=np.asarray(train,dtype=bool).copy()
        if window is not None:
            available=sorted(set(np.asarray(seasons)[mask]))
            mask &= np.isin(seasons,available[-window:])
        for value in values:
            m=make_pipeline(StandardScaler(),Ridge(alpha=value)).fit(x.loc[mask,cols],target[mask])
            pv=m.predict(x.loc[validation,cols])
            residual=target[validation]-pv
            if objective=='log_loss':
                from scipy.stats import norm
                p=norm.cdf(pv/max(float(np.std(residual,ddof=1)),1e-6))
                error=float(log_loss((target[validation]>0).astype(int),np.clip(p,1e-6,1-1e-6),labels=[0,1]))
            else:
                error=float(np.mean(np.abs(residual)))
            errors.append(error);trials.append((value,window,mask))
    index=int(np.argmin(errors));value,window,selected_train=trials[index]
    final=make_pipeline(StandardScaler(),Ridge(alpha=value)).fit(x.loc[selected_train|validation,cols],target[selected_train|validation])
    prediction=final.predict(x.loc[test,cols])
    residual=target[validation]-make_pipeline(StandardScaler(),Ridge(alpha=value)).fit(
        x.loc[selected_train,cols],target[selected_train]).predict(x.loc[validation,cols])
    from scipy.stats import normaltest,skew,kurtosis
    return prediction,dict(alpha=value,candidates=values,validation_mae=errors if objective=='mae' else None,
        history_window=window,validation_objective=objective,validation_losses=errors,
        history_candidates=[dict(alpha=a,window=w) for a,w,_ in trials],
        training_rows=int(selected_train.sum()),residual_sigma=float(np.std(residual,ddof=1)),
        residual_mean=float(np.mean(residual)),
        residual_normality_p=float(normaltest(residual).pvalue) if len(residual)>=8 else None,
        residual_skew=float(skew(residual)),residual_excess_kurtosis=float(kurtosis(residual)))
