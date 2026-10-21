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

def fit_predict(kind,x,y,train,validation,test):
    candidates=[.1,1.,10.] if kind=='logistic' else [
        dict(max_leaf_nodes=7,l2_regularization=1.,max_iter=50),
        dict(max_leaf_nodes=15,l2_regularization=10.,max_iter=100),
        dict(max_leaf_nodes=7,l2_regularization=10.,max_iter=100),
        dict(max_leaf_nodes=15,l2_regularization=1.,max_iter=50)]
    losses=[]
    for value in candidates:
        model=estimator(kind,value).fit(x.loc[train,FEATURES],y[train])
        p=model.predict_proba(x.loc[validation,FEATURES])[:,1]
        losses.append(log_loss(y[validation],p,labels=[0,1]))
    value=candidates[int(np.argmin(losses))]
    inner=estimator(kind,value).fit(x.loc[train,FEATURES],y[train])
    pv=inner.predict_proba(x.loc[validation,FEATURES])[:,1]
    logit=lambda p: np.log(np.clip(p,1e-6,1-1e-6)/np.clip(1-p,1e-6,1-1e-6)).reshape(-1,1)
    # Unpenalized Platt: both slope and intercept estimated, no hand-set regularizer.
    calibrator=LogisticRegression(penalty=None,max_iter=1000).fit(logit(pv),y[validation])
    final=estimator(kind,value).fit(x.loc[train|validation,FEATURES],y[train|validation])
    raw=final.predict_proba(x.loc[test,FEATURES])[:,1]
    return calibrator.predict_proba(logit(raw))[:,1],dict(parameter=value,
        candidates=candidates,validation_losses=losses,
        calibration='Unpenalized Platt on prior-season out-of-sample predictions',
        calibration_coefficient=float(calibrator.coef_[0,0]),calibration_intercept=float(calibrator.intercept_[0]))

def regression(x,target,train,validation,test):
    values=[.1,10.,100.]
    errors=[]
    for value in values:
        m=make_pipeline(StandardScaler(),Ridge(alpha=value)).fit(x.loc[train,FEATURES],target[train])
        errors.append(float(np.mean(np.abs(target[validation]-m.predict(x.loc[validation,FEATURES])))))
    value=values[int(np.argmin(errors))]
    final=make_pipeline(StandardScaler(),Ridge(alpha=value)).fit(x.loc[train|validation,FEATURES],target[train|validation])
    prediction=final.predict(x.loc[test,FEATURES])
    residual=target[validation]-make_pipeline(StandardScaler(),Ridge(alpha=value)).fit(
        x.loc[train,FEATURES],target[train]).predict(x.loc[validation,FEATURES])
    from scipy.stats import normaltest,skew,kurtosis
    return prediction,dict(alpha=value,candidates=values,validation_mae=errors,residual_sigma=float(np.std(residual,ddof=1)),
        residual_mean=float(np.mean(residual)),
        residual_normality_p=float(normaltest(residual).pvalue) if len(residual)>=8 else None,
        residual_skew=float(skew(residual)),residual_excess_kurtosis=float(kurtosis(residual)))
