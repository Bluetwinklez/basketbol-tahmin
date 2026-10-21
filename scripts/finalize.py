"""Regenerate the report and write the file manifest / code identity / completion record from real outputs."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from xml.etree import ElementTree

from bbtahmin.report import write_report

write_report()
folder = Path('docs/kanit')
files = set(subprocess.check_output(['git', 'diff', '--name-only'], text=True).splitlines())
files.update(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines())
files.add('docs/kanit/degisen_dosyalar.txt')
(folder / 'degisen_dosyalar.txt').write_text('\n'.join(sorted(files)) + '\n', 'utf8')
identity = {str(p).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
            for root in ['src', 'tests', 'scripts'] for p in sorted(Path(root).rglob('*.py'))}
(folder / 'kod_kimligi.json').write_text(json.dumps(identity, indent=2), 'utf8')
suite = ElementTree.parse(folder / 'pytest.xml').getroot().find('testsuite').attrib
negative = ElementTree.parse(folder / 'negatif_kontrol.xml').getroot().find('testsuite').attrib
record = dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              audit=json.loads((folder / 'dogrulama.json').read_text('utf8')),
              pytest=dict(tests=int(suite['tests']), failures=int(suite['failures']), errors=int(suite['errors']),
                          skipped=int(suite['skipped'])),
              negative_control=dict(tests=int(negative['tests']), failures=int(negative['failures']),
                                    expected='failure: deliberately leaky feature must be detected'))
(folder / 'tamamlanma.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), 'utf8')
print(json.dumps(record, ensure_ascii=False, indent=2))
