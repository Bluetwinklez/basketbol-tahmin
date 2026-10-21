"""Write environment, reference-path and data-identity evidence (offline; no network)."""
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

folder = Path('docs/kanit')
folder.mkdir(parents=True, exist_ok=True)

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return (result.stdout + result.stderr).strip() or f'(çıktı yok, çıkış kodu {result.returncode})'

reference = Path('data/raw/basketbolbet/main.py')
similar = sorted(str(p).replace('\\', '/') for p in Path('data/raw').iterdir() if 'basket' in p.name.lower() and 'reference' not in p.name.lower())
lines = [
    f'Zaman (UTC): {datetime.now(timezone.utc).isoformat()}',
    f'Çalışma klasörü: {Path.cwd()}',
    f'Python: {platform.python_version()} ({platform.python_implementation()}), node: {run(["node", "--version"])}',
    '',
    '$ git check-ignore -v data/raw/basketbolbet/main.py',
    run(['git', 'check-ignore', '-v', 'data/raw/basketbolbet/main.py']),
    '$ git check-ignore -v data/maclar.parquet .venv',
    run(['git', 'check-ignore', '-v', 'data/maclar.parquet', '.venv']),
    '',
    f'data/raw/basketbolbet/main.py var mı: {reference.exists()}',
    f'data/raw altında basketbol adlı benzer klasörler (basketball-reference hariç): {similar or "yok"}',
    f'data/raw içeriği: {sorted(p.name for p in Path("data/raw").iterdir())}',
    '',
    'Not: .venv/Scripts/python.exe bu oturumda etkileşimli onay istediği için komutlar aynı sürüm sistem CPython ile',
    '.runtime/run.py üzerinden (.venv site-packages + src yolu eklenerek) çalıştırıldı.',
]
(folder / 'ortam.txt').write_text('\n'.join(lines) + '\n', 'utf8')

data = Path('data/maclar.parquet')
games = pd.read_parquet(data)
identity = dict(sha256=hashlib.sha256(data.read_bytes()).hexdigest(), bytes=data.stat().st_size, rows=len(games),
                timestamp=datetime.now(timezone.utc).isoformat())
(folder / 'veri_kimligi.json').write_text(json.dumps(identity, indent=2), 'utf8')
print('\n'.join(lines))
print(json.dumps(identity, indent=2))
