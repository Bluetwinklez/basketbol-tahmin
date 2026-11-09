"""Recompute comparator evidence from saved predictions without refitting models."""
import gzip
import hashlib
import json
from pathlib import Path
from bbtahmin.football.data import load, write_json
from bbtahmin.football.challenger import VARIANTS
from bbtahmin.football.evaluation_audit import simple_baselines
from bbtahmin.football.model import metrics
from evaluate_football_ensemble import reliability


def main():
    source=Path('docs/kanit/requested_football/paired_results.json.gz')
    raw=source.read_bytes(); rows=json.loads(gzip.decompress(raw))
    frame=load(); target=frame[(frame.league=='BR2') & (frame.season=='2024') & (frame.status=='final')]
    report=dict(source_file=str(source),source_sha256=hashlib.sha256(raw).hexdigest(),
                simple_baselines=simple_baselines(rows,VARIANTS,target.event_id.tolist()),candidates={})
    for variant in VARIANTS:
        items=[x for x in rows if x['variant']==variant]
        calibration={}
        if items:
            for k in ('home','draw','away'):
                calibration[k]=reliability([x['prediction']['probabilities'][k] for x in items],
                                           [x['result']['actual_outcome']==k for x in items])
            for line in ('1.5','2.5','3.5'):
                calibration['over_'+line]=reliability([x['prediction']['over'][line] for x in items],
                    [x['result']['actual_home']+x['result']['actual_away']>float(line) for x in items])
            calibration['both_teams_score']=reliability([x['prediction']['both_teams_score'] for x in items],
                [min(x['result']['actual_home'],x['result']['actual_away'])>0 for x in items])
        report['candidates'][variant]=dict(metrics=metrics([x['result'] for x in items]),calibration=calibration)
    report['note']='Saved retrospective BR2 2024 predictions only. No refit, no forecast edits, no new records, no model promotion. CC0 community results are not officially verified. Historical publication times unknown; not prospective success.'
    write_json(source.parent/'cohort_audit_20261106.json',report)
    print(json.dumps({k:v['metrics']['winner_accuracy'] for k,v in report['candidates'].items()}))


if __name__=='__main__': main()
