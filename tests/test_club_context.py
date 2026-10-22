import pandas as pd
import pytest
from bbtahmin import club_context
from bbtahmin.veri.club_context import parse_zabiny,parse_vienna,validate


def game(**kwargs):
    return dict(event_id='a',competition='CZ_W_ZBL',gender='Women',home='ECW_892',away='ECW_891',
        tarih_utc=pd.Timestamp('2025-10-05T08:30Z'),**kwargs)


def test_zabiny_parsing_preserves_home_order_and_uses_prague_timezone():
    html='''<a class="team-game-item" href="/tym/9-a-tym/zapas/17">
    <div class="team-game-meta">Chance ŽBL - základní část</div>
    <div class="game-detail-teams-names"><strong>Žabiny Brno</strong><strong>KP Brno</strong></div>
    <span class="date-small">ne 5. 10. 2025 10:30</span>
    <span class="game-result-clean-result">93:77</span></a>'''
    r=parse_zabiny(html)[0]
    assert r['home']=='ECW_892' and r['away']=='ECW_891' and r['home_score']==93
    assert r['tarih_utc']==pd.Timestamp('2025-10-05T08:30Z')
    with pytest.raises(ValueError):parse_zabiny(html.replace('Chance ŽBL','EuroCup Women'))
    with pytest.raises(ValueError):parse_zabiny(html.replace('93:77','– : –'))


def test_vienna_uses_final_domestic_dates_without_assuming_score_orientation():
    html='''<div class="bcv-bsl-card"><a class="bcv-bsl-card-hitarea" href="https://bcvienna.com/en/schedule/?game=bsl-1"></a>
    <div class="bcv-bsl-competition-strip">win2day Basketball Superliga</div>
    <span class="bcv-bsl-status">Final</span>
    <span class="bcv-bsl-team-name">Other</span><span class="bcv-bsl-team-name">BC Vienna</span>
    <div class="bcv-bsl-meta-item">Sunday, October 18, 2026 · 6.00 PM</div>
    <span class="bcv-bsl-score">120:30</span></div>'''
    r=parse_vienna(html)[0]
    assert r['home_score'] is None and r['away_score'] is None and r['away']=='FEC_73436'
    assert r['tarih_utc']==pd.Timestamp('2026-10-18T16:00Z')
    with pytest.raises(ValueError):parse_vienna(html.replace('Final','VS'))
    with pytest.raises(ValueError):parse_vienna(html.replace('win2day Basketball Superliga','FIBA Europe Cup'))


@pytest.mark.parametrize('change',[{'gender':'Men'},{'home':'FEC_73436'},{'tarih_utc':'2099-01-01T00:00Z'},{'away':'ECW_892'}])
def test_context_validation_refuses_mixing_and_invalid_rows(change):
    r=game();r.update(change)
    with pytest.raises(ValueError):validate(pd.DataFrame([r]))


def test_auxiliary_features_never_read_same_day_or_future_results():
    g=validate(pd.DataFrame([game()]))
    when='2025-10-06T18:00Z';a=club_context.team_status(g,'ECW_892',when)
    other=game();other.update(event_id='b',tarih_utc=pd.Timestamp('2025-10-06T08:00Z'))
    future=game();future.update(event_id='c',tarih_utc=pd.Timestamp('2025-10-07T08:00Z'))
    changed=pd.concat([g,pd.DataFrame([other,future])],ignore_index=True)
    assert club_context.team_status(changed,'ECW_892',when)==a
    assert a['games_7d']==1
    unknown=club_context.team_status(g,'ECW_999',when)
    assert not unknown['observed'] and unknown['games_7d'] is None
    with pytest.raises(ValueError):club_context.team_status(g,'ECW_892','2025-10-06')


def test_auxiliary_values_always_include_availability_flags():
    g=validate(pd.DataFrame([game()]))
    target=pd.DataFrame([dict(mac_id='q',ev='ECW_892',dep='ECW_999',tarih_utc=pd.Timestamp('2025-10-06T18:00Z'))])
    row=club_context.features(target,g).iloc[0]
    assert row.aux_home_observed==1 and row.aux_away_observed==0 and row.aux_load7_diff==1
