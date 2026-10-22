"""Chronological second-stage calibration of archived out-of-sample scores.

No production change: every target season is transformed using earlier seasons
only, with the unmodified score probabilities scored on the same fixtures.
"""
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, brier_score_loss, accuracy_score


def evaluate(predictions):
    required = ['lig', 'sezon', 'mac_id', 'y', 'p']
    source = predictions.loc[predictions.model == 'skor', required].copy()
    if (source.duplicated(['lig', 'sezon', 'mac_id']).any()
            or not source.p.between(0, 1).all() or not source.y.isin([0, 1]).all()
            or source[required].isna().any().any()):
        raise ValueError('Invalid or duplicate score prediction evidence')
    rows, transformed = [], []
    for league, group in source.groupby('lig'):
        for season in sorted(group.sezon.unique()):
            train = group[group.sezon < season]
            test = group[group.sezon == season]
            if train.y.nunique() < 2:
                continue  # warmup season has no earlier out-of-sample evidence
            x = logit(np.clip(train.p.to_numpy(), 1e-6, 1-1e-6)).reshape(-1, 1)
            xt = logit(np.clip(test.p.to_numpy(), 1e-6, 1-1e-6)).reshape(-1, 1)
            calibrator = LogisticRegression(penalty=None, max_iter=1000).fit(x, train.y)
            for name, p in [('score_baseline', test.p.to_numpy()),
                            ('prior_seasons_platt', calibrator.predict_proba(xt)[:, 1])]:
                rows.append(dict(lig=league, sezon=season, model=name, n=len(test),
                    calibration_games=len(train), calibration_last_season=train.sezon.max(),
                    log_loss=float(log_loss(test.y, p, labels=[0, 1])),
                    brier=float(brier_score_loss(test.y, p)),
                    accuracy=float(accuracy_score(test.y, p >= .5)),
                    slope=float(calibrator.coef_[0, 0]), intercept=float(calibrator.intercept_[0])))
                transformed.extend(dict(lig=league, sezon=season, mac_id=r.mac_id,
                    model=name, y=int(r.y), p=float(p[i])) for i, r in enumerate(test.itertuples()))
    return pd.DataFrame(rows), pd.DataFrame(transformed)


def main():
    path = Path('docs/kanit/pregame_verified/tahminler.csv.gz')
    source = pd.read_csv(path)
    now = pd.Timestamp.now(tz='UTC'); year = now.year if now.month >= 7 else now.year-1
    source = source[source.sezon.str[:4].astype(int) < year]
    folds, predictions = evaluate(source)
    summary = []
    for (league, model), g in predictions.groupby(['lig', 'model']):
        summary.append(dict(lig=league, model=model, n=len(g),
            log_loss=float(log_loss(g.y, g.p, labels=[0, 1])),
            brier=float(brier_score_loss(g.y, g.p)),
            accuracy=float(accuracy_score(g.y, g.p >= .5))))
    output = Path('docs/kanit/calibration_research'); output.mkdir(parents=True, exist_ok=True)
    folds.to_csv(output/'folds.csv', index=False)
    result = pd.DataFrame(summary); result.to_csv(output/'summary.csv', index=False)
    (output/'method.json').write_text(json.dumps(dict(
        experimental=True, activated=False, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        python=sys.version,packages={name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','scikit-learn']},
        method='Unpenalized Platt on all strictly earlier completed-season OOS score probabilities.',
        warmup='2021-22 excluded from both candidate and baseline; partial current season excluded.',
        limitations='Exploratory comparison on existing research seasons; not a new untouched holdout.',
        timestamp=now.isoformat()), indent=2))
    print(result.to_string(index=False))


if __name__ == '__main__':
    main()
