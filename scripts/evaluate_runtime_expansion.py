"""Fixed-model, same-fixture KBL data ablation; never prospective evidence."""
import hashlib
import io
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from bbtahmin import asia_model
from bbtahmin.football.data import write_json

BASE = '0fafc2ef6345a19f447f36f2be046a9a26a41f29'


def summarize(rows):
    n = len(rows)
    p = np.array([r['prediction']['ev_kazanir'] for r in rows])
    y = np.array([r['actual_home'] > r['actual_away'] for r in rows])
    accuracy = float(np.mean((p >= .5) == y))
    z = 1.959963984540054
    centre = (accuracy+z*z/(2*n))/(1+z*z/n)
    radius = z*np.sqrt(accuracy*(1-accuracy)/n+z*z/(4*n*n))/(1+z*z/n)
    errors = [[r['prediction']['ev_skor']-r['actual_home'],
               r['prediction']['dep_skor']-r['actual_away']] for r in rows]
    errors = np.array(errors)
    bins=[]
    for lower in np.arange(0.,1.,.1):
        mask=(p>=lower)&(p<lower+.1)
        if mask.any():bins.append(dict(lower=float(lower),n=int(mask.sum()),mean_probability=float(p[mask].mean()),observed_home_rate=float(y[mask].mean())))
    return dict(games=n, winner_accuracy=accuracy, accuracy_wilson_95=[centre-radius, centre+radius],
                brier=float(np.mean((p-y)**2)),
                calibration_bins=bins,
                margin_in_80=float(np.mean([r['prediction']['fark_80'][0] <= r['actual_home']-r['actual_away'] <= r['prediction']['fark_80'][1] for r in rows])),
                log_loss=float(-np.mean(y*np.log(np.clip(p,1e-15,1))+(1-y)*np.log(np.clip(1-p,1e-15,1)))),
                team_score_mae=float(np.abs(errors).mean()),
                total_mae=float(np.abs(errors.sum(axis=1)).mean()),
                margin_mae=float(np.abs(errors[:,0]-errors[:,1]).mean()),
                total_in_80=float(np.mean([r['prediction']['toplam_80'][0] <= r['actual_home']+r['actual_away'] <= r['prediction']['toplam_80'][1] for r in rows])))


def main():
    raw = subprocess.check_output(['git','show',BASE+':data/asia/KBL.parquet'])
    old = pd.read_parquet(io.BytesIO(raw))
    current = asia_model.load('KBL')
    targets = current[~current.mac_id.isin(old.mac_id)].sort_values(['tarih_utc','mac_id'])
    if targets.empty:
        raise ValueError('No new KBL fixture cohort')
    records = {}
    original_load = asia_model.load
    try:
        for label, games, digest in [('old_data',old,hashlib.sha256(raw).hexdigest()),
                                     ('expanded_data',current,hashlib.sha256(Path('data/asia/KBL.parquet').read_bytes()).hexdigest())]:
            asia_model.load = lambda code, expanded_history=False, games=games: games.copy()
            rows = []
            with threadpool_limits(limits=1):
                for fixture in targets.itertuples():
                    prediction = asia_model.predict('KBL',fixture.ev,fixture.dep,fixture.tarih_utc)
                    # predict normally hashes its on-disk input. This ablation
                    # substitutes an explicit in-memory snapshot, so hash that source.
                    prediction['dataset_sha256'] = digest
                    rows.append(dict(event_id=fixture.mac_id, start_utc=fixture.tarih_utc.isoformat(),
                                     prediction=prediction, actual_home=int(fixture.ev_skor),actual_away=int(fixture.dep_skor)))
            records[label] = dict(summary=summarize(rows), rows=rows)
    finally:
        asia_model.load = original_load
    write_json('docs/kanit/delivery_audit/kbl_data_ablation.json', dict(
        league='KBL', base_revision=BASE, model=asia_model.SPEC,
        source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        model_source_sha256=hashlib.sha256(Path(asia_model.__file__).read_bytes()).hexdigest(), same_fixture_ids=targets.mac_id.tolist(),
        first_start_utc=targets.tarih_utc.min().isoformat(),last_start_utc=targets.tarih_utc.max().isoformat(),
        skipped=0, experiments=records, defaults_changed=False,
        note='Exploratory post-result data ablation on all newly imported KBL finals, selected by archive membership, not outcomes. Identical fixed previous-season policy and whole-UTC-day withholding. No target tuning or calibration changes. Historical publication availability is unknown. Seven matches cannot establish general improvement; not prospective success.'))
    print({name:value['summary'] for name,value in records.items()})


if __name__ == '__main__':
    main()
