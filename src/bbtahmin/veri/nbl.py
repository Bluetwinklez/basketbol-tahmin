"""Avustralya NBL maç sonuçları: JaseZiv/nblr_data (nblR paketinin veri deposu, her gün güncellenir).

https://github.com/JaseZiv/nblr_data/releases/download/box_team/box_team.csv — maç başına iki satır (ev/dep).
Takım kodları sezonlara göre değiştiği için (ILL/HAWKS/HWK…) takım adından tek koda indirilir.
Saatler yerel Avustralya saatidir; Sidney saat dilimiyle UTC'ye çevrilir (gün düzeyinde yeterli).
2025-26'dan itibaren depoda maç saati boş geldiği için 2022-23 ve sonrası ESPN skor tablosundan
(aylık sorgu, anahtarsız) alınır; ESPN'de daha eski NBL sezonu yok.
"""
import json
import urllib.request
from pathlib import Path
import pandas as pd
from .schema import normalize

ESPN = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nbl/scoreboard?dates={ay}'
ESPN_ILK_SEZON = 2022

URL = 'https://github.com/JaseZiv/nblr_data/releases/download/box_team/box_team.csv'
ONBELLEK = Path('data/raw/nbl/box_team.csv')
# Adın içinde geçen anahtar → kod (sıra önemli: "South East Melbourne" "Melbourne"dan önce).
KODLAR = [('south east melbourne', 'SEM'), ('melbourne united', 'MEL'), ('adelaide', 'ADL'), ('brisbane', 'BRI'),
          ('breakers', 'NZL'), ('cairns', 'CNS'), ('hawks', 'ILL'), ('perth', 'PER'), ('sydney', 'SYD'),
          ('tasmania', 'TAS'), ('townsville', 'TSV')]
ADLAR = {'SEM': 'South East Melbourne Phoenix', 'MEL': 'Melbourne United', 'ADL': 'Adelaide 36ers',
         'BRI': 'Brisbane Bullets', 'NZL': 'New Zealand Breakers', 'CNS': 'Cairns Taipans', 'ILL': 'Illawarra Hawks',
         'PER': 'Perth Wildcats', 'SYD': 'Sydney Kings', 'TAS': 'Tasmania JackJumpers', 'TSV': 'Townsville Crocodiles'}


def kod(ad):
    a = str(ad).casefold()
    for anahtar, k in KODLAR:
        if anahtar in a:
            return k
    raise ValueError(f'Bilinmeyen NBL takımı: {ad}')


def espn_topla(ilk=ESPN_ILK_SEZON, son=None):
    """ESPN NBL maçları (yalnız bitmiş), sezon başlangıç yılı ilk..son. Sezon Eylül-Mayıs."""
    son = son or pd.Timestamp.now().year
    satirlar = []
    for yil in range(ilk, son + 1):
        for ay in [f'{yil}{m:02d}' for m in range(9, 13)] + [f'{yil + 1}{m:02d}' for m in range(1, 6)]:
            istek = urllib.request.Request(ESPN.format(ay=ay), headers={'User-Agent': 'bbtahmin/0.1'})
            try:
                with urllib.request.urlopen(istek, timeout=30) as y:
                    olaylar = json.load(y).get('events', [])
            except Exception:
                continue
            for e in olaylar:
                c = e['competitions'][0]
                if c['status']['type']['name'] != 'STATUS_FINAL':
                    continue
                t = {x['homeAway']: x for x in c['competitors']}
                h, a = t['home'], t['away']
                hs, as_ = float(h['score']), float(a['score'])
                if hs == as_:
                    continue
                ceyrek = h.get('linescores') or []
                satirlar.append(dict(mac_id=f"NBL_E{e['id']}", lig='NBL', sezon=f'{yil}-{str(yil + 1)[-2:]}',
                                     tarih_utc=e['date'], ev=kod(h['team']['displayName']), dep=kod(a['team']['displayName']),
                                     ev_skor=hs, dep_skor=as_, uzatma=len(ceyrek) > 4, ev_iy=None, dep_iy=None,
                                     tarafsiz_saha=bool(c.get('neutralSite')), asama='normal', kaynak='espn'))
    return satirlar


def topla(yenile=True):
    if yenile or not ONBELLEK.exists():
        ONBELLEK.parent.mkdir(parents=True, exist_ok=True)
        istek = urllib.request.Request(URL, headers={'User-Agent': 'bbtahmin/0.1'})
        with urllib.request.urlopen(istek, timeout=120) as y:
            ONBELLEK.write_bytes(y.read())
    d = pd.read_csv(ONBELLEK, low_memory=False)
    ev, dep = d[d.home_away == 'home'].set_index('match_id'), d[d.home_away == 'away'].set_index('match_id')
    ortak = ev.index.intersection(dep.index)
    satirlar, atlanan = [], 0
    for m in ortak:
        h, a = ev.loc[m], dep.loc[m]
        if isinstance(h, pd.DataFrame):
            h, a = h.iloc[0], a.iloc[0]
        if pd.isna(h.score) or pd.isna(a.score) or h.score == a.score:
            atlanan += 1          # oynanmamış ya da hatalı (berabere) satır
            continue
        ceyrek = [h.get(f'p{i}_score') for i in range(1, 5)]
        uzatma = bool(all(pd.notna(c) for c in ceyrek) and sum(ceyrek) < h.score)
        iy = lambda r: r.p1_score + r.p2_score if pd.notna(r.p1_score) and pd.notna(r.p2_score) else None
        bas, son = str(h.season).split('-')
        tarih = pd.Timestamp(h.match_time).tz_localize('Australia/Sydney', ambiguous='NaT', nonexistent='shift_forward')
        satirlar.append(dict(mac_id=f'NBL_{m}', lig='NBL', sezon=f'{bas}-{son[-2:]}', tarih_utc=tarih.tz_convert('UTC'),
                             ev=kod(h['name']), dep=kod(a['name']), ev_skor=h.score, dep_skor=a.score, uzatma=uzatma,
                             ev_iy=iy(h), dep_iy=iy(a), tarafsiz_saha=False, asama='normal', kaynak=URL))
    eski = [s for s in satirlar if pd.notna(s['tarih_utc']) and int(s['sezon'][:4]) < ESPN_ILK_SEZON]
    yeni = espn_topla()
    tablo = normalize(eski + yeni)
    return tablo, dict(lig='NBL', mac=len(tablo), atlanan=atlanan, espn=len(yeni))
