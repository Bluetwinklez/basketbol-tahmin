"""Scheduled independent source refresh; preserve ledgers and surface failures."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from bbtahmin.daily import LEAGUES, run as basketball_run
from bbtahmin.football.data import collect, write_json
from bbtahmin.football.daily import run as football_run
from bbtahmin.football.calendar import collect as calendar_collect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sport',choices=['football','basketball','all'],default='all')
    parser.add_argument('--backfill',action='store_true',help='Refresh historical seasons as well as the active season')
    args=parser.parse_args(); results={}; failed=False
    for sport in ('football','basketball'):
        if args.sport not in (sport,'all'): continue
        try:
            if sport=='football':
                collection=collect(current_only=not args.backfill)
                calendar=calendar_collect(current_only=not args.backfill)
                for code in ('BR1','AR1','CO1','US1','JP1','CN1'):
                    extra=calendar_collect(current_only=not args.backfill,code=code)
                    calendar['errors'].extend(extra['errors'])
                report=football_run(output='data/football_ledger')
                errors=collection['errors']+calendar['errors']
            else:
                backfill_errors=[]
                if args.backfill:
                    from bbtahmin.veri import turkey,ukraine,argentina
                    for name,collector,first in [('TR_BSL',turkey.collect,2010),('UKR',ukraine.collect,2016),('ARG_LNB',argentina.collect,2022)]:
                        try: collector(first=first)
                        except Exception as exc: backfill_errors.append(dict(league=name,error=str(exc),stage='historical_backfill'))
                report=basketball_run(leagues=list(LEAGUES),output='data/basketball_ledger',update=True,hours=168)
                errors=backfill_errors+[dict(league=c,**s) for c,s in report['sources'].items() if s['status']=='failed']
            results[sport]=dict(status='partial' if errors else 'succeeded',errors=errors)
            # Keep data on partial success, but never report a green refresh.
            failed=failed or bool(errors)
        except Exception as exc:
            failed=True;results[sport]=dict(status='failed',error=f'{type(exc).__name__}: {exc}')
    write_json(Path('data/refresh')/(pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%SZ')+'.json'),results)
    print(json.dumps(results,indent=2));return 1 if failed else 0


if __name__=='__main__': sys.exit(main())

