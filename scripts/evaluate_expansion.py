"""Compare old/new history on identical completed-season games.

Run from repository root: PYTHONPATH=src python scripts/evaluate_expansion.py
    --baseline /path/to/original/maclar.parquet
This isolates the score model and excludes retrospective player-absence labels.
It does not overwrite the main seven-model benchmark or claim betting returns.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, mean_absolute_error
from threadpoolctl import threadpool_limits

from bbtahmin.model import regression
from bbtahmin.ozellik import FEATURES, build_features


def evaluate(baseline, expanded, output):
    baseline = baseline[(baseline.ev_skor > 0) & (baseline.dep_skor > 0)]
    expanded = expanded[(expanded.ev_skor > 0) & (expanded.dep_skor > 0)]
    parameters = json.loads(Path('docs/kanit/parametreler.json').read_text('utf8'))
    rows = []
    for league in sorted(baseline.lig.unique()):
        original = baseline[baseline.lig == league]
        full = expanded[expanded.lig == league]
        targets = sorted(original.sezon.unique())
        current = pd.Timestamp.now(tz='UTC')
        current_year = current.year if current.month >= 7 else current.year - 1
        targets = [s for s in targets if current_year-5 <= int(s[:4]) < current_year]
        for season in targets:
            test_ids = set(original.loc[original.sezon == season, 'mac_id']) & set(full.mac_id)
            if not test_ids:
                continue
            records = [r for r in parameters if r.get('lig') == league and r.get('sezon') == season]
            mov = next((r for r in records if r.get('model') == 'mov'), None)
            ewma = next((r for r in records if r.get('model') == 'ewma'), {})
            if mov is None:
                continue
            for variant, data in [('original', original), ('expanded_full', full), ('expanded_adaptive', full)]:
                g = data[data.sezon <= season].sort_values(['tarih_utc', 'mac_id']).reset_index(drop=True)
                seasons = sorted(g.sezon.unique())
                prior = seasons[seasons.index(season)-1]
                train = (g.sezon < prior).to_numpy()
                val = (g.sezon == prior).to_numpy()
                test = g.mac_id.isin(test_ids).to_numpy()
                x = build_features(g, k=mov['k'], advantage=mov['home_advantage'], shrink=mov['shrink'],
                                   alpha=ewma.get('alpha', .2), mov=True)
                margin = (g.ev_skor-g.dep_skor).to_numpy(dtype=float)
                total = (g.ev_skor+g.dep_skor).to_numpy(dtype=float)
                adaptive = variant == 'expanded_adaptive'
                options = dict(seasons=g.sezon, objective='log_loss') if adaptive else {}
                pm, detail = regression(x, margin, train, val, test, FEATURES, **options)
                pt, total_detail = regression(x, total, train, val, test, FEATURES,
                                              **(dict(seasons=g.sezon) if adaptive else {}))
                pt += total_detail['residual_mean']
                probability = norm.cdf(pm/max(detail['residual_sigma'], 1e-6))
                truth = (margin[test] > 0).astype(int)
                rows.append(dict(lig=league, sezon=season, variant=variant, n=len(truth),
                                 log_loss=log_loss(truth, np.clip(probability, 1e-6, 1-1e-6), labels=[0,1]),
                                 brier=brier_score_loss(truth, probability),
                                 accuracy=accuracy_score(truth, probability >= .5),
                                 margin_mae=mean_absolute_error(margin[test], pm),
                                 total_mae=mean_absolute_error(total[test], pt),
                                 history_window=detail['history_window'],
                                 training_rows=detail['training_rows']))
            print(f'{league} {season}: {len(test_ids)} identical test games', flush=True)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows)
    result.to_csv(output/'folds.csv', index=False)
    totals = []
    for (league, variant), part in result.groupby(['lig','variant']):
        totals.append(dict(lig=league, variant=variant, n=int(part.n.sum()),
                           **{key: float(np.average(part[key], weights=part.n)) for key in
                              ['log_loss','brier','accuracy','margin_mae','total_mae']}))
    pd.DataFrame(totals).to_csv(output/'summary.csv', index=False)
    metadata = dict(baseline_rows=len(baseline), expanded_rows=len(expanded),
                    timestamp=pd.Timestamp.now(tz='UTC').isoformat(),
                    test='Common games in the last five completed seasons; season-by-season chronological holdout.',
                    exclusions='Retrospective player-absence labels and new detailed box scores are excluded.',
                    parameters='Previously recorded fold-specific Elo/EWMA parameters, identical across variants.',
                    adaptive='Ridge alpha and 3/5/10/all prior training seasons selected on preceding validation season.',
                    limitations='Point estimates; no statistical superiority or live performance claim.')
    (output/'method.json').write_text(json.dumps(metadata, indent=2), 'utf8')
    print(pd.DataFrame(totals).to_string(index=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--expanded', default='data/maclar.parquet')
    parser.add_argument('--output', default='docs/kanit/data_expansion_model')
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        evaluate(pd.read_parquet(args.baseline), pd.read_parquet(args.expanded), args.output)
