"""Fixed four-result refresh audit; retrospective only, never model selection."""
import hashlib
from pathlib import Path
from bbtahmin.football.data import load, write_json
from bbtahmin.football.challenger import VARIANTS, fit
from bbtahmin.football.model import score, metrics
from evaluate_football_ensemble import reliability

EVENTS = ('AR1_c710fd4d774c4f6c8ba6dbfa','AR1_4742b94ce5bd46c373446729',
          'AR2_ebe09e3c71e52974700fa54e','AR2_69975b82196d732b04c0787a')


def main():
    frame=load(include_licensed=False)
    target=frame[frame.event_id.isin(EVENTS)].sort_values('event_id')
    if len(target)!=len(EVENTS):raise ValueError('Fixed audit cohort missing or duplicated')
    predictions=[];summaries={}
    for variant in VARIANTS:
        cohort=[]
        for game in target.itertuples():
            history=frame[(frame.league==game.league)&(frame.date<game.date)]
            p=fit(history,game.league,game.date,variant).predict(game.home,game.away)
            result=score(p,int(game.home_goals),int(game.away_goals))
            item=dict(event_id=game.event_id,variant=variant,cutoff=game.date,prediction=p,result=result)
            cohort.append(item);predictions.append(item)
        m=metrics([x['result'] for x in cohort]);m['coverage']=1.0
        m['calibration']={k:reliability([x['prediction']['probabilities'][k] for x in cohort],
            [x['result']['actual_outcome']==k for x in cohort]) for k in ('home','draw','away')}
        for line in ('1.5','2.5','3.5'):
            m['calibration']['over_'+line]=reliability([x['prediction']['over'][line] for x in cohort],
                [x['result']['actual_home']+x['result']['actual_away']>float(line) for x in cohort])
        m['calibration']['both_teams_score']=reliability([x['prediction']['both_teams_score'] for x in cohort],
            [min(x['result']['actual_home'],x['result']['actual_away'])>0 for x in cohort])
        summaries[variant]=m
    report=dict(cohort=list(EVENTS),summaries=summaries,predictions=predictions,
        simple_baselines=dict(always_home=float((target.home_goals>target.away_goals).mean()),
            always_under_2_5=float((target.home_goals+target.away_goals<2.5).mean()),
            always_btts_no=float(((target.home_goals==0)|(target.away_goals==0)).mean())),
        input_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('data/football').glob('AR[12]_20*.json.gz'))},
        limitations='Four publisher CC-BY-SA finals, retrospective post-result audit; whole target day withheld. Historical publication availability unknown. No tuning, policy promotion, significance or prospective accuracy claim. Not evidence of data-only improvement.',
        original_forecasts_changed=False)
    write_json('docs/kanit/football/argentina_refresh_20261028.json',report)
    print({k:dict(games=v['games'],winner_accuracy=v['winner_accuracy']) for k,v in summaries.items()})


if __name__=='__main__':main()
