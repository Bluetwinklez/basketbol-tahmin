"""Offline regression tests, runnable with unittest as well as pytest."""
import copy
import csv
import io
import json
import math
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from bbtahmin.archive_checks import reconcile_results
from bbtahmin.football.challenger import fit, compare
from bbtahmin.football.data import row, write_json
from bbtahmin.football.distributions import poisson
from bbtahmin.football.exports import export_csv, markdown
from bbtahmin.market_estimates import total_estimates


def history():
    rows=[]
    for i in range(240):
        day=(pd.Timestamp('2024-08-01')+pd.Timedelta(days=i)).strftime('%Y-%m-%d')
        rows.append(dict(event_id=str(i),league='TR1',season='2024-25',status='final',date=day,
                         home='a' if i%2 else 'b',away='b' if i%2 else 'a',home_goals=i%4,away_goals=i%3))
    return pd.DataFrame(rows)


class SportsUpgradeTests(unittest.TestCase):
    def test_poisson_matches_closed_form_and_extreme_tail(self):
        self.assertAlmostEqual(float(poisson.pmf([0],2)[0]),math.exp(-2),places=14)
        self.assertAlmostEqual(poisson.sf(1,2),1-3*math.exp(-2),places=14)
        self.assertGreater(poisson.sf(3,.2),0)
        self.assertEqual(poisson.ppf(.9,2),4)

    def test_candidates_have_coherent_goal_distributions(self):
        for variant in ('baseline','opponent','opponent_dc'):
            p=fit(history(),'TR1','2025-06-01',variant).predict('a','b')
            self.assertAlmostEqual(sum(p['probabilities'].values()),1,places=12)
            self.assertTrue(all(0<=v<=1 for v in p['probabilities'].values()))
            self.assertTrue(0<=p['over']['3.5']<=p['over']['2.5']<=p['over']['1.5']<=1)
            self.assertTrue(0<=p['both_teams_score']<=1)

    def test_candidate_excludes_future_same_day_and_foreign_results(self):
        h=history();extra=h.iloc[:10].copy();extra['date']='2025-06-01';extra['home_goals']=29
        foreign=h.copy();foreign['league']='EN1';foreign['away_goals']=29
        for variant in ('baseline','opponent','opponent_dc'):
            original=fit(h,'TR1','2025-06-01',variant).predict('a','b')
            changed=fit(pd.concat([h,extra,foreign]),'TR1','2025-06-01',variant).predict('a','b')
            self.assertEqual(original,changed)

    def test_unknown_team_has_diagnostics_and_never_false_validation(self):
        p=fit(history(),'TR1','2025-06-01','opponent_dc').predict('unknown','a')
        self.assertTrue(p['issues']);self.assertFalse(p['recommendation_validated'])

    def test_comparison_uses_identical_cohorts(self):
        h=history();target=h.iloc[:3].copy();target['date']='2025-08-01';target['season']='2025-26';target['event_id']=['t1','t2','t3']
        result=compare(pd.concat([h,target]),'2025-26')
        self.assertFalse(result['default_changed'])
        self.assertEqual({v['games'] for v in result['summaries'][0]['candidates'].values()},{3})

    def test_basketball_duplicate_provider_rows_count_once(self):
        base=dict(mac_id='TR_BSL_B1',lig='TR_BSL',sezon='2025-26',tarih_utc='2025-10-01T00:00Z',ev='a',dep='b',ev_skor=80,dep_skor=70)
        other=dict(base,mac_id='TR_BSL_T7')
        result=reconcile_results(pd.DataFrame([base,other]))
        self.assertEqual(result.mac_id.tolist(),['TR_BSL_B1'])
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            reconcile_results(pd.DataFrame([base,dict(other,ev_skor=81)]))

    def test_reverse_fixture_is_distinct(self):
        base=dict(mac_id='one',lig='TR_BSL',sezon='2025-26',tarih_utc='2025-10-01T00:00Z',ev='a',dep='b',ev_skor=80,dep_skor=70)
        self.assertEqual(len(reconcile_results(pd.DataFrame([base,dict(base,mac_id='two',ev='b',dep='a')]))),2)

    def test_turkish_fixture_id_survives_postponement(self):
        from bbtahmin.veri.turkey import fixtures
        base=dict(id=17,league=dict(id=393,sportId=23),homeTeam=dict(id=11774,name='Home'),
                  awayTeam=dict(id=10824,name='Away'),matchDate='2026-10-25T15:00Z',liteMatchStatus='preMatch')
        original=fixtures(dict(data=[base]),2026,'2026-10-23T00:00Z')[0]
        changed=fixtures(dict(data=[dict(base,matchDate='2026-10-28T15:00Z')]),2026,'2026-10-23T00:00Z')[0]
        self.assertEqual(original['mac_id'],changed['mac_id'])
        migrated=fixtures(dict(data=[base]),2026,'2026-10-23T00:00Z',{'2026:17':'legacy-frozen-id'})[0]
        self.assertEqual(migrated['mac_id'],'legacy-frozen-id')

    def test_basketball_totals_are_monotonic_and_reject_invalid_intervals(self):
        estimates=total_estimates(dict(toplam=170,toplam_80=[145,195]))
        self.assertEqual(len(estimates),3)
        self.assertTrue(estimates[0]['over']>estimates[1]['over']>estimates[2]['over'])
        for e in estimates:self.assertAlmostEqual(e['over']+e['under'],1)
        self.assertEqual(total_estimates(dict(toplam=170,toplam_80=[180,160])),[])

    def test_frozen_football_records_survive_new_candidate(self):
        from bbtahmin.football import daily
        # Keep the immutability test's source within the new current-history
        # diagnostic window; stale-source rejection has separate coverage.
        h=history();h['date']=(pd.to_datetime(h.date)+pd.Timedelta(days=550)).dt.strftime('%Y-%m-%d')
        fixture=row('TR1','2026-27','2026-10-25','A','B',None,'source','2026-10-23T12:00Z')
        frame=pd.concat([h,pd.DataFrame([fixture])],ignore_index=True)
        with tempfile.TemporaryDirectory() as folder,patch.object(daily,'load',return_value=frame):
            root=Path(folder);write_json(root/'collection.json',dict(checked_at_utc='2026-10-23T12:00Z',errors=[]))
            daily.run(output=root/'ledger',root=root,now='2026-10-23T13:00Z')
            path=next((root/'ledger/forecasts').glob('*.json'));original=path.read_bytes()
            daily.run(output=root/'ledger',root=root,now='2026-10-24T13:00Z',model_variant='opponent_dc')
            self.assertEqual(path.read_bytes(),original)

    def test_football_exports_preserve_pending_and_escape_names(self):
        p=fit(history(),'TR1','2025-06-01').predict('a','b')
        report=dict(forecasts=[dict(fixture=dict(league='TR1',date='2026-10-25',home_name='=formula',away_name='B|C'),prediction=p,status='pending',result=None)])
        values=list(csv.DictReader(io.StringIO(export_csv(report).decode('utf-8-sig'))))
        self.assertEqual(values[0]['home'],"'=formula");self.assertEqual(values[0]['actual_home'],'')
        self.assertIn(b'B\\|C',markdown(report))

    def test_football_exports_have_real_local_http_routes(self):
        from bbtahmin.app import AppServer,AppState
        with tempfile.TemporaryDirectory() as folder:
            state=AppState(Path(folder)/'basketball');state.football_directory=str(Path(folder)/'football')
            p=fit(history(),'TR1','2025-06-01').predict('a','b')
            report=dict(forecasts=[dict(fixture=dict(league='TR1',date='2026-10-25',home_name='A',away_name='B'),prediction=p,status='pending',result=None)])
            write_json(Path(state.football_directory)/'latest.json',report)
            server=AppServer(port=0,state=state);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                for kind in ('json','csv','md'):
                    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/football/export.{kind}') as response:
                        self.assertEqual(response.status,200);self.assertIn('attachment',response.headers['Content-Disposition'])
            finally:server.shutdown();server.server_close();thread.join(2)


if __name__=='__main__':unittest.main()
