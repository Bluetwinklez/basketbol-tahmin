"""Offline structural audit of the historical, community TR2 archive."""
import gzip
import hashlib
import json
from pathlib import Path
from bbtahmin.football.data import write_json
from bbtahmin.football.turkey_second import validate_2019

if __name__ == '__main__':
    path = Path('data/football/TR2_2019-20.json.gz')
    raw = path.read_bytes()
    payload = json.loads(gzip.decompress(raw))
    audit = validate_2019(payload['rows'])
    audit.update(archive=str(path), archive_sha256=hashlib.sha256(raw).hexdigest(),
                 source_url=payload['source_url'], license=payload['license'],
                 official_results_verified=False, new_matches=0,
                 note='Structural completeness only, not independent score verification or evidence of predictive improvement. No downloads or archive writes.')
    write_json('docs/kanit/football/TR2_2019-20_structure.json', audit)
    print(json.dumps(audit, indent=2))
