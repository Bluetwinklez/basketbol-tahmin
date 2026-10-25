"""Freeze league-specific future challengers before their first outcomes."""
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from bbtahmin.football.data import write_json
from bbtahmin.prior_policy import learn,TEMPERATURES


def main():
    cutoff=pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d');policies={};hashes={};errors=[]
    choices=dict(football=('baseline','recency90','shrinkage16','opponent','opponent_dc','ensemble'),
                 basketball=('baseline','form_slow','form_fast','without_rest','without_opponent_ratings','without_home'))
    for sport,variants in choices.items():
        policies[sport]={}
        for path in sorted(Path('docs/kanit/improvement',sport).glob('*.json.gz')):
            raw=path.read_bytes();hashes[path.as_posix()]=hashlib.sha256(raw).hexdigest()
            source=json.loads(gzip.decompress(raw))
            try:policies[sport][source['league']]=learn(source['rows'],variants,cutoff,basketball=sport=='basketball')
            except ValueError as exc:errors.append(dict(sport=sport,league=source['league'],reason=str(exc)))
    payload=dict(spec='prior-oos-forward-policy-v1',input_hashes=hashes,policies=policies,errors=errors,
                 temperature_grid=TEMPERATURES,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 note='Research challenger registry; no production promotion. Available past season completeness unverified. Current outcomes excluded.')
    path=Path('data/improvement_policy/current.json')
    if path.exists() and json.loads(path.read_text(encoding='utf8'))!=json.loads(json.dumps(payload)):
        raise ValueError('Frozen forward policies differ; create an explicit new registry version')
    if not path.exists():write_json(path,payload)
    print(json.dumps({s:{c:(p['variant'],p['temperature']) for c,p in groups.items()} for s,groups in policies.items()}))


if __name__=='__main__':main()
