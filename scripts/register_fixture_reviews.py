"""Retain audited fixture-date conflicts without rewriting frozen forecasts."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from bbtahmin.football.data import write_json


def register(audit):
    result={}
    for row in audit['rows']:
        if row['sport']!='football' or row['status'] not in ('final_date_corrected','date_mismatch_pending'):
            continue
        start=pd.Timestamp(row['actual_start'])
        if start.tzinfo is None: raise ValueError('Actual fixture requires timezone')
        if not row.get('result_source','').startswith('https://') or not row.get('provider_event_id'):
            raise ValueError('Provider fixture identity and source required')
        if row['event_id'] in result: raise ValueError('Ambiguous date correction')
        result[row['event_id']]=dict(league=row['league'],home=row['prediction']['home'],away=row['prediction']['away'],
                                     original_date=row['fixture_start'][:10],observed_start_utc=start.isoformat(),
                                     provider_event_id=row['provider_event_id'],source_url=row['result_source'],
                                     checked_at_utc=audit['checked_at_utc'],status='quarantined_date_conflict',
                                     note='Explicit prior audit identity review. Original forecast remains unchanged; provider date is not automatic rescheduling authority.')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',required=True)
    parser.add_argument('--output',default='data/football/fixture_reviews.json')
    args=parser.parse_args();raw=Path(args.audit).read_bytes();records=register(json.loads(raw))
    write_json(args.output,dict(spec='football-fixture-reviews-v1',audit_sha256=hashlib.sha256(raw).hexdigest(),reviews=records))
    print(json.dumps(dict(quarantined=len(records))))


if __name__=='__main__': main()
