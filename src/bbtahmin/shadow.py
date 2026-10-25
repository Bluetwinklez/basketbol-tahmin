"""Append-only paired forward experiments, separate from original forecasts.

An experiment is versioned by its frozen policy and code. Changes start a new
cohort; past experiment records are still settled, never replaced or pooled.
"""
import hashlib
import json
import base64
import gzip
import importlib.metadata
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .experiment_metrics import metrics, paired, validate
from .prospective import canonical, fingerprint
from .quality import timestamp


def checksum(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def checked(record):
    payload=dict(record);expected=payload.pop('sha256',None)
    if checksum(payload)!=expected: raise ValueError('Shadow record hash mismatch')
    return record


def forecast_path(directory,fixture):
    identity=('provider:'+str(fixture['provider_event_id']) if fixture.get('provider_event_id') else fixture['event_id'])
    return Path(directory)/'forecasts'/(checksum([fixture['league'],identity])+'.json')


def save_new(path,payload):
    record=dict(payload,sha256=checksum(payload));path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf8') as stream:
        json.dump(record,stream,ensure_ascii=False,indent=2,allow_nan=False)
    return record


def register(root,policy):
    runtime=dict(python=sys.version,packages={p:importlib.metadata.version(p) for p in ('numpy','pandas','scipy','scikit-learn')})
    payload=dict(spec='paired-forward-policy-v2',policy=policy,source_code_sha256=fingerprint(),runtime=runtime)
    identity=checksum(payload);directory=Path(root)/'experiments'/identity
    target=directory/'protocol.json'
    if target.exists():
        saved=checked(json.loads(target.read_text(encoding='utf8')))
        if {k:v for k,v in saved.items() if k!='sha256'}!=payload: raise ValueError('Experiment policy conflict')
    else: save_new(target,payload)
    snapshot_path=directory/'source_snapshot.json.gz'
    if not snapshot_path.exists():
        files={p.as_posix():base64.b64encode(p.read_bytes()).decode('ascii') for p in sorted(Path('src').rglob('*.py'))}
        snapshot=dict(files=files,python=sys.version,packages={p:importlib.metadata.version(p) for p in ('numpy','pandas','scipy','scikit-learn')})
        encoded=gzip.compress(canonical(snapshot),mtime=0)
        with snapshot_path.open('xb') as stream:stream.write(encoded)
    return directory,identity


def freeze(directory,identity,fixture,predictions,datasets,now=None):
    clock=timestamp(now or pd.Timestamp.now(tz='UTC'));start=timestamp(fixture['start_utc'])
    captured=timestamp(fixture['captured_at'])
    if not captured<=clock<start or clock-captured>pd.Timedelta(hours=24):
        raise ValueError('Fresh pregame fixture confirmation required')
    if fixture.get('status')!='scheduled' or fixture.get('home')==fixture.get('away'):
        raise ValueError('Distinct confirmed scheduled teams required')
    if not fixture.get('source_url','').startswith('https://'): raise ValueError('Fixture source required')
    if set(predictions)!={'reference','candidate'}: raise ValueError('Both paired variants required')
    for p in predictions.values():
        if p['class_labels'] not in (['home','away'],['home','draw','away']): raise ValueError('Unknown class order')
        validate([0],[p['probabilities']])
        if len(p['class_labels'])!=len(p['probabilities']): raise ValueError('Class order mismatch')
        if not np.isfinite([p['expected_home'],p['expected_away']]).all() or min(p['expected_home'],p['expected_away'])<0:
            raise ValueError('Finite nonnegative score expectations required')
        for key in ('league','home','away'):
            if p[key]!=fixture[key]: raise ValueError('Prediction fixture mismatch')
        if p['information_cutoff_utc']!=clock.isoformat(): raise ValueError('Prediction information cutoff mismatch')
        if type(p.get('eligible')) is not bool: raise ValueError('Explicit eligibility required')
    if predictions['reference']['class_labels']!=predictions['candidate']['class_labels']:
        raise ValueError('Paired class order mismatch')
    path=forecast_path(directory,fixture)
    if path.exists():
        original=checked(json.loads(path.read_text(encoding='utf8')))
        if original['fixture']!=fixture:
            # Fresh captures may change, but actual fixture identities may not.
            for key in ('league','home','away','start_utc'):
                if original['fixture'][key]!=fixture[key]: raise ValueError('Fixture changed; retain original pair for review')
        return original
    return save_new(path,dict(spec='paired-forward-forecast-v1',experiment_id=identity,
                             recorded_at_utc=clock.isoformat(),fixture=fixture,predictions=predictions,datasets=datasets))


def evaluate(directory,results,now=None,active=False):
    clock=timestamp(now or pd.Timestamp.now(tz='UTC'))
    protocol=checked(json.loads((Path(directory)/'protocol.json').read_text(encoding='utf8')))
    snapshot_path=Path(directory)/'source_snapshot.json.gz'
    snapshot_verified=False
    if snapshot_path.exists():
        snapshot=json.loads(gzip.decompress(snapshot_path.read_bytes()))
        # fingerprint uses paths relative to repository root, including src/.
        content=b''.join(name.encode()+b'\0'+base64.b64decode(raw) for name,raw in sorted(snapshot['files'].items()))
        snapshot_verified=hashlib.sha256(content).hexdigest()==protocol['source_code_sha256']
        if not snapshot_verified:raise ValueError('Frozen source snapshot fingerprint mismatch')
    indexed={}
    provider_index={}
    for result in results:
        key=(result['league'],result['event_id'])
        if key in indexed and result!=indexed[key]: raise ValueError('Ambiguous shadow final')
        indexed[key]=result
        if result.get('provider_event_id'):
            provider_key=(result['league'],result['provider_event_id'])
            old=provider_index.get(provider_key)
            if old and any(old.get(k)!=result.get(k) for k in ('home','away','start_utc','status','home_score','away_score')):
                raise ValueError('Ambiguous publisher final identity')
            provider_index[provider_key]=result
    rows=[];pending=0;rejected=[]
    for path in sorted((Path(directory)/'forecasts').glob('*.json')):
        record=checked(json.loads(path.read_text(encoding='utf8')));f=record['fixture']
        if record['experiment_id']!=protocol['sha256']: raise ValueError('Record belongs to another experiment')
        if timestamp(record['recorded_at_utc'])>clock: continue
        result=indexed.get((f['league'],f['event_id']))
        if result is None and f.get('provider_event_id'):result=provider_index.get((f['league'],f['provider_event_id']))
        if not result or result.get('status')!='final': pending+=1;continue
        try:
            if any(result[k]!=f[k] for k in ('league','home','away')): raise ValueError('Final team identity mismatch')
            actual=timestamp(result['start_utc']);captured=timestamp(result['captured_at'])
            if not timestamp(record['recorded_at_utc'])<actual<captured<=clock:
                raise ValueError('Invalid pregame/final evidence timing')
            if abs(actual-timestamp(f['start_utc']))>pd.Timedelta(hours=6): raise ValueError('Rescheduled fixture requires review')
            if not result.get('source_url','').startswith('https://'): raise ValueError('Final source required')
            h,a=result['home_score'],result['away_score']
            if any(type(v) is not int or v<0 for v in (h,a)): raise ValueError('Integer final scores required')
            labels=record['predictions']['reference']['class_labels']
            if len(labels)==2 and (h==a or min(h,a)<=0): raise ValueError('Basketball final must be positive and non-tied')
            outcome='home' if h>a else 'away' if a>h else 'draw'
            for variant,p in record['predictions'].items():
                total=p['expected_home']+p['expected_away'];margin=p['expected_home']-p['expected_away']
                rows.append(dict(event_id=f['event_id'],league=f['league'],day=actual.strftime('%Y-%m-%d'),
                                 variant=variant,y=labels.index(outcome),p=p['probabilities'],selected=p['eligible'],
                                 team_mae=(abs(p['expected_home']-h)+abs(p['expected_away']-a))/2,
                                 total_mae=abs(total-h-a),margin_mae=abs(margin-h+a),
                                 source_url=result['source_url'],record_sha256=record['sha256']))
        except ValueError as exc:
            rejected.append(dict(event_id=f['event_id'],reason=str(exc)));pending+=1
    groups=[]
    for code in sorted({r['league'] for r in rows}):
        group=[r for r in rows if r['league']==code]
        comparisons=paired(group,'reference','candidate')
        summary={v:dict(**metrics([r['y'] for r in group if r['variant']==v],
                                  [r['p'] for r in group if r['variant']==v],
                                  [r['selected'] for r in group if r['variant']==v]),
                        score_errors={k:float(np.mean([r[k] for r in group if r['variant']==v]))
                                      for k in ('team_mae','total_mae','margin_mae')}) for v in ('reference','candidate')}
        changes=comparisons['changes'];enough=comparisons['games']>=100 and comparisons['day_blocks']>=20
        ordered_days=sorted({r['day'] for r in group});boundary=ordered_days[len(ordered_days)//2]
        stability=[]
        for later in (False,True):
            part=[r for r in group if (r['day']>=boundary)==later]
            if not part:continue
            check=paired(part,'reference','candidate',replicates=200)
            stability.append(dict(period='later' if later else 'earlier',games=check['games'],
                                  accuracy_delta=check['changes']['accuracy']['delta'],
                                  log_loss_delta=check['changes']['log_loss']['delta']))
        eligible=bool(active and snapshot_verified and enough and changes['accuracy']['day_block_95_interval'][0]>0 and
                      changes['log_loss']['day_block_95_interval'][1]<0 and changes['brier']['delta']<=0 and
                      summary['candidate']['coverage']>=.9*summary['reference']['coverage'] and
                      summary['candidate']['selected']['games']>=20 and
                      len(stability)==2 and all(s['accuracy_delta']>=0 and s['log_loss_delta']<=0 for s in stability))
        groups.append(dict(league=code,summary=summary,paired=comparisons,
                           temporal_stability=stability,
                           promotion_review_eligible=eligible,production_promoted=False,
                           reason='Sample checkpoints plus paired uncertainty, losses and coverage; independent temporal stability review still required. No automatic promotion.'))
    return dict(spec='paired-forward-report-v1',checked_at_utc=clock.isoformat(),pending=pending,
                settled_games=len(rows)//2,rejected=rejected,leagues=groups,rows=rows,
                source_snapshot_verified=snapshot_verified,
                active_experiment=active,
                production_default_changed=False)
