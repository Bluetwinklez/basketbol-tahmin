"""Compare a fixed prior-season selection policy with its unchanged baselines."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from threadpoolctl import threadpool_limits

from bbtahmin import regional_model
from bbtahmin.evaluation import metrics
from bbtahmin.prospective import fingerprint


def main():
    root = Path('docs/kanit/regional_models'); root.mkdir(parents=True, exist_ok=True)
    now = pd.Timestamp.now(tz='UTC'); active = now.year if now.month >= 7 else now.year-1
    source = fingerprint(); summaries, folds, hashes = [], {}, {}
    for code in regional_model.CODES:
        path = Path(f'data/competitions/{code}.parquet')
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with threadpool_limits(limits=1):
            rows, policies, skipped = regional_model.walk_forward(code)
        folds[code] = dict(policies=policies, skipped=skipped)
        rows.to_csv(root/f'{code}_predictions.csv.gz', index=False, compression='gzip')
        for label, subset in [('completed', rows[rows.sezon.str[:4].astype(int) < active]),
                              ('current_partial', rows[rows.sezon.str[:4].astype(int) == active])]:
            for variant, group in subset.groupby('variant'):
                result = metrics(group.y, group.p)
                summaries.append(dict(league=code, cohort=label, variant=variant,
                    correct=int(((group.p >= .5) == group.y).sum()), **result,
                    home_baseline_accuracy=float(group.y.mean()), score_mae=float(group.score_mae.mean()),
                    total_mae=float(group.total_absolute_error.mean()), margin_mae=float(group.margin_absolute_error.mean()),
                    total_80_coverage=float(group.total_in_80.mean()), selected_games=int(group.eligible.sum())))
    if source != fingerprint() or any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in hashes.items()):
        raise ValueError('Source/data changed during evaluation; rerun')
    pd.DataFrame(summaries).to_csv(root/'summary.csv', index=False)
    (root/'folds.json').write_text(json.dumps(folds, indent=2))
    (root/'manifest.json').write_text(json.dumps(dict(spec=regional_model.SPEC,
        generated_at_utc=now.isoformat(), source_code_sha256=source, datasets=hashes,
        method='Earlier seasons train; previous season first UTC-day half calibrates score scale; second half selects lowest log loss among score/logistic/Elo/equal ensemble. Refit on all prior seasons. Same-day outcomes withheld. All variants use identical target games.',
        limitations='Retrospective collection; missing/undated fixtures excluded; nominal home court; unverified historical publication times. Completed and partial seasons separate. No prospective success claim or conditional interval guarantee.'), indent=2))
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__ == '__main__':
    main()
