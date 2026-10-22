import hashlib
import json
import subprocess
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

AGENT = 'BBTahminResearch/0.1 (local basketball research)'
# Görev üst sınırı dakikada 15; ilk koşu 15/dk ile 429 aldığı için daha düşük tutulur.
MIN_SPACING = 6.1
PER_MINUTE = 10

class CachedHTTP:
    def __init__(self):
        self.calls = deque()
        self.last_call = 0
        self.robots = {}
        self.events = []
        self.blocked = set()
        self.last_url = None  # yönlendirme sonrası son adres

    def get(self, url, nba=False, robots=True, refresh=False):
        key = hashlib.sha256(url.encode()).hexdigest()
        path = Path('data/raw') / urlparse(url).netloc / key
        path.parent.mkdir(parents=True, exist_ok=True)
        meta_path = path.with_suffix('.json')
        if not refresh and path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text('utf8'))
            if meta['status'] == 200 or (meta['status'] == 404 and url.endswith('/robots.txt')):
                self.events.append(dict(url=url, cached=True, status=meta['status']))
                self.last_url = meta.get('url', url)
                return path.read_bytes()
            if meta['status']==429: self.blocked.add(urlparse(url).netloc)
            raise RuntimeError(f"Önbellekte HTTP {meta['status']}: {url}")
        if urlparse(url).netloc in self.blocked:
            raise RuntimeError(f'HTTP 429 sonrası bu oturumda kaynak durduruldu: {url}')
        if robots:
            origin = f'{urlparse(url).scheme}://{urlparse(url).netloc}'
            if origin not in self.robots:
                raw = self.get(origin+'/robots.txt', nba=nba, robots=False)
                parser = RobotFileParser()
                parser.parse(raw.decode('utf8', errors='replace').splitlines())
                self.robots[origin] = parser
            if not self.robots[origin].can_fetch(AGENT, url):
                raise RuntimeError(f'robots.txt engeli: {url}')
        if nba:
            now = time.monotonic()
            while self.calls and now-self.calls[0] >= 60:
                self.calls.popleft()
            delay = max(0, MIN_SPACING-(now-self.last_call))
            if len(self.calls) >= PER_MINUTE:
                delay = max(delay, 60.1-(now-self.calls[0]))
            time.sleep(delay)
            self.last_call = time.monotonic()
            self.calls.append(self.last_call)
        result = subprocess.run(['node','scripts/fetch.mjs',url,str(path),AGENT],
                                capture_output=True,text=True,timeout=55)
        if result.returncode:
            raise RuntimeError(f'{url}: {result.stderr}')
        meta = json.loads(result.stdout)
        meta['requested_url'] = url
        self.last_url = meta.get('url', url)
        meta_path.write_text(json.dumps(meta,indent=2),'utf8')
        self.events.append(dict(url=url,cached=False,status=meta['status']))
        if meta['status'] == 429:
            self.blocked.add(urlparse(url).netloc)
        if meta['status'] == 404 and url.endswith('/robots.txt'):
            return b''
        if meta['status'] != 200:
            raise RuntimeError(f"HTTP {meta['status']}: {url}")
        return path.read_bytes()
