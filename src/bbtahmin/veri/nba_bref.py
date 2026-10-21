from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from .teams import team_code

def collect(http,year):
    base=f'https://www.basketball-reference.com/leagues/NBA_{year+1}_games.html'
    soup=BeautifulSoup(http.get(base,nba=True),'html.parser')
    links=sorted({urljoin(base,a['href']) for a in soup.select('.filter a[href]')
                  if f'NBA_{year+1}_games-' in a['href']})
    if not links:
        raise RuntimeError(f'Aylık sayfalar bulunamadı: {base}')
    rows=[]
    errors=[]
    for url in links:
        try:
            raw=http.get(url,nba=True)
        except Exception as exc:
            errors.append(str(exc))
            continue
        page=BeautifulSoup(raw,'html.parser')
        table=page.select_one('#schedule')
        if table is None:
            raise RuntimeError(f'schedule tablosu yok: {url}')
        playoffs=False
        for tr in table.select('tbody tr'):
            if 'Playoffs' in tr.get_text():
                playoffs=True
            f={c.get('data-stat'):c for c in tr.select('[data-stat]')}
            if not f.get('home_pts') or not f['home_pts'].text.strip():
                continue
            date=f['date_game'].get('csk')
            if not date:
                raise ValueError('Tarih csk alanı yok')
            day=datetime.strptime(date[:8],'%Y%m%d')
            text=f['game_start_time'].text.strip() if f.get('game_start_time') else ''
            if not text:
                raise ValueError('Maç saati yok; gece yarısı varsayılmadı')
            clock=datetime.strptime(text.replace('a','AM').replace('p','PM'),'%I:%M%p')
            dt=day.replace(hour=clock.hour,minute=clock.minute,tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
            home=team_code(f['home_team_name'].text)
            away=team_code(f['visitor_team_name'].text)
            box=f.get('box_score_text')
            link=box.find('a') if box else None
            identifier=link['href'].split('/')[-1].replace('.html','') if link else f'{date}-{home}'
            # Bubble and international neutral courts need explicit enrichment.
            rows.append(dict(mac_id='NBA_'+identifier,lig='NBA',sezon=f'{year}-{str(year+1)[-2:]}',
                tarih_utc=dt,ev=home,dep=away,ev_skor=int(f['home_pts'].text),dep_skor=int(f['visitor_pts'].text),
                uzatma=bool(f.get('overtimes') and f['overtimes'].text.strip()),ev_iy=None,dep_iy=None,
                tarafsiz_saha=None,asama='playoff' if playoffs else 'normal',kaynak=url))
    marked=[r['tarih_utc'] for r in rows if r['asama']=='playoff']
    if marked:
        boundary=min(marked)
        for r in rows:
            if r['tarih_utc']>=boundary: r['asama']='playoff'
    return rows,dict(partial=bool(errors),errors=errors,months=len(links))
