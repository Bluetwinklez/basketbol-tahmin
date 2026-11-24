"""Audit saved retrospective predictions against fixed, paired comparators."""
import gzip
import hashlib
import json
from pathlib import Path
from bbtahmin.football.data import write_json
from bbtahmin.football.challenger import VARIANTS
from bbtahmin.football.evaluation_audit import paired_accuracy

if __name__ == '__main__':
    source = Path('docs/kanit/requested_football/paired_results.json.gz')
    raw = source.read_bytes()
    rows = json.loads(gzip.decompress(raw))
    prior = Path('docs/kanit/requested_football/cohort_audit_20261106.json')
    audit = json.loads(prior.read_text())
    if audit['source_sha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('Saved prediction evidence changed')
    report = paired_accuracy(rows, VARIANTS, audit['simple_baselines']['event_ids'])
    report.update(source_file=str(source), source_sha256=hashlib.sha256(raw).hexdigest(),
                  metrics_and_calibration_file=str(prior),
                  metrics_and_calibration_sha256=hashlib.sha256(prior.read_bytes()).hexdigest(),
                  new_matches=0, official_results_verified=False,
                  limitation='Retrospective BR2 2024 community results. Historical publication times unknown. No independent official verification, refit, promotion or forecast edits.')
    write_json('docs/kanit/requested_football/paired_accuracy_20261116.json', report)
    print(json.dumps(report['comparisons'], indent=2))
