"""Compare two saved refresh reports offline; never download match data."""
import argparse
import hashlib
import json
from pathlib import Path
from bbtahmin.football.data import write_json
from bbtahmin.refresh_health import transitions

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous', type=Path)
    parser.add_argument('current', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = transitions(json.loads(args.previous.read_text()), json.loads(args.current.read_text()))
    report['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.previous, args.current)}
    write_json(args.output, report)
    print(json.dumps({s:{k:len(v) if isinstance(v,list) else v for k,v in r.items()} for s,r in report['sports'].items()},indent=2))
