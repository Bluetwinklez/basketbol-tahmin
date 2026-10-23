"""Fixed candidates, earlier-season selection, same test fixtures; no four-match tuning."""
import json,hashlib,importlib.metadata
from pathlib import Path
import pandas as pd
from bbtahmin import competition_model as base,winner_model as model


def main():
 root=Path('docs/kanit/winner');root.mkdir(parents=True,exist_ok=True)
 outputs={}
 def inputs():
  paths=[Path(f'data/competitions/{c}.parquet') for c in [*base.CODES,'ELW']]+[Path('data/competitions/ECW_early.parquet')]
  paths += [p for p in sorted(Path('data/domestic').glob('*.parquet')) if not p.name.endswith('_fixtures.parquet')]
  return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 from bbtahmin.prospective import fingerprint
 before=inputs();code_before=fingerprint()
 summaries=[];selections=[];now=pd.Timestamp.now(tz='UTC');year=now.year if now.month>=7 else now.year-1
 for code in base.CODES:
  records,choices=model.walk_forward(code);selections+=choices
  outputs[code]=records
  for (season,variant),p in records.groupby(['sezon','variant']):
   selected=p[p.eligible]
   summaries.append(dict(league=code,season=season,completed=int(season[:4])<year,variant=variant,n=len(p),
    **model._metrics(p.y.to_numpy(),p.p.to_numpy()),selected_games=len(selected),coverage=len(selected)/len(p),
    selected_accuracy=float(((selected.p>=.5)==selected.y).mean()) if len(selected) else None))
 if before!=inputs() or code_before!=fingerprint():raise ValueError('Evaluation inputs/code changed during run; rerun on a stable snapshot')
 for code,records in outputs.items():records.to_csv(root/f'{code}_predictions.csv',index=False)
 pd.DataFrame(summaries).to_csv(root/'summary.csv',index=False)
 (root/'selections.json').write_text(json.dumps(selections,indent=2))
 paths=[Path(f'data/competitions/{c}.parquet') for c in [*base.CODES,'ELW']]+[Path('data/competitions/ECW_early.parquet')]
 (root/'manifest.json').write_text(json.dumps(dict(spec=model.SPEC,generated_at_utc=now.isoformat(),
  packages={n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn']},
  files=before,source_code_sha256=code_before,
  limitations='Historical exploratory reuse of already inspected seasons, not a new untouched holdout. Prior season uses disjoint UTC-day halves for residual calibration and candidate selection. Current-season rows include the four known matches; never use their outcomes to choose parameters. All variants reported, including failures. Eligibility is coverage filtering, not model accuracy improvement.'),indent=2))
 print(pd.DataFrame(summaries).to_string(index=False))

if __name__=='__main__':main()
