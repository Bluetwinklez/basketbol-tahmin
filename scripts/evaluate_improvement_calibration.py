"""Prior-OOS-only basketball calibration, all common-policy variants retained."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.special import softmax

from bbtahmin.experiment_metrics import metrics,paired
from bbtahmin.football.data import write_json

TEMPERATURES=(.75,1.,1.25,1.5,2.)


def transform(p,temperature):
    return softmax(np.log(np.clip(p,1e-15,1))/temperature,axis=-1)


def evaluate(rows):
    reports=[]
    for variant in sorted({r['variant'] for r in rows}):
        group=[r for r in rows if r['variant']==variant]
        for season in sorted({r['season'] for r in group}):
            earlier=[r for r in group if r['season']<season]
            target=[r for r in group if r['season']==season]
            if len(earlier)<100 or len({r['y'] for r in earlier})<2:continue
            if max(r['day'] for r in earlier)>=min(r['day'] for r in target):
                raise ValueError('Calibration chronology overlaps target')
            value=min(TEMPERATURES,key=lambda t:(metrics([r['y'] for r in earlier],transform([r['p'] for r in earlier],t))['all']['log_loss'],abs(t-1)))
            original=[dict(r,variant='reference') for r in target]
            adjusted=[dict(r,variant='calibrated',p=transform(r['p'],value).tolist()) for r in target]
            summaries={}
            for name,part in (('reference',original),('calibrated',adjusted)):
                # Reapply the fixed .65 gate to calibrated confidence; preserve
                # original diagnostic eligibility separately from confidence.
                # Original records combine both, so do not infer missing flags.
                summaries[name]=metrics([r['y'] for r in part],[r['p'] for r in part])
            reports.append(dict(variant=variant,target_season=season,temperature=value,calibration_games=len(earlier),
                                last_calibration_day=max(r['day'] for r in earlier),summaries=summaries,
                                paired=paired(original+adjusted,'reference','calibrated'),
                                note='All-game calibration only; selected coverage not re-estimated from incomplete diagnostic flags. Score means/intervals unchanged.'))
    return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',default='docs/kanit/improvement/basketball')
    parser.add_argument('--output',default='docs/kanit/improvement/calibration')
    args=parser.parse_args();root=Path(args.output);root.mkdir(parents=True,exist_ok=True)
    sources=sorted(Path(args.input).glob('*.json.gz'))
    hashes={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    protocol=dict(spec='earlier-oos-temperature-v1',temperature_grid=TEMPERATURES,input_hashes=hashes,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  selection='Minimize log loss on strictly earlier OOS seasons only; no target tuning.',
                  production_default_changed=False,evidence_kind='exploratory_retrospective')
    path=root/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=json.loads(json.dumps(protocol)):
        raise ValueError('Changed calibration protocol; use a new output directory')
    if not path.exists():write_json(path,protocol)
    reports=[]
    for source in sources:
        payload=json.loads(gzip.decompress(source.read_bytes()))
        reports.append(dict(league=payload['league'],reports=evaluate(payload['rows'])))
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):
        raise ValueError('Calibration input changed during evaluation')
    write_json(root/'summary.json',dict(protocol=protocol,reports=reports,
                limitations='Historical publication availability unknown. Already inspected seasons are exploratory; calibration does not validate the production reference for other models.'))
    print(json.dumps(dict(leagues=len(reports),comparisons=sum(len(r['reports']) for r in reports))))


if __name__=='__main__':main()
