"""Same-model football data ablation on every newly available licensed final."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from bbtahmin.experiment_metrics import paired
from bbtahmin.football.data import load,write_json
from bbtahmin.football.model import GoalModel,metrics,score


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='docs/kanit/improvement/football-data-ablation')
    args=parser.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    old=load(include_licensed=False);expanded=load()
    prior_ids=set(old.loc[old.status=='final','event_id'])
    targets=expanded.loc[(expanded.status=='final')&(~expanded.event_id.isin(prior_ids))].sort_values(['date','event_id'])
    inputs={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('data/football').rglob('*.json.gz')}
    protocol=dict(spec='licensed-football-data-only-v1',model='football-poisson-v1',
                  settings=dict(half_life=180.,shrinkage=8.,window_days=1095),target_ids=targets.event_id.tolist(),input_hashes=inputs,
                  model_source_sha256=hashlib.sha256(Path('src/bbtahmin/football/model.py').read_bytes()).hexdigest(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  cutoff='Whole target day withheld. Same fixed model; only verified result/date supplement differs.',
                  evidence_kind='exploratory_retrospective',production_default_changed=False)
    path=root/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Changed ablation inputs; use a new output version')
    if not path.exists():write_json(path,protocol)
    rows=[];skipped=[];models={}
    for game in targets.to_dict('records'):
        key=(game['league'],game['date'])
        try:
            if key not in models:models[key]={v:GoalModel(frame,game['league'],game['date']) for v,frame in (('old_data',old),('expanded_data',expanded))}
            pair=[]
            for name,model in models[key].items():
                prediction=model.predict(game['home'],game['away']);result=score(prediction,int(game['home_goals']),int(game['away_goals']))
                pair.append(dict(event_id=game['event_id'],league=game['league'],day=game['date'],variant=name,
                                 y=('home','draw','away').index(result['actual_outcome']),
                                 p=[prediction['probabilities'][k] for k in ('home','draw','away')],prediction=prediction,result=result))
            rows.extend(pair)
        except ValueError as exc:skipped.append(dict(event_id=game['event_id'],reason=str(exc)))
    summaries=[]
    for league in sorted({r['league'] for r in rows}):
        group=[r for r in rows if r['league']==league]
        summaries.append(dict(league=league,variants={v:metrics([r['result'] for r in group if r['variant']==v]) for v in ('old_data','expanded_data')},
                              paired=paired(group,'old_data','expanded_data')))
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in inputs.items()):raise ValueError('Input changed during ablation')
    write_json(root/'summary.json',dict(protocol=protocol,summaries=summaries,skipped=skipped,
                scored_fixture_count=len(rows)//2,
                note='All newly available licensed finals selected by archive membership, never by outcomes. Historical publication times unknown; verified training date corrections are also part of the data change. Retrospective replay is not forward performance.'))
    (root/'rows.json.gz').write_bytes(gzip.compress(json.dumps(rows,ensure_ascii=False,allow_nan=False).encode(),mtime=0))
    print(json.dumps(dict(games=len(rows)//2,skipped=len(skipped),leagues=len(summaries))))


if __name__=='__main__':main()
