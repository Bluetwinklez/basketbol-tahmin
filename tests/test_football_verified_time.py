import json

import pandas as pd

from bbtahmin.football import daily
from bbtahmin.football.data import row,write_json


def test_new_record_uses_independent_time_and_preserves_corrected_record(tmp_path,monkeypatch):
    root=tmp_path/'football';root.mkdir()
    history=[dict(event_id=f'h{i}',league='EN1',season='2026-27',status='final',
                  date=(pd.Timestamp('2026-04-25')+pd.Timedelta(days=i)).strftime('%Y-%m-%d'),
                  home='a' if i%2 else 'b',away='b' if i%2 else 'a',home_goals=i%4,away_goals=i%3)
             for i in range(160)]
    game=row('EN1','2026-27','2026-10-28','A','B',None,'https://example.com','2026-10-25T11:00Z')
    frame=pd.DataFrame(history+[game]);monkeypatch.setattr(daily,'load',lambda root:frame)
    write_json(root/'collection.json',dict(checked_at_utc='2026-10-25T11:00Z',errors=[]))
    output=tmp_path/'ledger'
    rejected=daily.run(root=root,output=output,now='2026-10-25T12:00Z')
    assert not rejected['forecasts'] and 'unconfirmed' in rejected['skipped'][0]['reason']
    observation=dict(event_id=game['event_id'],league='EN1',home='a',away='b',status='scheduled',
                     provider_event_id='123',
                     start_utc='2026-10-27T19:00Z',captured_at='2026-10-25T11:30Z',source_url='https://www.espn.com/soccer/game/_/gameId/1')
    write_json(tmp_path/'football_fixture_checks/latest.json',dict(spec='football-fixture-confirmation-v1',errors=[],
              reviews=[dict(status='date_conflict',event_id=game['event_id'],observation=observation)]))
    accepted=daily.run(root=root,output=output,now='2026-10-25T12:00Z')
    assert accepted['forecasts'][0]['fixture']['date']=='2026-10-27'
    record_path=next((output/'forecasts').glob('*.json'));original=record_path.read_bytes()
    reissued=dict(game,event_id='replacement-date-hash',date='2026-10-27')
    new_observation=dict(observation,event_id=reissued['event_id'],captured_at='2026-10-26T11:30Z')
    write_json(tmp_path/'football_fixture_checks/latest.json',dict(spec='football-fixture-confirmation-v1',errors=[],
              reviews=[dict(status='confirmed',event_id=reissued['event_id'],observation=new_observation)]))
    frame=pd.DataFrame(history+[reissued])
    repeated=daily.run(root=root,output=output,now='2026-10-26T12:00Z')
    assert len(list((output/'forecasts').glob('*.json')))==1
    write_json(root/'fixture_reviews.json',dict(spec='football-fixture-reviews-v1',reviews={game['event_id']:
        dict(observed_start_utc='2026-10-27T19:00Z',status='quarantined_date_conflict')}))
    frame=pd.DataFrame(history+[dict(reissued,status='final',home_goals=2,away_goals=0)])
    final=daily.run(root=root,output=output,now='2026-10-29T12:00Z')
    assert final['publisher_performance']['games']==1
    assert record_path.read_bytes()==original
