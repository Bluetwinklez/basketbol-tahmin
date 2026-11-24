"""Historical TR2 candidates on the same monthly cohort; no model promotion."""
from pathlib import Path
import hashlib
from bbtahmin.football.data import load,write_json
from bbtahmin.football.challenger import compare,VARIANTS
from bbtahmin.football.evaluation_audit import simple_baselines
from evaluate_football_ensemble import reliability

if __name__=='__main__':
    frame=load(); frame=frame[frame.league=='TR2']
    r=compare(frame,'2019-20'); rows=r.pop('predictions')
    r['simple_baselines']=simple_baselines(rows,VARIANTS,frame.event_id.tolist())
    r['calibration']={}
    for v in VARIANTS:
        items=[x for x in rows if x['variant']==v]; c={}
        for k in ('home','draw','away'):
            c[k]=reliability([x['prediction']['probabilities'][k] for x in items],[x['result']['actual_outcome']==k for x in items])
        for line in ('1.5','2.5','3.5'):
            c['over_'+line]=reliability([x['prediction']['over'][line] for x in items],[x['result']['actual_home']+x['result']['actual_away']>float(line) for x in items])
        c['both_teams_score']=reliability([x['prediction']['both_teams_score'] for x in items],[min(x['result']['actual_home'],x['result']['actual_away'])>0 for x in items])
        r['calibration'][v]=c
    r['archive_sha256']=hashlib.sha256(Path('data/football/TR2_2019-20.json.gz').read_bytes()).hexdigest()
    r['note']+=' Historical TR2 community results only; no current support or official verification. No cross-league pooling. No earlier season history, so early months may be skipped.'
    write_json(Path('docs/kanit/football/TR2_2019-20_evaluation.json'),r)
    print(r['summaries'])
