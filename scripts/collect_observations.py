"""Collect actual information-time observations for future validation, not synthetic backfill."""
import json,sys
from pathlib import Path
import pandas as pd
from bbtahmin.player_context import archive_injuries
from bbtahmin.live_feed import capture
from bbtahmin.veri.iddaa import collect as collect_odds


def main():
    captured=pd.Timestamp.now(tz='UTC');report=dict(started_at_utc=captured.isoformat(),providers={})
    for name,operation in [('nba_injuries',lambda:archive_injuries(hours=1)),('espn_scoreboard',capture),
                           ('iddaa_observed_odds',lambda:collect_odds(Path('data/observations/odds/latest.json')))]:
        try:
            value=operation()
            summary=(value if name=='nba_injuries' else
                     dict(live_games=len(value['live_games']),listed=value['total_listed']) if name=='espn_scoreboard' else
                     dict(captured_at_utc=value['captured_at_utc'],events=len(value['events']),rejected=len(value['rejected'])))
            report['providers'][name]=dict(status='captured',result=summary)
        except Exception as e:report['providers'][name]=dict(status='failed',error=type(e).__name__+': '+str(e))
    root=Path('data/observations/runs');root.mkdir(parents=True,exist_ok=True)
    path=root/(captured.strftime('%Y%m%dT%H%M%S')+'.json')
    with path.open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
    if all(v['status']=='failed' for v in report['providers'].values()):sys.exit(1)

if __name__=='__main__':main()
