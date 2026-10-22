"""Validated, versioned imports for new official observations; no network or fuzzy IDs."""
import hashlib,json
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
from .quality import timestamp

REQUIRED={'event_id','competition','season','gender','home','away','home_score','away_score',
          'event_time','captured_at','available_at','source_url','status','date_precision','score_verified'}


def validate(records,identities,now=None):
    now=timestamp(now or pd.Timestamp.now(tz='UTC'));accepted=[];rejected=[]
    for row in records:
        try:
            if REQUIRED-set(row):raise ValueError('Missing provenance or result fields')
            r=dict(row)
            if any(not isinstance(r[k],str) or not r[k].strip() for k in ('event_id','competition','season','home','away')):
                raise ValueError('Nonempty string identities required')
            if r['gender'] not in ('Women','Men') or r['home']==r['away']:raise ValueError('Invalid gender or team')
            for team in (r['home'],r['away']):
                identity=identities.get(team,{})
                if identity.get('gender')!=r['gender'] or identity.get('category')!='senior':raise ValueError('Unverified senior team identity / gender')
            if r['status']!='final' or r['score_verified'] is not True:raise ValueError('Final and verified scores required')
            for key in ('home_score','away_score'):
                if type(r[key]) is not int or not 0<r[key]<=300:raise ValueError('Invalid final score')
            if r['home_score']==r['away_score']:raise ValueError('Tied score outside binary winner target')
            if r['date_precision'] not in ('timestamp','day'):raise ValueError('Unknown date precision')
            event,captured=timestamp(r['event_time']),timestamp(r['captured_at'])
            if event>=captured or captured>now:raise ValueError('Future result or invalid capture time')
            if r['available_at'] is not None:
                available=timestamp(r['available_at'])
                if available<event or available>captured:raise ValueError('Invalid information availability time')
                r['available_at']=available.isoformat()
            # Unknown historical publication time stays unknown; capture is the conservative availability.
            r['event_time']=event.isoformat();r['captured_at']=captured.isoformat()
            u=urlparse(r['source_url'])
            if u.scheme!='https' or not u.hostname:raise ValueError('HTTPS source URL required')
            accepted.append(r)
        except (ValueError,TypeError,KeyError) as e:rejected.append(dict(record=row,reason=str(e)))
    grouped={}
    for r in accepted:
        key=r['event_id'];previous=grouped.get(key)
        fields=('competition','season','gender','home','away','home_score','away_score','event_time')
        if previous and any(previous[k]!=r[k] for k in fields):raise ValueError('Conflicting event versions require explicit review')
        grouped.setdefault(key,r)
    return list(grouped.values()),rejected


def asof(records,when):
    cutoff=timestamp(when)
    return [r for r in records if timestamp(r['event_time'])<cutoff.floor('D') and
        timestamp(r['available_at'] or r['captured_at'])<=cutoff]


def ingest(source,identity_file,destination='data/context/imports'):
    records=[json.loads(line) for line in Path(source).read_text().splitlines() if line.strip()]
    accepted,rejected=validate(records,json.loads(Path(identity_file).read_text()))
    digest=hashlib.sha256(Path(source).read_bytes()).hexdigest();root=Path(destination)/digest
    root.mkdir(parents=True,exist_ok=True)
    report=dict(input_sha256=digest,accepted=len(accepted),rejected=len(rejected),
        historical_publication_time_unknown=sum(r['available_at'] is None for r in accepted),
        used_in_default_model=False,records=accepted,quarantine=rejected)
    for previous in Path(destination).glob('*/manifest.json'):
        for old in json.loads(previous.read_text()).get('records',[]):
            for new in accepted:
                fields=('competition','season','gender','home','away','home_score','away_score','event_time')
                if old['event_id']==new['event_id'] and any(old[k]!=new[k] for k in fields):
                    raise ValueError('Persisted observation conflict requires explicit review')
    target=root/'manifest.json'
    if target.exists():
        old=json.loads(target.read_text())
        if old!=report:raise ValueError('Existing immutable import differs')
    else:
        with target.open('x') as f:json.dump(report,f,indent=2,ensure_ascii=False)
    return report
