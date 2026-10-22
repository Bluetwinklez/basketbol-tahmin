"""Re-score the four known failures without changing their original predictions."""
import hashlib,json
from pathlib import Path
import pandas as pd
from bbtahmin.prospective import score
from bbtahmin.quality import assess


def main():
 source=Path('docs/kanit/competitions/2026-10-22_reconstruction.json');old=json.loads(source.read_text());rows=[]
 for item in old['fixtures']:
  p=item['prediction'];code=p['lig']
  if code not in ('ECW','FEC'):continue
  g=pd.read_parquet(f'data/competitions/{code}.parquet')
  found=g[g.mac_id==item['fixture_id']]
  if len(found)!=1:raise ValueError('Unresolved historical result identity')
  r=found.iloc[0]
  rows.append(dict(match=item['match'],fixture_id=item['fixture_id'],historical_reconstruction=True,
    prospective_eligible=False,data_quality_at_cutoff=assess(p,g,now=p['tarih_utc']),
    **score(p,int(r.ev_skor),int(r.dep_skor))))
 root=Path('docs/kanit/governance');root.mkdir(parents=True,exist_ok=True)
 report=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),games=rows,
  correct=sum(r['winner_correct'] for r in rows),n=len(rows),
  interpretation='All four have sparse-history issues, including the correct pick. No loser-only filtering or retuning. Missing data is a hypothesis, not a proven cause. These post-tipoff reconstructions never enter prospective accuracy.')
 (root/'four_match_review.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
