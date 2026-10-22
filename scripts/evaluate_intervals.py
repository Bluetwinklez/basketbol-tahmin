"""Same-fixture normal versus prior-season empirical residual intervals; no test tuning."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from bbtahmin import competition_model as model
from bbtahmin.ozellik import build_features


def score(y,lo,hi,alpha=.2):
 if (hi<lo).any():raise ValueError('Reversed interval')
 return dict(n=len(y),coverage=float(np.mean((lo<=y)&(y<=hi))),mean_width=float(np.mean(hi-lo)),
    interval_score=float(np.mean(hi-lo+2/alpha*(lo-y)*(y<lo)+2/alpha*(y-hi)*(y>hi))))


def main():
 root=Path('docs/kanit/intervals');root.mkdir(parents=True,exist_ok=True);rows=[]
 for code in model.CODES:
  g=model.load(code);x=build_features(g);seasons=sorted(g.sezon.unique())
  for i,season in enumerate(seasons):
   if i<2:continue
   train=(g.sezon<seasons[i-1]).to_numpy();val=(g.sezon==seasons[i-1]).to_numpy();test=(g.sezon==season).to_numpy()
   values,errors=model.fit(x,g,train,val,test)
   targets=[(g.ev_skor-g.dep_skor).to_numpy(float),(g.ev_skor+g.dep_skor).to_numpy(float)]
   for j,label in enumerate(['margin','total']):
    center=values[j];error=errors[j];qlo,qhi=error['residual_quantiles_80']
    empirical=(center+qlo,center+qhi)
    corrected=center+(error['bias'] if j else 0.)
    normal=(corrected-norm.ppf(.9)*error['sigma'],corrected+norm.ppf(.9)*error['sigma'])
    for method,(lo,hi) in [('normal',normal),('empirical',empirical)]:
     if j:lo=np.maximum(lo,0.)
     rows.append(dict(league=code,season=season,target=label,method=method,**score(targets[j][test],lo,hi)))
 pd.DataFrame(rows).to_csv(root/'summary.csv',index=False)
 (root/'method.json').write_text(json.dumps(dict(method='Quantiles 0.1 / 0.9 from preceding calibration season residuals, same training/refit and test fixtures as baseline.',
  runtime='Normal intervals unchanged; empirical intervals explicitly research-only.',limitations='Previously inspected test seasons, not fresh evidence. Marginal coverage is not per-team coverage; season/roster shifts can invalidate nominal coverage.'),indent=2))
 print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':main()
