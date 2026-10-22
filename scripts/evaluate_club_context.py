"""Measure available auxiliary history before allowing it into model training."""
import json
from pathlib import Path
import pandas as pd
from bbtahmin import club_context,competition_model


def main():
 root=Path('docs/kanit/context');root.mkdir(parents=True,exist_ok=True)
 context=club_context.load();rows=[]
 for code in competition_model.CODES:
  g=competition_model.load(code);f=club_context.features(g,context)
  observed=(f.aux_home_observed|f.aux_away_observed).astype(bool)
  for season in sorted(g.sezon.unique())[2:]:
   earlier=sorted(g.loc[g.sezon<season,'sezon'].unique());previous=earlier[-1]
   train=g.sezon<previous;val=g.sezon==previous;test=g.sezon==season
   a,b=int((observed&train).sum()),int((observed&val).sum())
   rows.append(dict(league=code,season=season,training_games_with_context=a,validation_games_with_context=b,
     test_games_with_context=int((observed&test).sum()),test_games=int(test.sum()),
     eligible_for_feature_experiment=a>=50 and b>=20))
 pd.DataFrame(rows).to_csv(root/'coverage.csv',index=False)
 (root/'admission.json').write_text(json.dumps(dict(score_features_enabled=False,
   reason='Insufficient earlier training/calibration coverage. No domestic-form accuracy improvement claimed.',
   source_coverage='Partial official club cohorts; no completeness guarantee. Captured now, not point-in-time publication snapshots.',
   thresholds=dict(minimum_covered_training_games=50,minimum_covered_validation_games=20)),indent=2))
 print(pd.DataFrame(rows).to_string(index=False))

if __name__=='__main__':main()
