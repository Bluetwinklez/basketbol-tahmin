"""Fixed-spec, separate-competition expanding-season evaluation; no tuning on test seasons."""
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss,log_loss
from bbtahmin import competition_model as model


def main():
    root=Path('docs/kanit/competitions');root.mkdir(parents=True,exist_ok=True)
    now=pd.Timestamp.now(tz='UTC');current=now.year if now.month>=7 else now.year-1
    summaries=[];files={}
    for code in model.CODES:
        g=model.load(code);p=model.walk_forward(code,g)
        p.to_csv(root/f'{code}_predictions.csv',index=False)
        for season,part in p.groupby('sezon'):
            summaries.append(dict(league=code,season=season,completed=int(season[:4])<current,
                n=len(part),correct=int(((part.p>=.5)==part.y).sum()),accuracy=float(((part.p>=.5)==part.y).mean()),
                home_baseline_accuracy=float(part.y.mean()),log_loss=float(log_loss(part.y,part.p,labels=[0,1])),
                brier=float(brier_score_loss(part.y,part.p)),margin_mae=float(np.mean(abs(part.margin-part.margin_prediction))),
                total_mae=float(np.mean(abs(part.total-part.total_prediction))),low_history_games=int(part.low_history.sum())))
        path=Path(f'data/competitions/{code}.parquet');files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    pd.DataFrame(summaries).to_csv(root/'summary.csv',index=False)
    (root/'manifest.json').write_text(json.dumps(dict(timestamp_utc=now.isoformat(),spec=model.SPEC,files=files,
        packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn']},
        method='Fixed Ridge alpha=10. Earlier seasons train; preceding season calibrates residuals; refit on both. Features update only after UTC day ends. No test-season tuning.',
        limitations='One completed test season per league; incomplete 2026-27 reported separately. VTB current-team cohort. No in-play support, odds, injuries, domestic-league games or cold-start-specific calibration. Retrospective results are not prospective accuracy.'),indent=2))
    print(pd.DataFrame(summaries).to_string(index=False))


if __name__=='__main__':main()
