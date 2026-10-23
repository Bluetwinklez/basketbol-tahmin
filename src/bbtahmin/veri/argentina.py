"""Separate senior men's Liga Nacional data: official current, publisher history.

Read only public page/fixture handlers. No women's, development, Liga Argentina
or Super 20 games are mixed into this archive. Unknown clubs fail explicitly.
"""
import hashlib
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
from bs4 import BeautifulSoup

from .competitions import fetch

CODE='ARG_LNB'
BASE='https://www.laliganacional.com.ar'
HISTORY='https://pickandroll.com.ar/pnr-fixture/'
ZONE='America/Argentina/Buenos_Aires'
CLUBS={
 'ARGENTINO':['ARGENTINO (J)','Argentino (Junín)','Argentino J.','Argentino','Atletico Argentino de Junin'],
 'ATENAS':['ATENAS (C)','Atenas (Córdoba)','Atenas Cordoba','Atenas Cord','Atenas'],
 'BOCA':['BOCA','Boca Juniors'], 'FERRO':['FERRO','Ferro Carril Oeste','Ferrocarril Oeste Buenos Aires'],
 'GIMNASIA':['GIMNASIA (CR)','Gimnasia y Esgrima (C. Rivadavia)','Gimnasia (Comodoro Rivadavia)','Gimnasia Indalo'],
 'INDEPENDIENTE':['INDEPENDIENTE (O)','Independiente (Oliva)','Independiente de Oliva'],
 'INSTITUTO':['INSTITUTO','Instituto (Córdoba)','Instituto Atletico Central Cordoba'],
 'LA_UNION':['LA UNION FSA','La Unión (Formosa)','La Union de Formosa'],
 'LANUS':['LANÚS','Lanus','CA Lanus'], 'OBERA':['OBERÁ','Oberá Tenis Club','Obera TC'],
 'OLIMPICO':['OLIMPICO (LB)','Olímpico (La Banda)','Ciclista Olimpico'],
 'PENAROL':['PEÑAROL (MDP)','Peñarol (Mar del Plata)','Penarol'], 'PLATENSE':['PLATENSE','Club Athletico Platense'],
 'QUIMSA':['QUIMSA','Quimsa (Santiago del Estero)','Quimsa S.'],
 'RACING':['RACING (CH)','Racing (Chivilcoy)','Racing de Chivilcoy'],
 'REGATAS':['REGATAS (C)','Regatas (Corrientes)','Regatas Corrientes'],
 'SAN_LORENZO':['SAN LORENZO','San Lorenzo (Almagro)','San Lorenzo de Almagro'],
 'SAN_MARTIN':['SAN MARTÍN (C)','San Martín (Corrientes)','San Martin Corrientes'],
 'COMUNICACIONES':['Comunicaciones','Comunicaciones (Mercedes)'], 'UNION_SF':['Unión (Santa Fe)','Union de Santa Fe'],
 'RIACHUELO':['Riachuelo (La Rioja)','Riachuelo'], 'OBRAS':['Obras Sanitarias','Obras'],
 'ZARATE':['Zárate Basket','Zarate Basket','Zárate'], 'HISPANO':['Hispano Americano'],
}


