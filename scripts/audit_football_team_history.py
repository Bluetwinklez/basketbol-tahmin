"""Create a reproducible last-50 inventory without downloading or changing data."""
import argparse
import hashlib
from pathlib import Path
from bbtahmin.football.data import load, write_json
from bbtahmin.football.coverage import team_history_coverage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--league', default='TR1')
    parser.add_argument('--season', required=True)
    parser.add_argument('--cutoff', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    root=Path('data/football')
    report=team_history_coverage(load(root),args.league,args.season,args.cutoff)
    paths=sorted(root.glob(f'{args.league}_20*.json.gz'))+sorted((root/'licensed_overlays').glob(f'{args.league}_20*.json.gz'))
    report['archive_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    write_json(args.output,report)
    print({k:v for k,v in report.items() if k not in ('teams','archive_sha256')})


if __name__=='__main__': main()
