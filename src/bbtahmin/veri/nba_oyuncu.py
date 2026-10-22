"""NBA oyuncu maç kayıtları: nba_api (stats.nba.com PlayerGameLogs, MIT lisanslı istemci).

Sezon başına bir istek; data/raw/nbaapi/ altında önbelleğe alınır (süren sezon her çalıştırmada yenilenir).
Maçlar Basketball Reference kimliğine (NBA_YYYYMMDD0EVKODU) ABD tarihi ve ev sahibi koduyla eşlenir.
"""
import json
import time
from pathlib import Path
import pandas as pd

ONBELLEK = Path('data/raw/nbaapi')
NBA_KOD = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}


def sezon_adi(yil):
    return f'{yil}-{str(yil + 1)[-2:]}'


def _cek(sezon, tur, yenile=False):
    yol = ONBELLEK / f"{sezon}_{tur.replace(' ', '')}.parquet"
    if yenile or not yol.exists():
        from nba_api.stats.endpoints import playergamelogs
        d = playergamelogs.PlayerGameLogs(season_nullable=sezon, season_type_nullable=tur, timeout=90).get_data_frames()[0]
        ONBELLEK.mkdir(parents=True, exist_ok=True)
        d[['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'MIN', 'PLUS_MINUS']].to_parquet(yol, index=False)
        time.sleep(1.5)   # stats.nba.com'u yormamak için
    return pd.read_parquet(yol)


def mac_kimligi(tarih, matchup, takim):
    """'LAL vs. GSW' → ev LAL; 'NOP @ MIN' → ev MIN."""
    ev = takim if ' vs. ' in matchup else matchup.split(' @ ')[1].strip()
    return f"NBA_{pd.Timestamp(tarih):%Y%m%d}0{NBA_KOD.get(ev, ev)}", ' vs. ' in matchup


def topla(maclar, ilk=2014, son=2026):
    bilinen = set(maclar.loc[maclar.lig == 'NBA', 'mac_id'])
    parcalar, eslesmeyen = [], set()
    for yil in range(ilk, son + 1):
        for tur in ('Regular Season', 'Playoffs'):
            try:
                d = _cek(sezon_adi(yil), tur, yenile=yil == son)
            except Exception as e:
                print(json.dumps(dict(sezon=sezon_adi(yil), tur=tur, hata=str(e)[:120]), ensure_ascii=False), flush=True)
                continue
            if d.empty:
                continue
            k = [mac_kimligi(t, m, a) for t, m, a in zip(d.GAME_DATE, d.MATCHUP, d.TEAM_ABBREVIATION)]
            d = d.assign(mac_id=[x[0] for x in k], rol=['ev' if x[1] else 'dep' for x in k])
            eslesmeyen |= set(d.mac_id) - bilinen
            parcalar.append(d[d.mac_id.isin(bilinen)])
    t = pd.concat(parcalar, ignore_index=True)
    t = t.rename(columns={'PLAYER_ID': 'oyuncu_id', 'PLAYER_NAME': 'ad', 'MIN': 'dakika', 'PLUS_MINUS': 'pm'})
    t = t[['mac_id', 'rol', 'oyuncu_id', 'ad', 'dakika', 'pm']].drop_duplicates(['mac_id', 'oyuncu_id'])
    t.to_parquet('data/nba_oyuncu_mac.parquet', index=False)
    ozet = dict(satir=len(t), mac=t.mac_id.nunique(), nba_mac=len(bilinen), eslesmeyen_mac=len(eslesmeyen))
    Path('docs/kanit').mkdir(parents=True, exist_ok=True)
    Path('docs/kanit/nba_oyuncu.json').write_text(json.dumps(ozet, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(ozet, ensure_ascii=False), flush=True)
    return ozet
