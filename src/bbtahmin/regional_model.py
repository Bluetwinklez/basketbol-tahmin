"""Independent regional model using the established preceding-season policy.

Reuse learner mathematics, never Asian observations or fitted weights. Model
selection sees only the previous season; target-day outcomes are withheld.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from .asia_model import fit_fold, walk_forward as evaluate_folds
from .ozellik import build_features

CODES = ('ABA',)
NAMES = {'ABA': "ABA League (senior men)"}
SPEC = 'regional-prior-policy-v1'


def load(code):
    if code not in CODES:
        raise ValueError('Unsupported regional league')
    path = Path(f'data/competitions/{code}.parquet')
    if not path.exists():
        raise ValueError('Run python -m bbtahmin aba-topla first')
    g = pd.read_parquet(path).sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
    values = g[['ev_skor', 'dep_skor']].to_numpy(float)
    if (set(g.lig) != {code} or g.mac_id.duplicated().any() or (g.ev == g.dep).any()
            or not np.isfinite(values).all() or (values <= 0).any()
            or (g.ev_skor == g.dep_skor).any()):
        raise ValueError('Invalid or mixed regional archive')
    return g


def walk_forward(code):
    return evaluate_folds(code, load(code))


def predict(code, home, away, when):
    date = pd.Timestamp(when)
    if pd.isna(date) or date.tzinfo is None:
        raise ValueError('Timezone-aware fixture required')
    date = date.tz_convert('UTC'); cutoff = date.floor('D')
    g = load(code); g = g[g.tarih_utc < cutoff]
    catalog = json.loads(Path(f'data/competitions/{code}_teams.json').read_text())
    if home == away or any(t not in catalog for t in (home, away)):
        raise ValueError('Unknown or identical regional team')
    year = date.year if date.month >= 7 else date.year-1
    season = f'{year}-{str(year+1)[-2:]}'
    query = dict(mac_id=f'{code}_QUERY', lig=code, sezon=season, tarih_utc=date,
                 ev=home, dep=away, ev_skor=np.nan, dep_skor=np.nan, tarafsiz_saha=False)
    all_g = pd.concat([g, pd.DataFrame([query])], ignore_index=True)
    probs, scores, errors, info = fit_fold(all_g, build_features(all_g), season)
    index = all_g[all_g.sezon == season].mac_id.tolist().index(query['mac_id'])
    total = max(0., float(scores[1][index] + errors[1]['bias']))
    margin = float(np.clip(scores[0][index], -total, total))
    p = float(probs[info['selected']][index]); z = norm.ppf(.9)
    recent = g[g.tarih_utc >= cutoff-pd.Timedelta(days=400)]
    counts = {t: int(((recent.ev == t) | (recent.dep == t)).sum()) for t in (home, away)}
    return dict(lig=code, ev=home, dep=away, tarih_utc=date.isoformat(),
                model=SPEC+'/'+info['selected'], ev_kazanir=p,
                ev_skor=(total+margin)/2, dep_skor=(total-margin)/2, fark=margin, toplam=total,
                fark_80=[margin-z*errors[0]['sigma'], margin+z*errors[0]['sigma']],
                toplam_80=[max(0., total-z*errors[1]['sigma']), total+z*errors[1]['sigma']],
                tum_modeller={k: float(v[index]) for k, v in probs.items()},
                az_veri=[t for t, n in counts.items() if n < 5], recent_games=counts, uzatma=None,
                training_cutoff=cutoff.isoformat(), selection=info,
                calibration_regime_gap=info['calibration_season_gap'] > 1,
                dataset_sha256=hashlib.sha256(Path(f'data/competitions/{code}.parquet').read_bytes()).hexdigest(),
                experimental=True, note='Separate senior league, retrospectively collected results. Unverified same-day scores excluded. Nominal home court and historical publication times not independently verified. Intervals are not conditional guarantees.')
