"""Scheduled independent source refresh; preserve ledgers and surface failures."""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from bbtahmin.daily import LEAGUES, run as basketball_run
from bbtahmin.football.data import collect, write_json, source_refresh_session
from bbtahmin.football.daily import run as football_run
from bbtahmin.football.calendar import collect as calendar_collect
from bbtahmin.refresh_health import (auto_disabled, classify_errors, load_known_missing,
                                    refresh_exit_code, saved_reports)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sport',choices=['football','basketball','all'],default='all')
    parser.add_argument('--backfill',action='store_true',help='Refresh historical seasons as well as the active season')
    args=parser.parse_args()
    with source_refresh_session():
        return refresh(args)


def refresh(args):
    directory=Path('data/refresh')
    entries=load_known_missing(directory/'known_missing.json')
    results={}
    for sport in ('football','basketball'):
        if args.sport not in (sport,'all'): continue
        skipped=[]
        try:
            if sport=='football':
                from refresh_screenshot_leagues import run as screenshot_refresh
                errors=[]
                def attempt(name, action):
                    try:
                        result=action()
                        errors.extend(dict(e, source=e.get('source', name), collector=name)
                                      for e in result.get('errors',[]))
                        return result
                    except Exception as exc:
                        errors.append(dict(source=name,error=f'{type(exc).__name__}: {exc}',retained_previous=True))
                        return None
                attempt('screenshots',lambda: screenshot_refresh(args.backfill))
                attempt('football',lambda: collect(current_only=not args.backfill))
                for code in ('BR2','BR1','AR1','CO1','US1','JP1','CN1'):
                    attempt(code,lambda code=code: calendar_collect(current_only=not args.backfill,code=code))
                # A source outage must not prevent settlement of existing forecasts.
                attempt('football_ledger',lambda: football_run(output='data/football_ledger'))

            else:
                skip=auto_disabled(saved_reports(directory),sport,'PBA_GOV',pd.Timestamp.now(tz='UTC'),
                                   threshold=3,retry_days=7)
                if skip:
                    skipped.append(skip)
                backfill_errors=[]
                if args.backfill:
                    from bbtahmin.veri import turkey,ukraine,argentina
                    for name,collector,first in [('TR_BSL',turkey.collect,2010),('UKR',ukraine.collect,2016),('ARG_LNB',argentina.collect,2022)]:
                        try: collector(first=first)
                        except Exception as exc: backfill_errors.append(dict(league=name,error=str(exc),stage='historical_backfill'))
                report=basketball_run(leagues=list(LEAGUES),output='data/basketball_ledger',update=True,hours=168,
                                      skip_sources={item['league'] for item in skipped})
                errors=backfill_errors+[dict(league=c,**s) for c,s in report['sources'].items() if s['status']=='failed']
            results[sport]=dict(status='partial' if errors else 'succeeded',errors=errors)
        except Exception as exc:
            results[sport]=dict(status='failed',error=f'{type(exc).__name__}: {exc}')
        results[sport].update(classify_errors(sport,results[sport].get('errors',[]),entries))
        if skipped:
            results[sport]['skipped_auto_disabled']=skipped
    finished=pd.Timestamp.now(tz='UTC')
    write_json(directory/(finished.strftime('%Y%m%dT%H%M%SZ')+'.json'),results)
    print(json.dumps(results,indent=2));return refresh_exit_code(results,entries,finished.date())


if __name__=='__main__': sys.exit(main())

