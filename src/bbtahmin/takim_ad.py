"""Serbest yazılmış takım adını veri setindeki takım koduna çevirir ("Fenerbahçe" → ULK)."""
import difflib
import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from .veri.teams import ALIASES

# Türkçe ve yaygın kısaltmalar; resmi adlar EuroLeague önbelleğinden okunur.
EK_ADLAR = {
    'ULK': ['fener', 'fenerbahce', 'fb'], 'IST': ['efes', 'anadolu efes', 'efes pilsen'],
    'PAN': ['pao', 'panathinaikos'], 'OLY': ['olympiacos', 'olimpiakos', 'oly'],
    'MAD': ['real', 'real madrid'], 'BAR': ['barca', 'barcelona'], 'RED': ['kizilyildiz', 'crvena zvezda', 'red star'],
    'PAR': ['partizan'], 'TEL': ['maccabi', 'maccabi tel aviv'], 'HTA': ['hapoel', 'hapoel tel aviv'],
    'MIL': ['milano', 'olimpia milano', 'armani'], 'MUN': ['bayern', 'bayern munih'], 'ZAL': ['zalgiris'],
    'MCO': ['monaco'], 'PAM': ['valencia'], 'BAS': ['baskonia', 'vitoria'], 'VIR': ['virtus', 'bologna'],
    'ASV': ['asvel', 'villeurbanne'], 'PRS': ['paris'], 'DUB': ['dubai'],
    'TTK': ['turk telekom'], 'BES': ['besiktas'], 'BAH': ['bahcesehir'], 'GAL': ['galatasaray'],
    'KAR': ['karsiyaka'], 'DAR': ['darussafaka'],
}


def anahtar(metin):
    """Büyük/küçük harf, Türkçe karakter ve noktalama farkını yok sayar."""
    metin = str(metin).replace('ı', 'i').replace('İ', 'i')
    metin = unicodedata.normalize('NFKD', metin).encode('ascii', 'ignore').decode()
    return ' '.join(''.join(c if c.isalnum() else ' ' for c in metin.casefold()).split())


@lru_cache(maxsize=None)
def euro_adlari(kok='data/raw/api-live.euroleague.net'):
    """Önbellekteki EuroLeague/EuroCup yanıtlarından (lig, kod) → ad kümesi."""
    adlar = {}
    for dosya in Path(kok).glob('*'):
        if dosya.suffix == '.json':
            continue
        try:
            veri = json.loads(dosya.read_text('utf8'))
        except (ValueError, UnicodeDecodeError):
            continue
        for oyun in veri.get('data', []) if isinstance(veri, dict) else []:
            lig = (oyun.get('season') or {}).get('competitionCode')
            for taraf in ('local', 'road'):
                kulup = (oyun.get(taraf) or {}).get('club') or {}
                if kulup.get('code') and lig:
                    kume = adlar.setdefault((lig, kulup['code']), set())
                    for alan in ('name', 'abbreviatedName', 'editorialName', 'tvCode'):
                        if kulup.get(alan):
                            kume.add(kulup[alan])
    return adlar


def aday_adlari(lig, kodlar):
    """lig içindeki her kod için aranabilir ad listesi."""
    euro = euro_adlari()
    sonuc = {}
    for kod in kodlar:
        adlar = {kod} | set(EK_ADLAR.get(kod, []))
        if lig == 'NBA':
            adlar |= set(ALIASES.get(kod, []))
        elif lig in ('ECW','FEC','VTB'):
            path=Path(f'data/competitions/{lig}_teams.json')
            entry=json.loads(path.read_text('utf8')).get(kod,{}) if path.exists() else {}
            adlar |= {entry.get('name','')} | set(entry.get('aliases',[]))
            specific={'ECW_892':['BK Zabiny Brno'],'ECW_58477':['ZKK Celje'],
                      'ECW_813':['Montana 2003'],'FEC_58616':['KK Parnu']}
            adlar |= set(specific.get(kod,[]))
        elif lig == 'CBA':
            path=Path('data/cba_teams.json')
            entry=json.loads(path.read_text('utf8')).get(kod,{}) if path.exists() else {}
            adlar |= {entry.get('name','')} | set(entry.get('aliases',[]))
        elif lig == 'NBL':
            from .veri.nbl import ADLAR
            ad = ADLAR.get(kod, '')
            adlar |= {ad, ad.split()[-1], ' '.join(ad.split()[:-1])} if ad else set()
        else:
            adlar |= euro.get((lig, kod), set())
        sonuc[kod] = {anahtar(a) for a in adlar if a}
    return sonuc


def coz(lig, metin, kodlar):
    """Metni lig koduna çevirir. Belirsiz ya da bulunamazsa ValueError (aday listesiyle)."""
    hedef = anahtar(metin)
    adaylar = aday_adlari(lig, kodlar)
    tam = [k for k, adlar in adaylar.items() if hedef in adlar]
    if len(tam) == 1:
        return tam[0]
    # Kısmi eşleşme: "real madrid" → "real madrid"; "zenit" gibi bilinmeyenler eşleşmez.
    kismi = [k for k, adlar in adaylar.items() if any(hedef and (hedef in a.split() or a.startswith(hedef) or hedef.startswith(a + ' ')) for a in adlar)]
    if len(kismi) == 1:
        return kismi[0]
    hepsi = {a: k for k, adlar in adaylar.items() for a in adlar}
    yakin = difflib.get_close_matches(hedef, list(hepsi), n=3, cutoff=.8)
    kodlar_yakin = sorted({hepsi[a] for a in yakin})
    if len(kodlar_yakin) == 1:
        return kodlar_yakin[0]
    oneriler = sorted(set(tam + kismi + kodlar_yakin))
    raise ValueError(f'"{metin}" {lig} liginde bulunamadı' + (f'; adaylar: {", ".join(oneriler)}' if oneriler else ''))
