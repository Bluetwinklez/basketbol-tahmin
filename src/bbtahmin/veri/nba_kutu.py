"""NBA takım ve oyuncu kutu skorları: sportsdataverse (ESPN kaynaklı) toplu parquet dosyaları.

https://github.com/sportsdataverse/sportsdataverse-data (MIT lisanslı paket; veri ESPN'den derlenir).
Dosyalar data/raw/espn/ altında önbelleğe alınır. ESPN maçı, Basketball Reference maç kimliğine
(NBA_YYYYMMDD0EVKODU) tarih ve ev sahibi koduyla eşlenir; eşleşmeyenler sayılır ve atlanır.
"""
import json
import urllib.request
from pathlib import Path
import pandas as pd

URL = 'https://github.com/sportsdataverse/sportsdataverse-data/releases/download/{etiket}/{dosya}_{yil}.parquet'
ONBELLEK = Path('data/raw/espn')
ESPN_KOD = {'BKN': 'BRK', 'CHA': 'CHO', 'GS': 'GSW', 'NO': 'NOP', 'NY': 'NYK', 'PHX': 'PHO', 'SA': 'SAS',
            'UTAH': 'UTA', 'WSH': 'WAS'}


def _indir(etiket, dosya, yil, yenile=False):
    yol = ONBELLEK / f'{dosya}_{yil}.parquet'
    if yenile or not yol.exists():
        ONBELLEK.mkdir(parents=True, exist_ok=True)
        istek = urllib.request.Request(URL.format(etiket=etiket, dosya=dosya, yil=yil),
                                       headers={'User-Agent': 'bbtahmin/0.1'})
        with urllib.request.urlopen(istek, timeout=120) as y:
            yol.write_bytes(y.read())
    return pd.read_parquet(yol)


def mac_kimligi(tarih, ev):
    return f"NBA_{pd.Timestamp(tarih):%Y%m%d}0{ESPN_KOD.get(ev, ev)}"


def topla(maclar, ilk=2015, son=2027):
    """maclar: data/maclar.parquet. data/kutu_nba.parquet ve data/oyuncular_nba.parquet yazar.
    Yıl, sezonun bittiği yıldır (2027 = 2026-27). Süren sezonun dosyası her çalıştırmada yenilenir."""
    bilinen = set(maclar.loc[maclar.lig == 'NBA', 'mac_id'])
    uzatma = dict(zip(maclar.mac_id, maclar.uzatma.fillna(False)))
    takimlar, oyuncular, eslesmeyen = [], [], 0
    for yil in range(ilk, son + 1):
        tb = _indir('espn_nba_team_boxscores', 'team_box', yil, yenile=yil == son)
        tb = tb[tb.season_type.isin([2, 3])]          # normal sezon ve playoff (all-star hariç)
        ev = tb[tb.team_home_away == 'home'].set_index('game_id')
        kimlik = {gid: mac_kimligi(r.game_date, r.team_abbreviation) for gid, r in ev.iterrows()}
        for r in tb.itertuples():
            mac = kimlik.get(r.game_id)
            if mac not in bilinen:
                eslesmeyen += r.team_home_away == 'home'
                continue
            fga3 = r.three_point_field_goals_attempted
            takimlar.append(dict(mac_id=mac, rol='ev' if r.team_home_away == 'home' else 'dep', say=r.team_score,
                                 fga2=r.field_goals_attempted - fga3, fga3=fga3, fta=r.free_throws_attempted,
                                 oreb=r.offensive_rebounds, dreb=r.defensive_rebounds, tov=r.total_turnovers,
                                 faul=r.fouls, sure=2880. + (300. if uzatma.get(mac) else 0.)))
        try:
            pb = _indir('espn_nba_player_boxscores', 'player_box', yil, yenile=yil == son)
        except Exception:
            continue
        pb = pb[pb.game_id.isin(kimlik) & (pd.to_numeric(pb.minutes, errors='coerce') > 0)]
        for r in pb.itertuples():
            mac = kimlik[r.game_id]
            if mac in bilinen:
                oyuncular.append(dict(mac_id=mac, rol='ev' if r.home_away == 'home' else 'dep',
                                      oyuncu=str(r.athlete_id), saniye=float(r.minutes) * 60))
    t = pd.DataFrame(takimlar).drop_duplicates(['mac_id', 'rol'])
    t.to_parquet('data/kutu_nba.parquet', index=False)
    pd.DataFrame(oyuncular).to_parquet('data/oyuncular_nba.parquet', index=False)
    ozet = dict(kutu_olan=len(t) // 2, oyuncu_satiri=len(oyuncular), eslesmeyen_mac=int(eslesmeyen),
                nba_mac=len(bilinen))
    Path('docs/kanit').mkdir(parents=True, exist_ok=True)
    Path('docs/kanit/kutu_nba.json').write_text(json.dumps(ozet, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(ozet, ensure_ascii=False), flush=True)
    return ozet
