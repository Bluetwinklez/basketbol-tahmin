"""Offline consistency audit of the actual run; does not retrain or access networks."""
import json
from pathlib import Path
import hashlib
from urllib.parse import urlparse
import numpy as np
import pandas as pd
from bbtahmin.backtest import scores

folder=Path('docs/kanit')
games=pd.read_parquet('data/maclar.parquet')
pred=pd.read_csv(folder/'tahminler.csv')
metrics=pd.read_csv(folder/'metrikler.csv')
cal=pd.read_csv(folder/'kalibrasyon.csv')
assert not pred.duplicated(['mac_id','model']).any()
assert np.isfinite(pred.p).all() and pred.p.between(0,1).all()
assert set(pred.model)=={'home','elo','mov_elo','logistic','hist_gradient_boosting'}
for row in metrics.itertuples():
    part=pred[(pred.lig==row.lig)&(pred.sezon==row.sezon)&(pred.model==row.model)]
    assert len(part)==row.n
    for key,value in scores(part.y,part.p).items():
        assert abs(value-getattr(row,key))<1e-10
    assert abs(np.mean(abs(part.margin-part.margin_prediction))-row.margin_mae)<1e-10
    assert cal[(cal.lig==row.lig)&(cal.sezon==row.sezon)&(cal.model==row.model)].n.sum()==row.n
parameters=json.loads((folder/'parametreler.json').read_text('utf8'))
for r in parameters:
    if 'model' not in r:continue
    group=games[games.lig==r['lig']]
    seasons=sorted(group.sezon.unique())
    validation=max(s for s in seasons if s<r['sezon'])
    train=[s for s in seasons if s<validation]
    assert train and validation<r['sezon']
    assert group.loc[group.sezon<r['sezon'],'tarih_utc'].max() < group.loc[group.sezon==r['sezon'],'tarih_utc'].min()
    r.update(training_seasons=train,validation_season=validation,
        training_rows=int(group.sezon.isin(train).sum()),
        validation_rows=int((group.sezon==validation).sum()),
        test_rows=int((group.sezon==r['sezon']).sum()))
    if r['model'] in ('elo','mov'):
        # EWMA is not used by either Elo baseline; omit the irrelevant cache setting.
        r.pop('ewma_alpha',None)
    if r['model'] in ('logistic','hist_gradient_boosting'):
        selected=r['candidates'][int(np.argmin(r['validation_losses']))]
        assert selected==r['parameter']
(folder/'parametreler.json').write_text(json.dumps(parameters,ensure_ascii=False,indent=2),'utf8')
collection=json.loads((folder/'toplama.json').read_text('utf8'))
for event in collection['http']:
    key=hashlib.sha256(event['url'].encode()).hexdigest()
    meta=Path('data/raw')/urlparse(event['url']).netloc/(key+'.json')
    if meta.exists(): event['status']=json.loads(meta.read_text('utf8'))['status']
(folder/'toplama.json').write_text(json.dumps(collection,ensure_ascii=False,indent=2),'utf8')
identity=json.loads((folder/'veri_kimligi.json').read_text('utf8'))
assert identity['sha256']==hashlib.sha256(Path('data/maclar.parquet').read_bytes()).hexdigest()
result=dict(passed=True,metric_rows=len(metrics),prediction_rows=len(pred),
    evaluated_games=int(pred.mac_id.nunique()),windows=int(len(metrics)/5),
    probability_bounds=True,unique_predictions=True,recomputed_metrics=True,
    calibration_counts=True,training_precedes_test=True,parameter_selection=True,dataset_hash_unchanged=True)
(folder/'dogrulama.json').write_text(json.dumps(result,indent=2),'utf8')
print(json.dumps(result,indent=2))
