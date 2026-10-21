"""Ortak sızıntı denetleyicisi: hedef maç ve sonrası silinince özellikler değişmemeli."""
import pandas as pd

def assert_no_leakage(feature_fn,games,match):
    original=feature_fn(games,match)
    past=games[games.tarih_utc<match['tarih_utc']]
    recomputed=feature_fn(past,match)
    pd.testing.assert_series_equal(original,recomputed,check_exact=True)

def leaky_features(history,match):
    """Kasıtlı sızıntı: ligin tüm maçlarının (gelecek dahil) ortalama ev skoru."""
    league=history[history.lig==match['lig']]
    return pd.Series(dict(ev_skor_ortalama=float(league.ev_skor.mean())),name=match['mac_id'])