def normalize_name(value):
    text=''.join(c for c in unicodedata.normalize('NFKD',str(value).casefold()) if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',text).split())


ALIASES={normalize_name(alias):CODE+'_'+club for club,aliases in CLUBS.items() for alias in aliases}


def team(name):
    result=ALIASES.get(normalize_name(name))
    if result is None:raise ValueError('Unknown Liga Nacional club: '+str(name))
    return result


def catalog():
    return {CODE+'_'+club:dict(name=aliases[0],aliases=aliases) for club,aliases in CLUBS.items()}


def _base(home,away,when,season,captured,source,identifier,precision):
    home_id,away_id=team(home),team(away)
    if home_id==away_id:raise ValueError('Same Argentina team on both sides')
    return dict(mac_id=CODE+'_'+hashlib.sha256(identifier.encode()).hexdigest()[:24],lig=CODE,
                sezon=season,tarih_utc=when.tz_convert('UTC'),ev=home_id,dep=away_id,
                home_name=home,away_name=away,source_url=source,captured_at_utc=captured,
                date_precision=precision,regulation_minutes=40,tarafsiz_saha=False)


def parse_history(html,year,captured,source,rejected=None):
    soup=BeautifulSoup(html,'html.parser');season=f'{year}-{str(year+1)[-2:]}'
    for field,value in [('comp','LNB'),('season',season)]:
        selected=soup.select_one(f'input[name="{field}"]')
        if selected is not None and selected.get('value')!=value:raise ValueError('Wrong history competition/season')
    rows=[];eligible=0
    for table in soup.select('table'):
        heading=table.select_one('tr')
        if heading is None or not all(label in heading.get_text(' ',strip=True) for label in ('Fecha','Local','Visitante','Estado')):continue
        for tr in table.select('tr'):
            cells=tr.find_all('td',recursive=False)
            if len(cells)!=7:continue
            date=cells[0].get_text(' ',strip=True)
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):raise ValueError('Unknown history match date')
            when=pd.Timestamp(date).tz_localize(ZONE)
            if not year<=when.year<=year+1:raise ValueError('History date outside selected season')
            status=cells[5].get_text(' ',strip=True).casefold()
            if status!='final':continue
            eligible+=1
            if when.normalize()>=pd.Timestamp(captured).tz_convert(ZONE).normalize():continue
            hs,ds=[c.get_text(' ',strip=True) for c in cells[2:4]]
            if not hs.isdecimal() or not ds.isdecimal() or not 0<int(hs)<=250 or not 0<int(ds)<=250 or hs==ds:
                if rejected is None:raise ValueError('Invalid historical final score')
                rejected.append(dict(season=season,date=date,home=cells[1].get_text(' ',strip=True),away=cells[4].get_text(' ',strip=True),home_score=hs,away_score=ds,reason='Invalid historical final score',source_url=source))
                continue
            home,away=cells[1].get_text(' ',strip=True),cells[4].get_text(' ',strip=True)
            link=cells[6].find('a',href=True)
            identity=f'{season}:{date}:{team(home)}:{team(away)}'
            row=_base(home,away,when,season,captured,source,identity,'day')
            row.update(ev_skor=int(hs),dep_skor=int(ds),source_kind='publisher_history_not_official',
                       publisher_match_url=link['href'] if link else None)
            rows.append(row)
    if len(rows)<50:raise ValueError('History page has too few valid final rows or an unexpected schema')
    return rows


def parse_official(html,year,captured,source):
    soup=BeautifulSoup(html,'html.parser');rows=[];fixtures=[]
    for tr in soup.select('tr.fila-tabla-calendarios'):
        names=tr.select('td.celda-nombre');clock=tr.select_one('td.fecha-campo strong')
        if len(names)!=2 or clock is None:raise ValueError('Incomplete official fixture row')
        date=clock.get_text(' ',strip=True)
        if not re.fullmatch(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}',date):raise ValueError('Unconfirmed official fixture clock')
        when=pd.to_datetime(date,format='%d/%m/%Y %H:%M').tz_localize(ZONE)
        if not year<=when.year<=year+1:raise ValueError('Official fixture outside requested season')
        home,away=[n.get_text(' ',strip=True) for n in names]
        link=tr.select_one('a[href*="/laliga/partido/"]')
        if link is None:raise ValueError('Official fixture has no stable match link')
        path=link['href'];token=path.split('/partido/',1)[1].split('/',1)[0]
        source_url=BASE+path if path.startswith('/') else path
        row=_base(home,away,when,f'{year}-{str(year+1)[-2:]}',captured,source_url,'official:'+token,'timestamp')
        row['listing_url']=source;row['source_kind']='official_liga_nacional';row['provider_event_token']=token
        scores=[n.get_text(' ',strip=True) for n in tr.select('td.resultados')]
        has_scores=len(scores)==2 and all(s.isdecimal() and 0<int(s)<=250 for s in scores)
        if has_scores and scores[0]!=scores[1] and when.normalize()<pd.Timestamp(captured).tz_convert(ZONE).normalize():
            row.update(ev_skor=int(scores[0]),dep_skor=int(scores[1]));rows.append(row)
        else:
            row['status']='scheduled' if not has_scores and when>pd.Timestamp(captured) else 'unverified'
            fixtures.append(row)
    if not rows and not fixtures:raise ValueError('Official fixture handler returned no match rows')
    return rows,fixtures


