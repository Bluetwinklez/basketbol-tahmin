"""Expose failures, paired differences, low-history strata and fixed coverage curves."""
import json,hashlib
from pathlib import Path
import pandas as pd
from bbtahmin import competition_model as base
from bbtahmin.evaluation import paired,metrics,equal_coverage


def main():
 root=Path('docs/kanit/protocol');root.mkdir(parents=True,exist_ok=True);results=[];strata=[];curves=[]
 for code in base.CODES:
  g=base.load(code);meta=g[['mac_id','tarih_utc']].copy();meta['day']=meta.tarih_utc.dt.strftime('%Y-%m-%d')
  rows=pd.read_csv(f'docs/kanit/winner/{code}_predictions.csv').merge(meta,on='mac_id',validate='many_to_one')
  for season,part in rows.groupby('sezon'):
   ref=part[part.variant=='score'].copy()
   for variant,candidate in part.groupby('variant'):
    if variant=='score':continue
    result=paired(ref,candidate);results.append(dict(league=code,season=season,variant=variant,**result))
    for curve in equal_coverage(ref,candidate):curves.append(dict(league=code,season=season,candidate=variant,**curve))
   for (variant,low),subset in part.assign(low_history=part.min_recent_games<5).groupby(['variant','low_history']):
    strata.append(dict(league=code,season=season,variant=variant,low_history=bool(low),**metrics(subset.y,subset.p)))
 (root/'paired.json').write_text(json.dumps(results,indent=2));pd.DataFrame(strata).to_csv(root/'strata.csv',index=False)
 pd.DataFrame(curves).to_csv(root/'coverage_curves.csv',index=False)
 files=[Path(f'docs/kanit/winner/{c}_predictions.csv') for c in base.CODES]
 (root/'manifest.json').write_text(json.dumps(dict(generated_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),
  files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
  runtime_policy='Default model retained. Every challenger and failed prior-season selection policy remains research-only.',
  limitations='Previously inspected historical seasons; no fresh holdout. Domestic form covers explicitly mapped Czech senior women only, retrospective availability unverified. Confidence-based filtering does not demonstrate higher all-game accuracy. Bootstrap intervals are exploratory, not multiple-testing corrected.'),indent=2))
 print('Paired comparisons:',len(results),'strata:',len(strata),'coverage rows:',len(curves))

if __name__=='__main__':main()
