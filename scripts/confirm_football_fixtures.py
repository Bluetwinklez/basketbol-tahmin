"""Bounded independent fixture confirmation; publisher scores do not feed training."""
import argparse
import json
from bbtahmin.football.fixture_confirmation import refresh as run

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lookback',type=int,default=2)
    result=run(parser.parse_args().lookback)
    print(json.dumps(dict(checked=len(result['reviews']),errors=result['errors'])))
    raise SystemExit(1 if result['errors'] else 0)
