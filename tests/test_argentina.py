"""Small synthetic HTML fixtures exercise parsing, never serve as match data."""
import json
import pandas as pd
import pytest
from bbtahmin.veri import argentina as a


def official(date='24/10/2026 21:00', scores=('', ''), token='stable'):
    return f'''<table><tr class="fila-tabla-calendarios">
    <td class="celda-nombre">Argentino (J)</td><td class="resultados">{scores[0]}</td>
    <td class="resultados">{scores[1]}</td><td class="celda-nombre">Quimsa</td>
    <td class="fecha-campo"><strong>{date}</strong></td>
    <td><a href="/laliga/partido/{token}/argentino-vs-quimsa">Stats</a></td></tr></table>'''


def history(status='Final', comp='LNB', season='2022-23'):
    header='<tr><th>Fecha</th><th>Local</th><th>Pts</th><th>Pts</th><th>Visitante</th><th>Estado</th><th>Partido</th></tr>'
    rows=''.join(f'<tr><td>{day.date()}</td><td>Argentino (Junín)</td><td>80</td><td>75</td><td>Quimsa</td><td>{status}</td><td></td></tr>' for day in pd.date_range('2022-10-01',periods=60))
    return f'<input name="comp" value="{comp}"><input name="season" value="{season}"><table>{header}{rows}</table>'


def test_aliases_require_known_senior_club():
    assert a.team('Argentino J.')==a.team('ARGENTINO (J)')
    assert a.team('Atenas Cordoba')==a.team('ATENAS (C)')
    assert a.team('LANÚS')=='ARG_LNB_LANUS'
    with pytest.raises(ValueError,match='Unknown'):a.team('Atenas Women')


def test_fixture_clock_utc_and_identity_survive_postponement():
    _, first=a.parse_official(official(),2026,'2026-10-23T20:00Z','public')
    _, later=a.parse_official(official('25/10/2026 21:00'),2026,'2026-10-23T20:00Z','public')
    assert first[0]['tarih_utc']==pd.Timestamp('2026-10-25T00:00Z')
    assert first[0]['mac_id']==later[0]['mac_id']
    assert first[0]['status']=='scheduled'


def test_same_local_day_positive_score_is_never_final():
    rows,fixtures=a.parse_official(official('23/10/2026 12:00',('80','75')),2026,'2026-10-23T20:00Z','public')
    assert not rows and fixtures[0]['status']=='unverified'
    rows,_=a.parse_official(official('22/10/2026 21:00',('80','75')),2026,'2026-10-23T20:00Z','public')
    assert rows[0]['ev_skor']==80 and rows[0]['dep_skor']==75


def test_publisher_history_day_precision_and_schema_guards():
    rows=a.parse_history(history(),2022,'2026-10-23T20:00Z','publisher')
    assert len(rows)==60 and {r['date_precision'] for r in rows}=={'day'}
    assert rows[0]['tarih_utc']==pd.Timestamp('2022-10-01T03:00Z')
    for page in (history(comp='LigaArgentina'),history(season='2021-22'),history(status='En juego')):
        with pytest.raises(ValueError):a.parse_history(page,2022,'2026-10-23T20:00Z','publisher')


def test_persisted_scores_conflicts_fail_instead_of_overwrite():
    rows,_=a.parse_official(official('22/10/2026 21:00',('80','75')),2026,'2026-10-23T20:00Z','public')
    previous=pd.DataFrame(rows)
    assert len(a.merge_results(previous,rows))==1
    with pytest.raises(ValueError,match='Conflicting'):a.merge_results(previous,[dict(rows[0],ev_skor=81)])


def test_invalid_publisher_score_is_quarantined_with_provenance():
    rejected=[]
    page=history().replace('<td>80</td>','<td>0</td>',1)
    rows=a.parse_history(page,2022,'2026-10-23T20:00Z','publisher',rejected)
    assert len(rows)==59 and len(rejected)==1
    assert rejected[0]['home_score']=='0' and rejected[0]['source_url']=='publisher'


