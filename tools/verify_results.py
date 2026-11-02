#!/usr/bin/env python3
"""Audit archived results against the unchanged school analyser and source hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analyse_results import analyse_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=ROOT / 'results/final')
    args = parser.parse_args()
    folder = args.results.resolve()
    metadata = json.loads((folder / 'metadata.json').read_text())
    for name, digest in metadata['sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(f'Source changed since measurement: {name}; rerun validation before claiming these results.')
    checked = 0
    scores = {}
    observations = {}
    with zipfile.ZipFile(folder / 'raw_results.zip') as archive, tempfile.TemporaryDirectory() as tmp:
        if archive.testzip() is not None: raise SystemExit('Corrupt raw-results archive')
        for name in sorted(archive.namelist()):
            if not name.startswith(('raw/', 'comparison/')) or not name.endswith('.json') or '_run' not in name:
                continue
            recorded = json.loads(archive.read(name))
            csv_name = name[:-5] + '.csv'
            path = Path(tmp) / Path(csv_name).name
            path.write_bytes(archive.read(csv_name))
            clients = recorded['clients']
            calculated = analyse_file(path,
                expected_finals=recorded['expected_finals_total'] // clients,
                expected_updates=recorded['expected_updates_total'] // clients,
                fresh_threshold_ms=500.0)
            if calculated != recorded:
                keys = [key for key in calculated if calculated[key] != recorded.get(key)]
                raise SystemExit(f'CSV/JSON mismatch: {name}: {keys}')
            checked += 1
            if name.startswith('raw/'):
                group = Path(name).name.split('_run')[0]
                scores.setdefault(group, []).append(recorded['final_completeness_pct'])
                observations.setdefault(group, []).append(recorded)
                if recorded['duplicates'] or recorded['stale'] or recorded['connection_errors']:
                    raise SystemExit(f'Correctness/connection errors in {name}')
                if group in ('t1', 't2') and recorded['normal_update_coverage_pct'] != 100:
                    raise SystemExit(f'Unconstrained revisions were suppressed in {name}')
        for test in ('t1','t2','t3','t4','t5'):
            if len(scores.get(test, [])) < 3:
                raise SystemExit(f'Missing required repeated results: {test}')
    published = json.loads((folder / 'summary.json').read_text())
    for group, rows in observations.items():
        for metric, value in published['tests'][group]['medians'].items():
            if statistics.median(row[metric] for row in rows) != value:
                raise SystemExit(f'Published median mismatch: {group} {metric}')
    print(f'PASS: {checked} archived run summaries reproduce exactly from their CSVs.')
    print('PASS: measured source hashes match the current project; no duplicate/stale/connection errors; T1/T2 full revision coverage.')
    for name, values in scores.items():
        print(name, ', '.join(f'{value:.2f}%' for value in values))
    if any(value < 99 for values in scores.values() for value in values):
        print('NOTE: some workloads are below 99% completeness. Review the report; this audit does not hide or relabel them.')

if __name__ == '__main__':
    main()
