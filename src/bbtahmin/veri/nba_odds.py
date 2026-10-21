"""Sportsbook Reviews Online NBA arşivi: sezon sayfası HTML tablosu (Date/Rot/VH/Team/.../ML).

Sitenin Terms sayfası içeriğin yazılı izin olmadan kullanılmasını yasaklar; bu yüzden
indirme ve ayrıştırma yalnız `topla --sbr-izni` ile açıkça istenirse çalışır.
"""
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import pandas as pd
from bs4 import BeautifulSoup
from .teams import team_code

TERMS = 'https://www.sportsbookreviewsonline.com/terms/'

def season_url(year):
    return f'https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-{year}-{str(year+1)[-2:]}/'

def moneyline(text):
    text=text.strip().replace('+','')
    try:
        value=float(text)
    except ValueError:
        return None
    return value if abs(value)>=100 else None

def parse_season(html,year):
    """Returns one row per game; rows of the table come in visitor/home (or N/N) pairs."""
    soup=BeautifulSoup(html,'html.parser')
    table=soup.find('table')
    if table is None:
        raise RuntimeError('Oran tablosu yok')
    header=[c.get_text(strip=True) for c in table.find('tr').find_all(['td','th'])]
    needed=['Date','VH','Team','Final','ML']
    if any(h not in header for h in needed):
        raise RuntimeError(f'Beklenmeyen başlık: {header}')
    index={h:header.index(h) for h in needed}
    lines=[]
    for tr in table.find_all('tr')[1:]:
        cells=[c.get_text(strip=True) for c in tr.find_all(['td','th'])]
        if len(cells)<len(header): continue
        lines.append({h:cells[i] for h,i in index.items()})
    if len(lines)%2:
        raise RuntimeError('Tek sayıda oran satırı: eşleştirilemez')
    games=[]
    for first,second in zip(lines[0::2],lines[1::2]):
        if first['Date']!=second['Date']:
            raise RuntimeError(f"Çift satır tarihleri farklı: {first['Date']} {second['Date']}")
        neutral=first['VH']=='N' and second['VH']=='N'
        if not neutral and (first['VH'],second['VH'])!=('V','H'):
            raise RuntimeError(f"Beklenmeyen VH sırası: {first['VH']} {second['VH']}")
        month,day=int(first['Date'][:-2]),int(first['Date'][-2:])
        games.append(dict(sezon=f'{year}-{str(year+1)[-2:]}',tarih_yerel=pd.Timestamp(
            year=year if month>=8 else year+1,month=month,day=day),
            ev_adi=second['Team'],dep_adi=first['Team'],ev_skor=int(second['Final']),dep_skor=int(first['Final']),
            ev_ml=moneyline(second['ML']),dep_ml=moneyline(first['ML']),tarafsiz=neutral))
    return games

def match(odds,games):
    """Joins odds rows to bref games by US-Eastern date and team pair; returns (matched, unmatched)."""
    nba=games[games.lig=='NBA'].copy()
    nba['tarih_yerel']=nba.tarih_utc.dt.tz_convert(ZoneInfo('America/New_York')).dt.tz_localize(None).dt.normalize()
    by_key={(r.tarih_yerel,frozenset((r.ev,r.dep))):r for r in nba.itertuples()}
    matched,unmatched=[],[]
    for o in odds:
        try:
            home,away=team_code(o['ev_adi']),team_code(o['dep_adi'])
        except ValueError as exc:
            unmatched.append(dict(o,neden=str(exc)));continue
        game=by_key.get((o['tarih_yerel'],frozenset((home,away))))
        if game is None:
            unmatched.append(dict(o,neden='Basketball Reference maçı yok'));continue
        flipped=game.ev!=home
        if flipped and not o['tarafsiz']:
            unmatched.append(dict(o,neden='Ev/deplasman ters'));continue
        ev_ml,dep_ml=(o['dep_ml'],o['ev_ml']) if flipped else (o['ev_ml'],o['dep_ml'])
        ev_skor,dep_skor=(o['dep_skor'],o['ev_skor']) if flipped else (o['ev_skor'],o['dep_skor'])
        if (ev_skor,dep_skor)!=(game.ev_skor,game.dep_skor):
            unmatched.append(dict(o,neden='Skor uyuşmuyor'));continue
        if ev_ml is None or dep_ml is None:
            unmatched.append(dict(o,neden='Moneyline yok'));continue
        matched.append(dict(mac_id=game.mac_id,sezon=o['sezon'],ev_ml=ev_ml,dep_ml=dep_ml))
    return pd.DataFrame(matched,columns=['mac_id','sezon','ev_ml','dep_ml']),unmatched

def collect(http,year):
    url=season_url(year)
    raw=http.get(url)
    if urlparse(http.last_url).path.rstrip('/')!=urlparse(url).path.rstrip('/'):
        raise RuntimeError(f'Arşiv sayfası yok (ana sayfaya yönlendirildi): {url}')
    return parse_season(raw,year)
