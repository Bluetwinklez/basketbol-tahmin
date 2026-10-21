import numpy as np
import pytest
from bbtahmin.elo import expected,update
from bbtahmin.odds import decimal_probability,american_decimal,no_vig,simulate
from bbtahmin.veri.teams import team_code
def test_expected_and_zero_sum():
    assert expected(1500,1500)==.5
    assert expected(1600,1500)> .5
    h,a=update(1500,1500,90,80,k=20)
    assert h==1510 and a==1490
    h,a=update(1600,1400,70,90,k=30,advantage=75,mov=True)
    assert h+a==pytest.approx(3000)
@pytest.mark.parametrize('odds,decimal',[(150,2.5),(-200,1.5),(100,2),(-100,2)])
def test_american(odds,decimal):
    assert american_decimal(odds)==decimal
def test_vig():
    assert decimal_probability(2)==.5
    assert no_vig(1.91,1.91).sum()==pytest.approx(1)
    assert no_vig(1.91,1.91)[0]==pytest.approx(.5)
@pytest.mark.parametrize('name,code',[('Golden State','GSW'),('New Jersey Nets','BRK'),('Seattle SuperSonics','OKC'),
    ('Charlotte Bobcats','CHO'),('New Orleans Hornets','NOP'),('LAClippers','LAC')])
def test_team_mapping(name,code):
    assert team_code(name)==code
def test_unknown_team():
    with pytest.raises(ValueError):team_code('Unknown')
def test_fixed_and_kelly():
    for method in ['fixed','kelly']:
        result=simulate([.8,.2],[1,0],[2.,2.],[2.,2.],.05,method)
        assert result['bets']==2 and result['roi']>0 and result['max_drawdown']==0

def test_official_nba_mov_multiplier():
    h,a=update(1500,1500,104,100,k=20,mov=True)
    expected_delta=20*(7**.8)/7.5*.5
    assert h==pytest.approx(1500+expected_delta)
    assert a==pytest.approx(1500-expected_delta)
