"""Diagnostic drift and forecast summaries; never automatic retraining on two losses."""
import numpy as np
import pandas as pd
from .evaluation import metrics


def distribution_shift(reference,current,columns):
    rows=[]
    for column in columns:
        a=pd.to_numeric(reference[column],errors='coerce');b=pd.to_numeric(current[column],errors='coerce')
        finite=a[np.isfinite(a)];recent=b[np.isfinite(b)]
        scale=float(finite.std(ddof=1)) if len(finite)>1 else 0.
        shift=float((recent.mean()-finite.mean())/scale) if scale>0 and len(recent) else None
        rows.append(dict(feature=column,reference_n=len(finite),current_n=len(recent),
            current_missing_fraction=float(1-len(recent)/len(b)) if len(b) else None,
            standardized_mean_shift=shift,diagnostic_alert=bool(shift is not None and abs(shift)>2)))
    return dict(features=rows,automatic_retraining=False,
        note='Two-standard-deviation mean shifts are diagnostic alerts, not validated performance alarms. Review sample sizes and data-source changes.')


def reliability(y,p,bins=5):
    y=np.asarray(y);p=np.asarray(p);rows=[]
    for lo in np.linspace(0,1,bins+1)[:-1]:
        hi=lo+1/bins;mask=(p>=lo)&((p<hi) if hi<1-1e-9 else p<=1)
        if mask.any():rows.append(dict(lower=float(lo),upper=float(hi),n=int(mask.sum()),
            mean_predicted=float(p[mask].mean()),observed_home_win_rate=float(y[mask].mean())))
    return dict(metrics=metrics(y,p),bins=rows,note='Small reliability bins are noisy; do not interpret them as per-match accuracy guarantees.')
