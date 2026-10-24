"""Audit screenshot coverage and evaluate BR2 on identical earlier-only cohorts."""
import gzip
import json
from pathlib import Path
from bbtahmin.football.data import load, write_json, key
from bbtahmin.football.challenger import compare, VARIANTS, fit
from evaluate_football_ensemble import reliability


def main():
    frame=load(); br=frame.loc[frame.league=='BR2']; report=compare(br,'2024'); rows=report.pop('predictions')
    report['calibration']={}
    for v in VARIANTS:
        items=[x for x in rows if x['variant']==v]
        report['calibration'][v]={}
        for outcome in ('home','draw','away'):
            report['calibration'][v][outcome]=reliability([x['prediction']['probabilities'][outcome] for x in items],[x['result']['actual_outcome']==outcome for x in items])
        for line in ('1.5','2.5','3.5'):
            report['calibration'][v]['over_'+line]=reliability([x['prediction']['over'][line] for x in items],[x['result']['actual_home']+x['result']['actual_away']>float(line) for x in items])
        report['calibration'][v]['both_teams_score']=reliability([x['prediction']['both_teams_score'] for x in items],[min(x['result']['actual_home'],x['result']['actual_away'])>0 for x in items])
    pairs=[('CO2','Bogotá','Real Santander'),('CO2','Real Cundinamarca','Independiente Yumbo'),('USL1','Portland Hearts of Pine','Charlotte Independence'),('USLC','Loudoun United','Brooklyn'),('SV1','Alianza','Metapán'),('SV1','CD Águila','CD FAS'),('HN1','CD Choloma','Genesis PN'),('BO1','San Antonio Bulo Bulo','Real Potosí'),('BR2','CRB AL','Londrina PR')]
    coverage=[]
    for league,home,away in pairs:
        item=dict(league=league,home=home,away=away,status='unsupported',reason='No licensed archive integrated for this competition')
        if league=='BR2':
            p=fit(br,league,'2026-10-25','ensemble').predict(home,away)
            item.update(status='blocked_stale_history',reason='No 2026 source season; not a usable current forecast',prior_team_games=p['prior_team_games'],issues=p['issues'])
        coverage.append(item)
    target_games=br.loc[(br.season=='2024') & (br.status=='final')]
    report['simple_baselines']={'always_home_accuracy':float((target_games.home_goals>target_games.away_goals).mean()),'always_under_2_5_accuracy':float(((target_games.home_goals+target_games.away_goals)<=2).mean()),'always_btts_no_accuracy':float(((target_games.home_goals==0)|(target_games.away_goals==0)).mean())}
    report.update(requested_coverage=coverage,imported_finals=len(br),source_kind='community_CC0_not_official',new_current_forecasts=0)
    target=Path('docs/kanit/requested_football');target.mkdir(parents=True,exist_ok=True)
    write_json(target/'evaluation.json',report)
    (target/'paired_results.json.gz').write_bytes(gzip.compress(json.dumps(rows,ensure_ascii=False).encode(),mtime=0))
    print(json.dumps(report['summaries'],indent=2))


if __name__=='__main__':main()
