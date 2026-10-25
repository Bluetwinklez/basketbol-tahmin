"""Fill exact existing fixture dates using licensed, independently checked scores.

Scores come from CC BY-SA Wikipedia matrices. Existing CC0 fixture dates must
also match a unique publisher final and its score. No dates or scores guessed;
conflicts retain the entire prior league overlay. Originals remain untouched.
"""
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from bbtahmin.football.data import ROOT,key,load,write_json
from bbtahmin.football.licensed import merge
from bbtahmin.football.storage import save
from bbtahmin.quality import timestamp


WIKI_ALIASES={
    'DE1':{'Mainz 05':'Mainz','SC Paderborn':'SC Paderborn 07','Union Berlin':'1. FC Union Berlin'},
    'EN1':{'Bournemouth':'AFC Bournemouth'},'ES1':{'Deportivo A Coruña':'Deportivo','Athletic Bilbao':'Athletic Club'},
    'FR1':{'Auxerre':'AJ Auxerre','Le Havre':'Le Havre AC','Monaco':'AS Monaco','Rennes':'Stade Rennais'},
    'IT1':{'Inter Milan':'Internazionale','Roma':'AS Roma'},
    'NL1':{'AZ':'AZ Alkmaar','Ajax':'Ajax Amsterdam','Cambuur':'SC Cambuur','Feyenoord':'Feyenoord Rotterdam',
           'Groningen':'FC Groningen','NEC':'NEC Nijmegen','Twente':'FC Twente','Utrecht':'FC Utrecht'},
    'PT1':{'Estoril Praia':'Estoril','Estrela da Amadora':'Estrela','Famalicão':'FC Famalicao','Nacional':'C.D. Nacional','Porto':'FC Porto'},
    'TR1':{'Amedspor':'Amed SFK','Başakşehir':'Istanbul Basaksehir','Erzurumspor':'Erzurum BB','Gaziantep':'Gaziantep FK','Rizespor':'Caykur Rizespor','Çorum':'Çorum FK'}}


def build(frame,source,reviews,now,aliases=None):
    now=timestamp(now)
    frame=frame.astype(object).where(pd.notna(frame),None)
    if source['license']!='CC-BY-SA-4.0' or timestamp(source['captured_at_utc'])>now:
        raise ValueError('Valid licensed source capture required')
    lookup={}
    links={key(k):key(v) for k,v in {**(aliases or {}),**WIKI_ALIASES.get(source['league'],{})}.items()}
    for r in source['rows']:
        pair=tuple(links.get(key(r[k]),key(r[k])) for k in ('home_name','away_name'))
        if pair in lookup:raise ValueError('Ambiguous licensed score pair')
        lookup[pair]=r
    indexed={r['event_id']:r for r in frame.to_dict('records')}
    rows=[];skipped=[]
    for review in reviews:
        if review['status'] not in ('confirmed','date_conflict'):continue
        observation=review['observation']
        if observation['league']!=source['league'] or observation['status']!='final':continue
        original=indexed.get(review['event_id'])
        if original is None or original['season']!=source['season']:continue
        actual_date=observation['start_utc'][:10]
        if actual_date>=now.strftime('%Y-%m-%d'):continue
        wiki=lookup.get((key(observation['home_name']),key(observation['away_name'])))
        if wiki is None:
            skipped.append(dict(event_id=original['event_id'],reason='No exact licensed club/score pair'));continue
        if [wiki['home_goals'],wiki['away_goals']]!=[observation['home_score'],observation['away_score']]:
            raise ValueError(f'Licensed/publisher score conflict: {original["event_id"]}')
        if not timestamp(observation['start_utc'])<timestamp(observation['captured_at'])<=now:
            raise ValueError('Independent date evidence invalid')
        if original['status']=='final':
            if [int(original['home_goals']),int(original['away_goals'])]!=[wiki['home_goals'],wiki['away_goals']]:
                raise ValueError('Existing archive final conflicts; explicit review required')
            if actual_date==original['date']:continue
        rows.append(dict(original,status='final',date=actual_date,original_date=original['date'],
                         date_correction_verified=actual_date!=original['date'],home_goals=wiki['home_goals'],away_goals=wiki['away_goals'],
                         captured_at_utc=source['captured_at_utc'],source_url=source['source_url'],
                         source_kind='wikipedia_CC_BY_SA_independently_checked',license=source['license'],
                         attribution='Wikipedia contributors; extracted and matched by bbtahmin',
                         license_url=source['license_url'],source_sha256=source['sha256'],
                         fixture_verification_url=observation['source_url'],actual_start_utc=observation['start_utc']))
    merge(frame.to_dict('records'),rows)
    return rows,skipped


