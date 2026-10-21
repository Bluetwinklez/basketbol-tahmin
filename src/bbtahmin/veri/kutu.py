"""EuroLeague/EuroCup kutu skorları (takım toplamları ve oyuncu dakikaları).

Kaynak: https://api-live.euroleague.net/v3/competitions/{E,U}/seasons/{kod}/games/{no}/stats
Yanıtlar data/raw/kutu/<mac_id>.json olarak önbelleğe alınır; önbellekte olan yeniden indirilmez.
Saniyede en fazla ~3 istek gider; 429/5xx yanıtında beklenip yeniden denenir.
"""
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

URL = 'https://api-live.euroleague.net/v3/competitions/{lig}/seasons/{sezon}/games/{no}/stats'
AGENT = 'bbtahmin/0.1 (+github.com/Bluetwinklez; kisisel arastirma)'
ONBELLEK = Path('data/raw/kutu')
TAKIM_ALANLARI = {'points': 'say', 'fieldGoalsAttempted2': 'fga2', 'fieldGoalsAttempted3': 'fga3',
                  'freeThrowsAttempted': 'fta', 'offensiveRebounds': 'oreb', 'defensiveRebounds': 'dreb',
                  'turnovers': 'tov', 'foulsCommited': 'faul', 'timePlayed': 'sure'}


class Sinirlayici:
    """İş parçacıkları arasında paylaşılan basit istek aralığı."""
    def __init__(self, aralik):
        self.aralik, self.son, self.kilit = aralik, 0., threading.Lock()

    def bekle(self):
        with self.kilit:
            simdi = time.monotonic()
            gecikme = self.son + self.aralik - simdi
            if gecikme > 0:
                time.sleep(gecikme)
            self.son = time.monotonic()


def _indir(mac_id, sinirlayici, deneme=4):
    yol = ONBELLEK / f'{mac_id}.json'
    if yol.exists():
        return json.loads(yol.read_text('utf8'))
    lig = mac_id[0]
    sezon, no = mac_id.split('_')
    istek = urllib.request.Request(URL.format(lig=lig, sezon=sezon, no=no),
                                   headers={'User-Agent': AGENT, 'Accept': 'application/json'})
    for n in range(deneme):
        sinirlayici.bekle()
        try:
            with urllib.request.urlopen(istek, timeout=30) as yanit:
                veri = json.loads(yanit.read())
            ONBELLEK.mkdir(parents=True, exist_ok=True)
            yol.write_text(json.dumps(veri, ensure_ascii=False), 'utf8')
            return veri
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 500, 502, 503, 504) and n < deneme - 1:
                time.sleep(5 * 2 ** n)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if n < deneme - 1:
                time.sleep(5 * 2 ** n)
                continue
            raise
    return None


def ayristir(mac_id, veri):
    """Yanıttan (takım satırları, oyuncu satırları) üretir. Toplam yoksa ([], [])."""
    takimlar, oyuncular = [], []
    for taraf, rol in (('local', 'ev'), ('road', 'dep')):
        blok = (veri or {}).get(taraf) or {}
        toplam = blok.get('total')
        if not toplam:
            return [], []
        takimlar.append(dict(mac_id=mac_id, rol=rol, **{ad: toplam.get(alan) for alan, ad in TAKIM_ALANLARI.items()}))
        for o in blok.get('players') or []:
            st = o.get('stats') or {}
            kod = ((o.get('player') or {}).get('person') or {}).get('code')
            if kod and (st.get('timePlayed') or 0) > 0:
                oyuncular.append(dict(mac_id=mac_id, rol=rol, oyuncu=kod, saniye=float(st['timePlayed'])))
    return takimlar, oyuncular


def topla(maclar, iscik=10, aralik=.34, ilerleme=500):
    # Yanıt süresi ~3 sn olduğundan darboğaz gecikme; 10 işçi, sınırlayıcıyla en fazla ~3 istek/sn.
    """maclar: mac_id içeren tablo (E/U). data/kutu.parquet ve data/oyuncular.parquet yazar."""
    kimlikler = [m for m in maclar.mac_id if m[:1] in ('E', 'U')]
    sinirlayici = Sinirlayici(aralik)
    takimlar, oyuncular, hatalar = [], [], []

    def is_(mac_id):
        try:
            return mac_id, _indir(mac_id, sinirlayici), None
        except Exception as e:  # tek maçın hatası toplamayı durdurmasın
            return mac_id, None, str(e)

    with ThreadPoolExecutor(iscik) as havuz:
        for i, (mac_id, veri, hata) in enumerate(havuz.map(is_, kimlikler), 1):
            if hata:
                hatalar.append(dict(mac_id=mac_id, hata=hata))
            t, o = ayristir(mac_id, veri)
            takimlar += t
            oyuncular += o
            if i % ilerleme == 0:
                print(json.dumps(dict(islenen=i, toplam=len(kimlikler), hata=len(hatalar)), ensure_ascii=False), flush=True)
    pd.DataFrame(takimlar).to_parquet('data/kutu.parquet', index=False)
    pd.DataFrame(oyuncular).to_parquet('data/oyuncular.parquet', index=False)
    ozet = dict(mac=len(kimlikler), kutu_olan=len(takimlar) // 2, oyuncu_satiri=len(oyuncular), hata=len(hatalar))
    Path('docs/kanit').mkdir(parents=True, exist_ok=True)
    Path('docs/kanit/kutu_toplama.json').write_text(json.dumps(dict(ozet, hatalar=hatalar[:50]), ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(ozet, ensure_ascii=False), flush=True)
    return ozet
