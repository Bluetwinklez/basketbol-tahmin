import pytest
from bbtahmin.veri.nbl import kod
from bbtahmin.takim_ad import coz

def test_kod_tarihsel_adlar():
    assert kod('South East Melbourne Phoenix') == 'SEM'
    assert kod('Melbourne United') == 'MEL'
    assert kod('The Hawks') == 'ILL' and kod('Illawarra Hawks') == 'ILL'
    assert kod('NZ Breakers') == 'NZL'
    with pytest.raises(ValueError):
        kod('Zenit')

def test_serbest_ad_cozumu():
    kodlar = {'SYD', 'ILL', 'TAS', 'MEL', 'SEM'}
    assert coz('NBL', 'Illawarra Hawks', kodlar) == 'ILL'
    assert coz('NBL', 'Sydney Kings', kodlar) == 'SYD'
    assert coz('NBL', 'JackJumpers', kodlar) == 'TAS'
