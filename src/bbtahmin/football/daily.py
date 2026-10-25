"""Freeze timestamp-confirmed football forecasts; retain legacy day-only records."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from .data import ROOT, load, write_json
from .model import GoalModel, metrics, score
from .health import assess as assess_history


def digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def run(days=7, output='rapor/football', root=ROOT, now=None, model_variant='baseline',require_fixture_confirmation=True):
    from .challenger import fit, VARIANTS
    if model_variant not in VARIANTS: raise ValueError('Unknown football model candidate')
    if type(days) is not int or not 1<=days<=14: raise ValueError('Horizon must be 1..14 days')
    replay_clock=now is not None
    now=pd.Timestamp(now or pd.Timestamp.now(tz='UTC'))
    if now.tzinfo is None: raise ValueError('Timezone required')
    now=now.tz_convert('UTC'); today=now.strftime('%Y-%m-%d'); end=(now+pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    frame=load(root)
    frame=frame.astype(object).where(pd.notna(frame),None)
    output=Path(output); ledger=output/'forecasts'; ledger.mkdir(parents=True,exist_ok=True)
    if frame.empty: raise ValueError('Collect football data first')
    collection=json.loads((Path(root)/'collection.json').read_text())
    review_path=Path(root)/'fixture_reviews.json'
    reviews={}
    if review_path.exists():
        review_file=json.loads(review_path.read_text(encoding='utf8'))
        if review_file.get('spec')!='football-fixture-reviews-v1' or not isinstance(review_file.get('reviews'),dict):
            raise ValueError('Invalid fixture review registry')
        reviews=review_file['reviews']
    forecasts=[]; skipped=[]; models={}
    known_provider={}
    for existing in sorted(ledger.glob('*.json')):
        saved=json.loads(existing.read_text(encoding='utf8'));payload=dict(saved);expected=payload.pop('payload_sha256')
        if digest(payload)!=expected:raise ValueError('Frozen football forecast hash mismatch')
        if pd.Timestamp(saved['recorded_at_utc'])>now:continue
        source=saved['fixture'].get('independent_fixture',{})
        if source.get('provider_event_id'):
            identity=(saved['fixture']['league'],source['provider_event_id'])
            if identity in known_provider:raise ValueError('Duplicate frozen publisher fixture requires review')
            known_provider[identity]=existing
    confirmation_path=Path(root).parent/'football_fixture_checks/latest.json'
    confirmations={}
    confirmation_errors=[]
    failed_confirmation_leagues=set()
    provider_bindings={}
    if confirmation_path.exists():
        snapshot=json.loads(confirmation_path.read_text(encoding='utf8'))
        if snapshot.get('spec')!='football-fixture-confirmation-v1':raise ValueError('Invalid independent fixture confirmation schema')
        failed_confirmation_leagues={e['league'] for e in snapshot.get('errors',[]) if e.get('league')}
        confirmation_errors=snapshot.get('errors',[])
        for check in snapshot['reviews']:
            if check['event_id'] in confirmations:raise ValueError('Duplicate independent fixture confirmation')
            confirmations[check['event_id']]=check
            if check['status'] in ('confirmed','date_conflict'):
                obs=check['observation']
                if obs.get('provider_event_id'):
                    identity=(obs['league'],obs['provider_event_id'])
                    if identity in provider_bindings and provider_bindings[identity]!=obs['event_id']:
                        raise ValueError('Ambiguous publisher-to-archive fixture identity')
                    provider_bindings[identity]=obs['event_id']
    elif require_fixture_confirmation:
        confirmation_errors=[dict(source='independent_fixture_confirmation',error='No independent fixture snapshot; refresh required')]
    known_future={identity for identity,check in confirmations.items() if check['status'] in ('confirmed','date_conflict') and
                  check['observation']['status']=='scheduled' and pd.Timestamp(check['observation']['start_utc'])>now and
                  pd.Timestamp(check['observation']['captured_at'])<=now and now-pd.Timestamp(check['observation']['captured_at'])<=pd.Timedelta(hours=24)}
    health_frame=frame.loc[~frame.event_id.isin(known_future)]
    archive_sha=digest(frame.to_json(orient='records'))
    from ..prospective import fingerprint
    code_sha=fingerprint()
    window_start=(now-pd.Timedelta(days=2)).strftime('%Y-%m-%d');window_end=(now+pd.Timedelta(days=days+2)).strftime('%Y-%m-%d')
    for g in frame.loc[(frame.status=='scheduled')&(frame.date>=window_start)&(frame.date<=window_end)].sort_values(['date','league','event_id']).to_dict('records'):
        path=ledger/(g['event_id']+'.json')
        if path.exists(): continue
        try:
            if g['event_id'] in reviews:
                raise ValueError('Fixture date/identity is quarantined; original record retained for review')
            # A future fixture is valid only if actually captured before its date.
            if not require_fixture_confirmation and g['captured_at_utc'][:10]>=g['date']: raise ValueError('Not a pregame source capture')
            captured=pd.Timestamp(g['captured_at_utc'])
            if captured.tzinfo is None: raise ValueError('Fixture capture timezone required')
            if captured>now: raise ValueError('Fixture capture is in the future')
            if (now-captured).total_seconds()>72*3600: raise ValueError('Fixture snapshot older than 72 hours; refresh required')
            if require_fixture_confirmation:
                if g['league'] in failed_confirmation_leagues:raise ValueError('Independent fixture source refresh incomplete for league')
                check=confirmations.get(g['event_id'])
                if not check or check['status'] not in ('confirmed','date_conflict'):
                    raise ValueError('Independent fixture identity/time unconfirmed; refresh fixture checks')
                observation=check['observation'];start=pd.Timestamp(observation['start_utc']);observed=pd.Timestamp(observation['captured_at'])
                if any(observation[k]!=g[k] for k in ('league','home','away')):raise ValueError('Independent fixture team mismatch')
                if observation['status']!='scheduled' or not observed<=now<start<=now+pd.Timedelta(days=days) or now-observed>pd.Timedelta(hours=24):
                    raise ValueError('Fresh independent future scheduled fixture required')
                if observation.get('provider_event_id') and (g['league'],observation['provider_event_id']) in known_provider:continue
                g=dict(g,source_original_date=g['date'],date=start.strftime('%Y-%m-%d'),verified_start_utc=start.isoformat(),
                       independent_fixture=observation)
            elif not today<g['date']<=end:continue
            health=assess_history(health_frame,g,now)
            if not health['diagnostic_gate_passed']:
                raise ValueError('Insufficient history (current coverage): '+'; '.join(health['blocking_issues']))
            if g['league'] not in models: models[g['league']]=fit(frame,g['league'],today,model_variant)
            prediction=models[g['league']].predict(g['home'],g['away'])
            if prediction.get('issues'): raise ValueError('Insufficient history: '+'; '.join(prediction['issues']))
            recorded=now if replay_clock else pd.Timestamp.now(tz='UTC')
            if g.get('verified_start_utc') and recorded>=pd.Timestamp(g['verified_start_utc']):raise ValueError('Forecast computation finished after kickoff')
            payload=dict(spec='football-prospective-v1',recorded_at_utc=recorded.isoformat(),fixture=g,prediction=prediction,
                         archive_sha256=archive_sha,source_code_sha256=code_sha,
                         requested_model_variant=model_variant,history_health=health,
                         selection_policy='Current-history diagnostic gate plus existing model issues; research only, no validated recommendation.')
            record=dict(payload,payload_sha256=digest(payload))
            encoded=json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)
            with path.open('x',encoding='utf8') as f: f.write(encoded)
        except (ValueError, OSError) as exc: skipped.append(dict(event_id=g['event_id'],reason=str(exc)))
    rows={g['event_id']:g for g in frame.to_dict('records')}
    for g in list(rows.values()):
        aliases=g.get('event_aliases')
        if isinstance(aliases,list):
            for alias in aliases:
                if alias in rows and rows[alias]['event_id']!=g['event_id']:raise ValueError('Ambiguous archive event alias')
                rows[alias]=g
    settled=[]; pending=0
    for path in sorted(ledger.glob('*.json')):
        record=json.loads(path.read_text()); sha=record.pop('payload_sha256')
        if digest(record)!=sha: raise ValueError('Frozen football forecast hash mismatch')
        if pd.Timestamp(record['recorded_at_utc'])>now:
            skipped.append(dict(record=str(path),reason='Forecast was recorded after requested clock'))
            continue
        fixture=record['fixture']; g=rows.get(fixture['event_id'])
        if g is None:
            source=fixture.get('independent_fixture',{})
            if source.get('provider_event_id'):
                g=rows.get(provider_bindings.get((fixture['league'],source['provider_event_id'])))
        result=None
        if fixture.get('verified_start_utc'):
            if pd.Timestamp(record['recorded_at_utc'])>=pd.Timestamp(fixture['verified_start_utc']):raise ValueError('Forecast was not recorded before verified kickoff')
        elif record['recorded_at_utc'][:10]>=fixture['date']: raise ValueError('Forecast was not recorded before fixture date')
        # Community scores are explicitly separate from official verification.
        review=reviews.get(fixture['event_id'])
        if review and fixture.get('verified_start_utc') and pd.Timestamp(fixture['verified_start_utc'])==pd.Timestamp(review['observed_start_utc']) and fixture['date']==review['observed_start_utc'][:10]:
            review=None  # This new immutable record already used the checked time.
        if g and g['status']=='final' and g['date']<today and not review:
            if any(g[k]!=fixture[k] for k in ('home','away','date','league')): raise ValueError('Result identity mismatch')
            result=score(record['prediction'],int(g['home_goals']),int(g['away_goals']))
            result.update(verification='community_source_final_not_official',source_url=g['source_url'])
            settled.append(result)
        else: pending+=1
        forecasts.append(dict(fixture=fixture,prediction=record['prediction'],recorded_at_utc=record['recorded_at_utc'],
                              status='fixture_review_required' if review else 'publisher_final' if result else 'pending',result=result,
                              fixture_review=review))
    report=dict(spec='football-daily-v1',checked_at_utc=now.isoformat(),collection_checked_at_utc=collection['checked_at_utc'],
                source_errors=collection['errors']+confirmation_errors,forecasts=forecasts,skipped=skipped,pending=pending,
                requested_model_variant=model_variant,
                publisher_performance=metrics(settled),official_verified_games=0,official_winner_accuracy=None,
                note='Community CC0 and separately attributed CC BY-SA supplements; publisher finals are not official confirmation. Official accuracy is unavailable. New forecasts require independently confirmed future kickoffs. Small samples cannot establish accuracy. Expected goals are model means, not observed xG.')
    write_json(output/'latest.json',report)
    return report

