"""CC BY-SA score overlays, independently checked against exact dated fixtures."""
from ..quality import timestamp


def merge(base,overlays):
    indexed={r['event_id']:r for r in base}
    licensed_ids=set()
    if len(indexed)!=len(base):raise ValueError('Duplicate base fixture identity')
    for row in overlays:
        previous=indexed.get(row['event_id'])
        if previous is not None and any(row[k]!=previous[k] for k in ('league','season','home','away')):
            raise ValueError('Licensed overlay requires an exact existing fixture identity')
        if previous is not None and row['date']!=previous['date'] and not (row.get('date_correction_verified') is True and row.get('original_date')==previous['date']):
            raise ValueError('Explicit independently verified original-date correction required')
        if (row.get('license')!='CC-BY-SA-4.0' or row.get('source_kind')!='wikipedia_CC_BY_SA_independently_checked'
                or not row.get('source_url','').startswith('https://en.wikipedia.org/wiki/')
                or not row.get('fixture_verification_url','').startswith('https://www.espn.com/soccer/game/')
                or not row.get('attribution') or not row.get('source_sha256')):
            raise ValueError('Licensed overlay provenance missing')
        start=timestamp(row['actual_start_utc']);captured=timestamp(row['captured_at_utc'])
        if not start<captured or start.strftime('%Y-%m-%d')!=row['date']:
            raise ValueError('Licensed overlay date evidence mismatch')
        if row['status']!='final' or any(type(row[k]) is not int or not 0<=row[k]<=30 for k in ('home_goals','away_goals')):
            raise ValueError('Invalid licensed final')
        licensed_ids.add(row['event_id'])
        if previous is not None and previous['status']=='final':
            if any(row[k]!=previous[k] for k in ('home_goals','away_goals')):
                raise ValueError('Licensed score conflicts with an existing final')
            if row['date']!=previous['date']:indexed[row['event_id']]=row
        else:indexed[row['event_id']]=row
    # A later community calendar may omit or regenerate a date-hashed id.
    # Retain independently checked finals and reconcile only exact dated club
    # identities backed by that final. Never silently merge conflicting scores.
    natural={}
    for row in indexed.values():
        key=tuple(row[k] for k in ('league','season','date','home','away'))
        natural.setdefault(key,[]).append(row)
    result=[]
    for group in natural.values():
        if len(group)==1:result.extend(group);continue
        backed=[r for r in group if r['event_id'] in licensed_ids]
        if len(backed)!=1:raise ValueError('Ambiguous duplicate fixture without a licensed identity bridge')
        chosen=backed[0]
        if any(r['status']=='final' and any(r[k]!=chosen[k] for k in ('home_goals','away_goals')) for r in group):
            raise ValueError('Reissued community final conflicts with licensed evidence')
        result.append(dict(chosen,event_aliases=sorted({r['event_id'] for r in group if r['event_id']!=chosen['event_id']})))
    return result
