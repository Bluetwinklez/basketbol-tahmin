import pandas as pd
import pytest
from bbtahmin.takim_ad import anahtar,coz

def test_anahtar_turkce_ve_noktalama():
    assert anahtar('Fenerbahçe Beko İstanbul')=='fenerbahce beko istanbul'
    assert anahtar('L.A. Clippers')=='l a clippers'

def test_coz_kisa_ad_ve_tam_ad():
    kodlar={'ULK','IST','PAN','MAD'}
    assert coz('E','Fenerbahçe',kodlar)=='ULK'
    assert coz('E','anadolu efes',kodlar)=='IST'
    assert coz('E','MAD',kodlar)=='MAD'

def test_coz_nba_alias():
    assert coz('NBA','Los Angeles Lakers',{'LAL','LAC'})=='LAL'

def test_coz_bilinmeyen_takim_hata_verir():
    with pytest.raises(ValueError):
        coz('E','Zenit Petersburg',{'ULK','IST'})
