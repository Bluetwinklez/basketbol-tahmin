"""Compare the fixed baseline with an earlier-season-gated monthly refit policy."""
import hashlib,json,importlib.metadata
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss,brier_score_loss
from bbtahmin import competition_model,adaptive


def main():
 root=Path('docs/kanit/adaptive');root.mkdir(parents=True,exist_ok=True)
 summaries=[];selections=[];now=pd.Timestamp.now(tz='UTC');year=now.year if now.month>=7 else now.year-1
 for code in competition_model.CODES:
  g=competition_model.load(code);baseline=competition_model.walk_forward(code,g);new,choices=adaptive.walk_forward(code,g)
  assert baseline.mac_id.tolist()==new.mac_id.tolist()
  selections+=choices
  for name,p in [('fixed',baseline),('prior_gated_monthly',new)]:
   p.to_csv(root/f'{code}_{name}.csv',index=False)
   for season,part in p.groupby('sezon'):
    summaries.append(dict(league=code,season=season,completed=int(season[:4])<year,variant=name,n=len(part),
      correct=int(((part.p>=.5)==part.y).sum()),accuracy=float(((part.p>=.5)==part.y).mean()),
      log_loss=float(log_loss(part.y,part.p,labels=[0,1])),brier=float(brier_score_loss(part.y,part.p)),
      margin_mae=float(np.mean(abs(part.margin-part.margin_prediction))),total_mae=float(np.mean(abs(part.total-part.total_prediction)))))
 pd.DataFrame(summaries).to_csv(root/'summary.csv',index=False)
 (root/'selections.json').write_text(json.dumps(selections,indent=2))
 paths=[Path(f'data/competitions/{c}.parquet') for c in competition_model.CODES]
 (root/'manifest.json').write_text(json.dumps(dict(spec=adaptive.SPEC,generated_at_utc=now.isoformat(),
  files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
  packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn']},
  method='Prior-season-only selection; candidate expands training at UTC month boundaries, never with current-month outcomes. Same evaluation rows. Existing historical research seasons reused; exploratory, not an untouched holdout.'),indent=2))
 print(pd.DataFrame(summaries).to_string(index=False))

if __name__=='__main__':main()
