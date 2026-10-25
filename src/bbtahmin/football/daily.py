"""Freeze future day-level forecasts separately from basketball records."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from .data import ROOT, load, write_json
from .model import GoalModel, metrics, score


def digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def run(days=7, output='rapor/football', root=ROOT, now=None, model_variant='baseline'):
    from .challenger import fit, VARIANTS
    if model_variant not in VARIANTS: raise ValueError('Unknown football model candidate')
    if type(days) is not int or not 1<=days<=14: raise ValueError('Horizon must be 1..14 days')
    now=pd.Timestamp(now or pd.Timestamp.now(tz='UTC'))
    if now.tzinfo is None: raise ValueError('Timezone required')
    now=now.tz_convert('UTC'); today=now.strftime('%Y-%m-%d'); end=(now+pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    frame=load(root)
    frame=frame.astype(object).where(pd.notna(frame),None)
    output=Path(output); ledger=output/'forecasts'; ledger.mkdir(parents=True,exist_ok=True)
    if frame.empty: raise ValueError('Collect football data first')
    collection=json.loads((Path(root)/'collection.json').read_text())
    forecasts=[]; skipped=[]; models={}
    archive_sha=digest(frame.to_json(orient='records'))
    for g in frame.loc[(frame.status=='scheduled')&(frame.date>today)&(frame.date<=end)].sort_values(['date','league','event_id']).to_dict('records'):
        path=ledger/(g['event_id']+'.json')
        if path.exists(): continue
        try:
            # A future fixture is valid only if actually captured before its date.
            if g['captured_at_utc'][:10]>=g['date']: raise ValueError('Not a pregame source capture')
            captured=pd.Timestamp(g['captured_at_utc'])
            if captured.tzinfo is None: raise ValueError('Fixture capture timezone required')
            if captured>now: raise ValueError('Fixture capture is in the future')
            if (now-captured).total_seconds()>72*3600: raise ValueError('Fixture snapshot older than 72 hours; refresh required')
            if g['league'] not in models: models[g['league']]=fit(frame,g['league'],today,model_variant)
            prediction=models[g['league']].predict(g['home'],g['away'])
            if prediction.get('issues'): raise ValueError('Insufficient history: '+'; '.join(prediction['issues']))
            payload=dict(spec='football-prospective-v1',recorded_at_utc=now.isoformat(),fixture=g,prediction=prediction,
                         archive_sha256=archive_sha)
            record=dict(payload,payload_sha256=digest(payload))
            encoded=json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)
            with path.open('x',encoding='utf8') as f: f.write(encoded)
        except (ValueError, OSError) as exc: skipped.append(dict(event_id=g['event_id'],reason=str(exc)))
    rows={g['event_id']:g for g in frame.to_dict('records')}
    settled=[]; pending=0
    for path in sorted(ledger.glob('*.json')):
        record=json.loads(path.read_text()); sha=record.pop('payload_sha256')
        if digest(record)!=sha: raise ValueError('Frozen football forecast hash mismatch')
        fixture=record['fixture']; g=rows.get(fixture['event_id'])
        result=None
        if record['recorded_at_utc'][:10]>=fixture['date']: raise ValueError('Forecast was not recorded before fixture date')
        # Community scores are explicitly separate from official verification.
        if g and g['status']=='final' and g['date']<today:
            if any(g[k]!=fixture[k] for k in ('home','away','date','league')): raise ValueError('Result identity mismatch')
            result=score(record['prediction'],int(g['home_goals']),int(g['away_goals']))
            result.update(verification='community_source_final_not_official',source_url=g['source_url'])
            settled.append(result)
        else: pending+=1
        forecasts.append(dict(fixture=fixture,prediction=record['prediction'],recorded_at_utc=record['recorded_at_utc'],
                              status='publisher_final' if result else 'pending',result=result))
    report=dict(spec='football-daily-v1',checked_at_utc=now.isoformat(),collection_checked_at_utc=collection['checked_at_utc'],
                source_errors=collection['errors'],forecasts=forecasts,skipped=skipped,pending=pending,
                requested_model_variant=model_variant,
                publisher_performance=metrics(settled),official_verified_games=0,official_winner_accuracy=None,
                note='Community CC0 source; publisher finals are not official confirmation. Official accuracy is unavailable. Day-only fixtures exclude today. Small samples cannot establish accuracy. Expected goals are model means, not observed xG.')
    write_json(output/'latest.json',report)
    return report

