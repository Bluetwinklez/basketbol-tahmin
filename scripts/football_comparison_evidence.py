"""Reproduce paired day-block uncertainty from stored challenger predictions."""
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

from bbtahmin.football.data import write_json


def summarize(rows):
    days={}
    for item in rows:
        b=item['results']['baseline'];o=item['results']['opponent']
        value=days.setdefault(item['date'],[0,0.,0.])
        value[0]+=1;value[1]+=int(o['winner_correct'])-int(b['winner_correct'])
        value[2]+=o['log_loss']-b['log_loss']
    array=np.array(list(days.values()));rng=np.random.default_rng(1729)
    sampled=array[rng.integers(0,len(array),size=(2500,len(array)))].sum(axis=1)
    return dict(games=len(rows),days=len(days),baseline_correct=sum(x['results']['baseline']['winner_correct'] for x in rows),
        opponent_correct=sum(x['results']['opponent']['winner_correct'] for x in rows),
        accuracy_delta=float(array[:,1].sum()/array[:,0].sum()),
        accuracy_delta_day_block_95=list(map(float,np.quantile(sampled[:,1]/sampled[:,0],[.025,.975]))),
        log_loss_delta=float(array[:,2].sum()/array[:,0].sum()),
        log_loss_delta_day_block_95=list(map(float,np.quantile(sampled[:,2]/sampled[:,0],[.025,.975]))),
        note='Paired bootstrap by fixture date across leagues, 2500 resamples, seed 1729; descriptive retrospective uncertainty, not prospective proof.')


def main():
    root=Path('docs/kanit/football_challenger')
    rows=json.loads(gzip.decompress((root/'predictions.json.gz').read_bytes()))
    original={'AT1','DE1','DE2','EN1','EN2','ES1','ES2','FR1','FR2','IT1','IT2','NL1','PT1','TR1'}
    report=dict(expanded_20_leagues=summarize(rows),original_14_leagues=summarize([x for x in rows if x['league'] in original]))
    write_json(root/'paired_uncertainty.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
