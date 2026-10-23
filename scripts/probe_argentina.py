"""Read public source structure before implementing the Liga Nacional importer."""
import json
import re
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
from bs4 import BeautifulSoup

BASE='https://basketball.realgm.com/international/league/58/Argentinian-Liga-A'
urls=['https://www.laliganacional.com.ar/laliga/fixture',
      'https://www.laliganacional.com.ar/js/funciones.js',
      'https://www.laliganacional.com.ar/laliga/tabla-posiciones']
results=[]
for url in urls:
    item=dict(url=url,captured_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'bbtahmin/0.3 research'})
        with urllib.request.urlopen(request,timeout=30) as response:raw=response.read(6000000)
        soup=BeautifulSoup(raw,'html.parser')
        if url.endswith('.js'):
            item['javascript']=raw.decode('utf8')[:50000];results.append(item);continue
        item.update(title=soup.title.get_text(' ',strip=True) if soup.title else None,
                    headings=[x.get_text(' ',strip=True) for x in soup.select('h1')],
                    tables=[dict(rows=len(table.select('tr')),header=table.select_one('tr').get_text(' ',strip=True),
                                 sample=[str(tr) for tr in table.select('tr')[1:3]]) for table in soup.select('table')[:3]],
                    links=[dict(text=a.get_text(' ',strip=True),href=a.get('href')) for a in soup.select('a[href]') if '/schedule' in a.get('href','')][:30],
                    scripts=[s.get('src') for s in soup.select('script[src]')],
                    selects=[dict(name=s.get('name'),id=s.get('id'),selected=[o.get_text(' ',strip=True) for o in s.select('option[selected]')]) for s in soup.select('select')],
                    inline_scripts=[s.get_text()[:20000] for s in soup.select('script:not([src])')],
                    inputs=[str(s) for s in soup.select('input')],
                    game_links=[str(a) for a in soup.select('a[href]') if any(k in a.get('href','') for k in ('partido','fixture','equipo','temporada'))][:40],
                    data_elements=[str(a)[:3000] for a in soup.select('[onclick], [data-id]')][:30],
                    text=soup.get_text(' ',strip=True)[-18000:])
    except Exception as exc:item['error']=f'{type(exc).__name__}: {exc}'
    results.append(item)
out=Path('docs/kanit/argentina');out.mkdir(parents=True,exist_ok=True)
(out/'probe.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps([dict(url=x['url'],error=x.get('error'),headings=x.get('headings')) for x in results]))
