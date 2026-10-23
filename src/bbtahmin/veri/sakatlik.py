"""NBA resmi sakatlık raporu (Official Injury Report) PDF'i.

Rapor her gün 15 ya da 30 dakikada bir yayınlanır:
https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HH_MM{AM,PM}.pdf (ABD Doğu saati)
Maçtan önceki en son rapor bulunur, data/raw/sakatlik/ altına kaydedilir ve tablo olarak okunur.
Bilgi amaçlıdır: modele girmez (geçmiş raporlarla backtest yapılmadı).
"""
import re
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
import pandas as pd
from .teams import ALIASES, _key

URL = 'https://ak-static.cms.nba.com/referee/injury/Injury-Report_{tarih}_{saat}.pdf'
ONBELLEK = Path('data/raw/sakatlik')
DURUMLAR = ('Out', 'Doubtful', 'Questionable', 'Probable', 'Available')
# PDF metninde adlar boşluksuz gelir ("Dennis,RayJ"). İç içe tekrar kullanılmaz: uzun satırda
# üstel geri izlemeye düşüyordu.
SATIR = re.compile(r'(?P<oyuncu>[^\s,]+,[^\s,]+)\s+(?P<durum>' + '|'.join(DURUMLAR) + r')\b(?P<neden>.*)')
MAC = re.compile(r'\b([A-Z]{3})@([A-Z]{3})\b')
# Rapordaki kısaltmalar (BKN, CHA, PHX…) veri setindeki Basketball Reference kodlarına.
RAPOR_KODU = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO', 'NOP': 'NOP', 'GSW': 'GSW', 'NYK': 'NYK', 'SAS': 'SAS'}


def _takim_kodu(ad):
    """'AtlantaHawks' → 'ATL'."""
    k = _key(ad)
    for kod, adlar in ALIASES.items():
        if k in {_key(a) for a in adlar}:
            return kod
    return None


def ayristir(metin, include_dates=False):
    """PDF metninden (mac, takim, oyuncu, durum, neden) satırları."""
    satirlar, mac, takim = [], None, None
    game_date=None
    for satir in metin.splitlines():
        date=re.search(r'(?<![0-9])(\d{2}/\d{2}/\d{4})(?![0-9])',satir)
        if date:game_date=pd.to_datetime(date[1],format='%m/%d/%Y').strftime('%Y-%m-%d')
        m = MAC.search(satir)
        if m:
            mac = f'{RAPOR_KODU.get(m.group(1), m.group(1))}@{RAPOR_KODU.get(m.group(2), m.group(2))}'
            satir = satir[m.end():].strip()
        # Takım adı satırın başında, oyuncudan önce bitişik yazılır: "AtlantaHawks Dennis,RayJ Questionable ..."
        parca = satir.split(' ', 1)
        if parca and ',' not in parca[0] and _takim_kodu(parca[0]):
            takim = _takim_kodu(parca[0])
            satir = parca[1] if len(parca) > 1 else ''
        o = SATIR.search(satir)
        if o and mac and takim:
            row=dict(mac=mac,takim=takim,oyuncu=o.group('oyuncu'),durum=o.group('durum'),neden=o.group('neden').strip())
            if include_dates:row['game_date']=game_date
            satirlar.append(row)
    return pd.DataFrame(satirlar, columns=['mac', 'takim', 'oyuncu', 'durum', 'neden']+(['game_date'] if include_dates else []))


def _saat_adi(t):
    return t.strftime('%I_%M%p')


def son_rapor(an, geriye_saat=30):
    """an (UTC zaman damgası) ya da öncesindeki en son raporu indirir ve okur. Bulunamazsa boş tablo."""
    import pdfplumber
    requested = pd.Timestamp(an)
    if requested.tzinfo is None:
        raise ValueError('Injury report cutoff must include a timezone')
    cutoff = min(requested.tz_convert('UTC'), pd.Timestamp.now(tz='UTC'))
    et = cutoff.floor('15min').tz_convert('America/New_York')
    for adim in range(int(geriye_saat * 4)):
        t = et - timedelta(minutes=15 * adim)
        ad = f"{t.strftime('%Y-%m-%d')}_{_saat_adi(t)}"
        yol = ONBELLEK / f'{ad}.pdf'
        if not yol.exists():
            try:
                istek = urllib.request.Request(URL.format(tarih=t.strftime('%Y-%m-%d'), saat=_saat_adi(t)),
                                               headers={'User-Agent': 'Mozilla/5.0 (bbtahmin)'})
                with urllib.request.urlopen(istek, timeout=20) as y:
                    veri = y.read()
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
                continue
            ONBELLEK.mkdir(parents=True, exist_ok=True)
            yol.write_bytes(veri)
        with pdfplumber.open(yol) as pdf:
            metin = '\n'.join(p.extract_text() or '' for p in pdf.pages)
        tablo = ayristir(metin,include_dates=True)
        import hashlib
        tablo.attrs['source_pdf_sha256']=hashlib.sha256(yol.read_bytes()).hexdigest()
        tablo.attrs['rapor'] = f'{ad} ET'
        tablo.attrs['published_at_utc'] = t.tz_convert('UTC').isoformat()
        return tablo
    return pd.DataFrame(columns=['mac', 'takim', 'oyuncu', 'durum', 'neden'])