def merge_results(previous,rows):
    g=pd.concat([previous,pd.DataFrame(rows)],ignore_index=True)
    if g.empty:raise ValueError('No Argentina finals available')
    fields=['lig','sezon','tarih_utc','ev','dep','ev_skor','dep_skor']
    for _,group in g.groupby('mac_id'):
        if len(group[fields].drop_duplicates())!=1:raise ValueError('Conflicting persisted Argentina result')
    g=g.drop_duplicates('mac_id',keep='last')
    day=pd.to_datetime(g.tarih_utc,utc=True).dt.tz_convert(ZONE).dt.strftime('%Y-%m-%d')
    if g.assign(day=day).duplicated(['sezon','day','ev','dep']).any():raise ValueError('Duplicate Argentina natural fixture identity')
    return g.sort_values(['tarih_utc','mac_id']).reset_index(drop=True)


def collect(first=2022,last=None):
    now=pd.Timestamp.now(tz='UTC');active=now.year if now.month>=7 else now.year-1
    last=active if last is None else last
    if not 2022<=first<=last<=active:raise ValueError('Argentina source coverage starts in 2022')
    root=Path('data/competitions');root.mkdir(parents=True,exist_ok=True)
    path=root/f'{CODE}.parquet';previous=pd.read_parquet(path) if path.exists() else pd.DataFrame()
    records=[];fixtures=[];errors=[];sources=[];counts=[];rejected=[];official_ok=False
    for year in range(first,last+1):
        if year<active:
            url=HISTORY+'?'+urlencode(dict(comp='LNB',season=f'{year}-{str(year+1)[-2:]}'))
        else:
            url=BASE+'/laliga/fixture?'+urlencode(dict(handler='ProximosPartidos',fechaInicio=f'{year}-07-01',fechaFin=(now+pd.Timedelta(days=30)).strftime('%Y-%m-%d')))
        try:
            html=fetch(url,refresh=year==active);sources.append(dict(url=url,sha256=hashlib.sha256(html.encode()).hexdigest()))
            if year<active:rows=parse_history(html,year,now.isoformat(),url,rejected)
            else:
                rows,fixtures=parse_official(html,year,now.isoformat(),url)
                # Positive listing scores alone cannot certify a completed match.
                def confirmed(row):
                    detail=fetch(row['source_url'],refresh=True)
                    return row if re.search(r'\bfinalizado\b',BeautifulSoup(detail,'html.parser').get_text(' ',strip=True),re.I) else None
                with ThreadPoolExecutor(max_workers=2) as pool:checked=list(pool.map(confirmed,rows))
                unresolved=sum(row is None for row in checked)
                if unresolved:errors.append(dict(year=year,error=f'{unresolved} listing scores lacked explicit final confirmation'))
                rows=[row for row in checked if row is not None];official_ok=True
            records+=rows;counts.append(dict(season=f'{year}-{str(year+1)[-2:]}',finals=len(rows)))
        except Exception as exc:
            errors.append(dict(year=year,error=f'{type(exc).__name__}: {exc}',retained_previous=True))
            print(json.dumps(errors[-1],ensure_ascii=False),flush=True)
    combined=merge_results(previous,records)
    # Prepare validated outputs before replacing persisted files.
    frame=None
    if official_ok:
        target=root/f'{CODE}_fixtures.parquet'
        columns=['mac_id','lig','sezon','tarih_utc','ev','dep','home_name','away_name','source_url','captured_at_utc','date_precision','status']
        frame=pd.DataFrame(fixtures,columns=columns+['provider_event_token','source_kind','listing_url','regulation_minutes','tarafsiz_saha'])
        if frame.mac_id.duplicated().any():raise ValueError('Duplicate official Argentina fixtures')
    temp=path.with_suffix('.part');combined.to_parquet(temp,index=False)
    if frame is not None:
        temporary=target.with_suffix('.part');frame.to_parquet(temporary,index=False)
    temp.replace(path)
    if frame is not None:temporary.replace(target)
    (root/f'{CODE}_teams.json').write_text(json.dumps(catalog(),ensure_ascii=False,indent=2),encoding='utf8')
    report=dict(captured_at_utc=now.isoformat(),league=CODE,games=len(combined),seasons=combined.groupby('sezon').size().to_dict(),
                teams=int(pd.concat([combined.ev,combined.dep]).nunique()),counts=counts,fixtures=len(fixtures),errors=errors,sources=sources,
                official_current_refresh=official_ok,timezone=ZONE,rejected_results=rejected,
                limitations='Publisher historical finals have day precision and unknown historical availability. Official old-season handler returned no history. Current positive scores require a separate Finalizado match page and prior local day. No other Argentine divisions or cups. Full season coverage and venue neutrality not certified.')
    evidence=Path('docs/kanit/competitions');evidence.mkdir(parents=True,exist_ok=True)
    (evidence/f'{CODE}_collection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    return combined