def main():
    now=pd.Timestamp.now(tz='UTC');frame=load(include_licensed=False)
    before=load();before_final_ids=set(before.loc[before.status=='final','event_id'])
    checks=json.loads(Path('data/football_fixture_checks/latest.json').read_text(encoding='utf8'))
    aliases=json.loads(Path('data/football/provider_aliases.json').read_text(encoding='utf8'))['aliases']
    if now-timestamp(checks['checked_at_utc'])>pd.Timedelta(hours=24):raise ValueError('Refresh independent fixture checks')
    reports=[];errors=[]
    refresh_status=ROOT/'licensed_source_refresh.json'
    if refresh_status.exists():
        status=json.loads(refresh_status.read_text(encoding='utf8'))
        errors.extend(dict(league=r['league'],reason=r['error'],retained_previous=True)
                      for r in status['results'] if 'error' in r)
    for path in sorted(Path('.runtime/wiki_football').glob('*.json')):
        if path.name=='report.json':continue
        source=json.loads(path.read_text(encoding='utf8'))
        try:
            if now-timestamp(source['captured_at_utc'])>pd.Timedelta(hours=24):raise ValueError('Refresh licensed score source')
            from inspect_wikipedia_football import parse
            raw_path=Path('data/raw/domestic_feeds')/(hashlib.sha256(source['source_url'].encode()).hexdigest()+'.bin')
            raw=raw_path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=source['sha256'] or parse(raw)!=source['rows']:
                raise ValueError('Licensed score extraction no longer matches its captured source')
            rows,skipped=build(frame,source,checks['reviews'],now,aliases)
            if rows:
                # Preserve attribution-licensed derivatives apart from CC0 base.
                save(rows,source['league'],source['season'],ROOT/'licensed_overlays',dict(
                    license='CC-BY-SA-4.0',attribution='Wikipedia contributors',source_url=source['source_url']))
                evidence=ROOT/'licensed_source_evidence'/(source['sha256']+'.json.gz')
                evidence.parent.mkdir(parents=True,exist_ok=True)
                if not evidence.exists():evidence.write_bytes(gzip.compress(json.dumps(dict(source,
                    training_imported=True,matched_fixture_ids=[r['event_id'] for r in rows],
                    note='Only the listed fixture IDs were independently matched; matrix dates remain unavailable.'),ensure_ascii=False).encode(),mtime=0))
            reports.append(dict(league=source['league'],added_candidates=len(rows),skipped=skipped,source_url=source['source_url']))
        except Exception as exc:errors.append(dict(league=source['league'],reason=f'{type(exc).__name__}: {exc}',retained_previous=True))
    # Verify the combined archive and expose all remaining missing sources.
    combined=load()
    registry_path=ROOT/'fixture_reviews.json'
    registry=json.loads(registry_path.read_text(encoding='utf8')) if registry_path.exists() else dict(spec='football-fixture-reviews-v1',reviews={})
    for row in combined.loc[combined.get('date_correction_verified',pd.Series(False,index=combined.index)).fillna(False).astype(bool)].to_dict('records'):
        registry['reviews'].setdefault(row['event_id'],dict(league=row['league'],home=row['home'],away=row['away'],
            original_date=row['original_date'],observed_start_utc=row['actual_start_utc'],source_url=row['fixture_verification_url'],
            checked_at_utc=now.isoformat(),status='quarantined_date_conflict',
            note='Training date independently checked against licensed score; original forecast settlement still requires timing review.'))
    write_json(registry_path,registry)
    report=dict(checked_at_utc=now.isoformat(),leagues=reports,errors=errors,
                licensed_finals=int((combined.source_kind=='wikipedia_CC_BY_SA_independently_checked').sum()),
                new_unique_finals=len(set(combined.loc[combined.status=='final','event_id'])-before_final_ids),
                note='Partial CC BY-SA supplement; original CC0 archives and frozen forecasts retained. Same-day, unknown date, name mismatch and conflicting results are excluded; calendar completeness is unverified.')
    write_json(ROOT/'licensed_collection.json',report)
    print(json.dumps(report,ensure_ascii=False))
    return 1 if errors else 0


if __name__=='__main__':raise SystemExit(main())
