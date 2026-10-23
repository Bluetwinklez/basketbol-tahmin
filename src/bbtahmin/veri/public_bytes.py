"""Bounded, cached public GETs for domestic JSON and spreadsheet feeds."""
import hashlib
import urllib.request
from pathlib import Path


def fetch_bytes(url, refresh=False, headers=None):
    path = Path('data/raw/domestic_feeds')/(hashlib.sha256(url.encode()).hexdigest()+'.bin')
    if refresh or not path.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'bbtahmin research', **(headers or {})})
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError('Domestic response exceeds limit')
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.part'); temp.write_bytes(raw); temp.replace(path)
    return path.read_bytes()