def test_day_only_history_cannot_settle_exact_time_forecasts(tmp_path,monkeypatch):
    from bbtahmin.daily import source_facts
    monkeypatch.chdir(tmp_path)
    root=tmp_path/'data/competitions';root.mkdir(parents=True)
    rows=a.parse_history(history(),2022,'2026-10-23T20:00Z','publisher')
    pd.DataFrame(rows).to_parquet(root/'ARG_LNB.parquet')
    _,fixtures=a.parse_official(official(),2026,'2026-10-23T20:00Z','public')
    pd.DataFrame(fixtures).to_parquet(root/'ARG_LNB_fixtures.parquet')
    future,finals=source_facts('ARG_LNB')
    assert len(future)==1 and not finals


def test_promoted_club_is_not_selected_despite_five_current_games():
    from bbtahmin.quality import assess
    p=dict(lig='ARG_LNB',ev='ARG_LNB_LANUS',dep='ARG_LNB_ATENAS',tarih_utc='2026-10-25T00:00Z',
           ev_kazanir=.7,ev_skor=90,dep_skor=80,toplam=170,fark=10,toplam_80=[140,200],fark_80=[-5,25],
           prior_season_missing=['ARG_LNB_LANUS'])
    rows=[dict(lig='ARG_LNB',sezon='2026-27',ev=p['ev'],dep=p['dep'],tarih_utc=pd.Timestamp(day,tz='UTC'))
          for day in pd.date_range('2026-10-01',periods=6)]
    quality=assess(p,pd.DataFrame(rows),now='2026-10-23T20:00Z')
    assert not quality['diagnostic_gate_passed']
    assert any('promoted-team' in issue for issue in quality['blocking_issues'])


def test_source_failure_preserves_results_and_fixtures(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    root=tmp_path/'data/competitions';root.mkdir(parents=True)
    rows,_=a.parse_official(official('22/10/2026 21:00',('80','75')),2026,'2026-10-23T20:00Z','public')
    pd.DataFrame(rows).to_parquet(root/'ARG_LNB.parquet')
    fixture=root/'ARG_LNB_fixtures.parquet';fixture.write_bytes(b'prior snapshot')
    def unavailable(*args,**kwargs):raise ValueError('source unavailable')
    monkeypatch.setattr(a,'fetch',unavailable)
    result=a.collect(first=2026,last=2026)
    assert len(result)==1 and fixture.read_bytes()==b'prior snapshot'
    report=json.loads((tmp_path/'docs/kanit/competitions/ARG_LNB_collection.json').read_text())
    assert report['errors'] and not report['official_current_refresh']


def test_independent_model_route(monkeypatch):
    from bbtahmin import regional_model
    from bbtahmin.tahmin import _tahmin_et
    from bbtahmin.daily import LEAGUES
    monkeypatch.setattr(regional_model,'predict',lambda *args:dict(route=args))
    assert _tahmin_et('ARG_LNB',[('ARG_LNB_ARGENTINO','ARG_LNB_QUIMSA')],'2026-10-25T00:00Z')[0]['route'][0]=='ARG_LNB'
    assert 'ARG_LNB' in LEAGUES


def test_published_argentina_forecasts_reused_in_new_local_ledger(tmp_path,monkeypatch):
    from bbtahmin import daily
    def no_recalculation(*args,**kwargs):raise AssertionError('Frozen forecast must be reused')
    monkeypatch.setattr('bbtahmin.tahmin.tahmin_et',no_recalculation)
    from pathlib import Path
    originals={p:p.read_bytes() for p in Path('data/argentina_ledger/forecasts').glob('*.json')}
    assert len(originals)==10
    report=daily.run(['ARG_LNB'],str(tmp_path/'new-ledger'),hours=168,now='2026-10-23T21:00Z')
    assert len(report['upcoming'])==10
    assert all(row['record_status']=='existing_immutable' for row in report['upcoming'])
    assert all(p.read_bytes()==raw for p,raw in originals.items())
