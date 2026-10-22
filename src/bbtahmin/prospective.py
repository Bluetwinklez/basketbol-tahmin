"""Append-only pretipoff forecasts and explicit point/percentage settlement errors."""
import hashlib,json,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from .quality import timestamp,validate_prediction,ARCHIVES

SPEC='prospective-v1'


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()


def fingerprint(root=Path('.')):
    paths=sorted((root/'src').rglob('*.py'))
    return hashlib.sha256(b''.join(str(p.relative_to(root)).encode()+b'\0'+p.read_bytes() for p in paths)).hexdigest()


def freeze(predictions,fixtures,destination,now=None):
    now=timestamp(now or pd.Timestamp.now(tz='UTC'))
    if not predictions or len(predictions)!=len(fixtures):raise ValueError('Each prediction requires one verified fixture')
    ids=set();rows=[]
    for p,f in zip(predictions,fixtures):
        validate_prediction(p)
        for key in ('event_id','source_url','captured_at','start_utc','league','home','away','status'):
            if not f.get(key):raise ValueError('Missing fixture identity or provenance')
        if f['event_id'] in ids:raise ValueError('Duplicate prospective fixture')
        ids.add(f['event_id'])
        start=timestamp(f['start_utc']);captured=timestamp(f['captured_at'])
        if not captured<=now<start or f['status']!='scheduled':raise ValueError('Only confirmed future scheduled fixtures may be frozen')
        if now-captured>pd.Timedelta(hours=24):raise ValueError('Refresh stale fixture confirmation')
        if not f['source_url'].startswith('https://'):raise ValueError('HTTPS fixture source required')
        if (p['ev'],p['dep'],p['lig'],timestamp(p['tarih_utc']))!=(f['home'],f['away'],f['league'],start):
            raise ValueError('Prediction and official fixture disagree')
        rows.append(dict(fixture=f,prediction=p))
    try:revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    except (OSError,subprocess.CalledProcessError):revision=None
    payload=dict(spec=SPEC,recorded_at_utc=now.isoformat(),git_revision=revision,
        source_code_sha256=fingerprint(),datasets={path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
            for path in ARCHIVES.values() if Path(path).exists()},forecasts=rows,
        selection_rule='Earliest verified future fixtures with supported identities; no outcome-based replacement.',
        note='Research predictions. Two games cannot establish general accuracy. Baseline and all limited-data flags remain visible.')
    payload['payload_sha256']=hashlib.sha256(canonical(payload)).hexdigest()
    target=Path(destination);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as f:json.dump(payload,f,ensure_ascii=False,indent=2,allow_nan=False)
    return payload


def verify(record):
    payload=dict(record);expected=payload.pop('payload_sha256')
    if hashlib.sha256(canonical(payload)).hexdigest()!=expected:raise ValueError('Frozen forecast checksum mismatch')
    return record


def score(p,home,away):
    if any(type(v) is not int or v<=0 for v in (home,away)) or home==away:raise ValueError('Positive non-tied final integer scores required')
    total=home+away;margin=home-away;y=int(home>away);prob=p['ev_kazanir']
    clipped=float(np.clip(prob,1e-12,1-1e-12))
    return dict(actual_home=home,actual_away=away,winner_correct=bool((prob>=.5)==y),
        home_signed_error=float(p['ev_skor']-home),away_signed_error=float(p['dep_skor']-away),
        home_absolute_error=float(abs(p['ev_skor']-home)),away_absolute_error=float(abs(p['dep_skor']-away)),
        score_mae=float((abs(p['ev_skor']-home)+abs(p['dep_skor']-away))/2),
        total_signed_error=float(p['toplam']-total),total_absolute_error=float(abs(p['toplam']-total)),
        total_percentage_error=float(100*abs(p['toplam']-total)/total),
        margin_signed_error=float(p['fark']-margin),margin_absolute_error=float(abs(p['fark']-margin)),
        home_percentage_error=float(100*abs(p['ev_skor']-home)/home),
        away_percentage_error=float(100*abs(p['dep_skor']-away)/away),
        brier=float((prob-y)**2),log_loss=float(-(y*np.log(clipped)+(1-y)*np.log(1-clipped))),
        total_in_80=bool(p['toplam_80'][0]<=total<=p['toplam_80'][1]),
        margin_in_80=bool(p['fark_80'][0]<=margin<=p['fark_80'][1]))


def settle(record,results,now=None):
    verify(record);now=timestamp(now or pd.Timestamp.now(tz='UTC'));rows=[]
    if len({r['event_id'] for r in results})!=len(results):raise ValueError('Ambiguous result identity')
    by_id={r['event_id']:r for r in results}
    for item in record['forecasts']:
        f,p=item['fixture'],item['prediction'];r=by_id.get(f['event_id'])
        entry=dict(event_id=f['event_id'],home=f['home'],away=f['away'],status='pending')
        if r and r.get('status')=='final':
            if (r.get('home'),r.get('away'),r.get('league'))!=(f['home'],f['away'],f['league']):raise ValueError('Result identity mismatch')
            actual_start=timestamp(r['start_utc'])
            if actual_start<=timestamp(record['recorded_at_utc']):raise ValueError('Forecast was not pretipoff for actual fixture')
            if abs(actual_start-timestamp(f['start_utc']))>pd.Timedelta(hours=6):raise ValueError('Rescheduled fixture requires explicit review')
            captured=timestamp(r['captured_at'])
            if not actual_start<captured<=now or not r.get('source_url','').startswith('https://'):raise ValueError('Missing valid final-result provenance')
            entry.update(status='final',result_source=r['source_url'],captured_at=captured.isoformat(),
                **score(p,r['home_score'],r['away_score']))
        rows.append(entry)
    done=[r for r in rows if r['status']=='final']
    return dict(forecast_sha256=record['payload_sha256'],checked_at_utc=now.isoformat(),games=rows,
        settled_games=len(done),pending_games=len(rows)-len(done),
        winner_accuracy=float(np.mean([r['winner_correct'] for r in done])) if done else None,
        mean_total_absolute_error=float(np.mean([r['total_absolute_error'] for r in done])) if done else None,
        mean_score_mae=float(np.mean([r['score_mae'] for r in done])) if done else None,
        note='Percentage errors use actual positive scores as denominator. Signed errors = prediction minus actual. Winner accuracy is separate from score accuracy; this small batch is not a general benchmark.')


def generate(fixture_file,destination,limit=2):
    from .tahmin import tahmin_et
    now=pd.Timestamp.now(tz='UTC');fixtures=json.loads(Path(fixture_file).read_text())
    future=[f for f in fixtures if timestamp(f['start_utc'])>now+pd.Timedelta(minutes=10) and f['status']=='scheduled']
    future=sorted(future,key=lambda f:(timestamp(f['start_utc']),f['event_id']))[:limit]
    if len(future)!=limit:raise ValueError('Not enough verified upcoming fixtures')
    predictions=[tahmin_et(f['league'],[(f['home'],f['away'])],f['start_utc'])[0] for f in future]
    return freeze(predictions,future,destination)
