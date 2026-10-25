"""Record and settle versioned paired candidates without changing production."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from threadpoolctl import threadpool_limits

from bbtahmin.daily import source_facts
from bbtahmin.football.data import load,write_json
from bbtahmin.football.health import assess
from bbtahmin.prospective import dataset_hashes,fingerprint
from bbtahmin.quality import timestamp
from bbtahmin.shadow import checked,evaluate,forecast_path,freeze,register
from bbtahmin import shadow_models
from bbtahmin.prior_policy import calibrated

BASKETBALL=('E','KBL','ABA','ECW','FEC','UKR','TR_BSL','ARG_LNB')
POLICY=dict(version='paired-shadow-v1',basketball_reference='unchanged runtime model',
            basketball_candidate='frozen earlier-OOS league pipeline and calibration',
            basketball_leagues=BASKETBALL,football_reference='baseline',football_candidate='frozen earlier-OOS league pipeline and calibration',
            confidence_threshold=.65,minimum_review_games=100,minimum_review_days=20,
            note='Independent future experiment, fixed before outcomes; historical candidate reports cannot promote production. Skipped source/history fixtures are explicitly counted outside the frozen cohort.')


def run(root='data/improvement_shadow',record=True):
    from bbtahmin.tahmin import tahmin_et
    from bbtahmin.football.challenger import fit
    registry_path=Path('data/improvement_policy/current.json');root=Path(root)
    if record:
        registry=json.loads(registry_path.read_text(encoding='utf8'))
        directory,identity=register(root,dict(POLICY,frozen_pipelines=registry,
            cycle_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        write_json(root/'active.json',dict(spec='active-paired-forward-v1',experiment_id=identity))
    else:
        # Status checks on another host must not create a new runtime epoch or
        # supersede the canonical scheduled experiment merely by checking it.
        pointer=root/'active.json'
        prior=json.loads((pointer if pointer.exists() else root/'latest.json').read_text(encoding='utf8'))
        identity=prior['experiment_id'];directory=root/'experiments'/identity
        if len(identity)!=64 or any(c not in '0123456789abcdef' for c in identity) or not (directory/'protocol.json').exists():
            raise ValueError('Valid active paired experiment required for settlement')
    clock=pd.Timestamp.now(tz='UTC');results=[];skipped=[];new=0;existing=0
    hashes=dataset_hashes()
    hashes.update({p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('data/football').rglob('*.json.gz')})
    hashes.update({p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('data/football').glob('*.json')})
    hashes[registry_path.as_posix()]=hashlib.sha256(registry_path.read_bytes()).hexdigest()
    code_hash=fingerprint()
    def verify_snapshot():
        if fingerprint()!=code_hash:raise ValueError('Code changed during cycle')
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in hashes.items()):
            raise ValueError('Training data changed during cycle')
    # Dataset hashes cover the complete source inputs; no archive may mutate
    # concurrently with this cycle. CI serializes refresh before this command.
    with threadpool_limits(limits=1):
        for code in BASKETBALL:
            try: fixtures,finals=source_facts(code);results.extend(finals)
            except Exception as exc:skipped.append(dict(league=code,reason=str(exc)));continue
            if not record:continue
            for fixture in sorted(fixtures,key=lambda f:(f['start_utc'],f['event_id'])):
                if not clock<timestamp(fixture['start_utc'])<=clock+pd.Timedelta(days=7):continue
                try:
                    # Reuse the immutable pair; do not refit it on every check.
                    saved=forecast_path(directory,fixture)
                    if saved.exists():checked(json.loads(saved.read_text(encoding='utf8')));existing+=1;continue
                    captured=timestamp(fixture['captured_at'])
                    if not captured<=clock or clock-captured>pd.Timedelta(hours=24):raise ValueError('Refresh stale/future fixture confirmation')
                    if fixture['status']!='scheduled':raise ValueError('Fixture not scheduled')
                    reference=tahmin_et(code,[(fixture['home'],fixture['away'])],fixture['start_utc'])[0]
                    candidate=shadow_models.slow_form(code,fixture,clock,registry['policies']['basketball'][code])
                    recorded=pd.Timestamp.now(tz='UTC')
                    pair=dict(reference=shadow_models.basketball(reference,recorded),candidate=dict(candidate,information_cutoff_utc=recorded.isoformat()))
                    verify_snapshot()
                    freeze(directory,identity,fixture,pair,hashes,now=recorded);new+=1
                except Exception as exc:skipped.append(dict(league=code,event_id=fixture['event_id'],reason=f'{type(exc).__name__}: {exc}'))
        facts_path=Path('data/football_fixture_checks/latest.json')
        if facts_path.exists():
            confirmations=json.loads(facts_path.read_text(encoding='utf8'))
            skipped.extend(confirmations.get('errors',[]));frame=load();models={}
            bad_leagues={e['league'] for e in confirmations.get('errors',[]) if e.get('league')}
            known_future={r['event_id'] for r in confirmations['reviews'] if r['status'] in ('confirmed','date_conflict') and
                          r['observation']['status']=='scheduled' and clock<timestamp(r['observation']['start_utc']) and
                          timestamp(r['observation']['captured_at'])<=clock and clock-timestamp(r['observation']['captured_at'])<=pd.Timedelta(hours=24)}
            health_frame=frame.loc[~frame.event_id.isin(known_future)]
            quarantine_path=Path('data/football/fixture_reviews.json')
            quarantine=json.loads(quarantine_path.read_text(encoding='utf8'))['reviews'] if quarantine_path.exists() else {}
            for review in confirmations['reviews']:
                if review['status'] not in ('confirmed','date_conflict'):continue
                fixture=review['observation'];code=fixture['league']
                if fixture['status']=='final':results.append(fixture);continue
                if not record or not clock<timestamp(fixture['start_utc'])<=clock+pd.Timedelta(days=7):continue
                try:
                    if code in bad_leagues:raise ValueError('Independent fixture refresh incomplete')
                    if fixture['event_id'] in quarantine:raise ValueError('Quarantined fixture conflict')
                    saved=forecast_path(directory,fixture)
                    if saved.exists():checked(json.loads(saved.read_text(encoding='utf8')));existing+=1;continue
                    archive=frame.loc[frame.event_id==fixture['event_id']]
                    if len(archive)!=1:raise ValueError('Unique archive fixture required')
                    verified=dict(archive.iloc[0].to_dict(),date=fixture['start_utc'][:10])
                    health=assess(health_frame,verified,clock)
                    if not health['diagnostic_gate_passed']:raise ValueError('; '.join(health['blocking_issues']))
                    policy=registry['policies']['football'][code]
                    year=timestamp(fixture['start_utc']).year if timestamp(fixture['start_utc']).month>=7 else timestamp(fixture['start_utc']).year-1
                    if year-int(policy['prior_season'][:4])!=1:raise ValueError('Frozen challenger pipeline prior season is not adjacent')
                    if code not in models:
                        from bbtahmin.football.model import GoalModel
                        variant=policy['variant'];cutoff=clock.strftime('%Y-%m-%d')
                        candidate=(GoalModel(frame,code,cutoff,half_life=90.) if variant=='recency90' else
                                   GoalModel(frame,code,cutoff,shrinkage=16.) if variant=='shrinkage16' else fit(frame,code,cutoff,variant))
                        models[code]=dict(reference=fit(frame,code,cutoff,'baseline'),candidate=candidate)
                    predictions={name:model.predict(fixture['home'],fixture['away']) for name,model in models[code].items()}
                    if any(p['issues'] for p in predictions.values()):raise ValueError('Insufficient team history')
                    recorded=pd.Timestamp.now(tz='UTC')
                    verify_snapshot()
                    normalized={name:shadow_models.football(p,fixture,recorded,health) for name,p in predictions.items()}
                    normalized['candidate']['probabilities']=calibrated(normalized['candidate']['probabilities'],policy['temperature']).tolist()
                    normalized['candidate']['eligible']=bool(health['diagnostic_gate_passed'] and max(normalized['candidate']['probabilities'])>=.65)
                    normalized['candidate']['frozen_pipeline_policy']=policy
                    freeze(directory,identity,fixture,normalized,hashes,now=recorded)
                    new+=1
                except Exception as exc:skipped.append(dict(league=code,event_id=fixture['event_id'],reason=str(exc)))
        else: skipped.append(dict(sport='football',reason='No independent fixture confirmations; run confirm_football_fixtures.py'))
    checks=[]
    for experiment in sorted((root/'experiments').iterdir()):
        if experiment.is_dir():checks.append(dict(experiment_id=experiment.name,**evaluate(experiment,results,active=experiment.name==identity)))
    report=dict(checked_at_utc=pd.Timestamp.now(tz='UTC').isoformat(),experiment_id=identity,new_pairs=new,
                reused_pairs=existing,skipped=skipped,experiments=checks,production_default_changed=False)
    write_json(root/'latest.json',report)
    save=root/'checks'/(pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    write_json(save,report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--settle-only',action='store_true')
    parser.add_argument('--output',default='data/improvement_shadow');args=parser.parse_args()
    report=run(args.output,not args.settle_only)
    print(json.dumps(dict(new_pairs=report['new_pairs'],reused_pairs=report['reused_pairs'],skipped=len(report['skipped']),
                          settled=sum(r['settled_games'] for r in report['experiments']))))
