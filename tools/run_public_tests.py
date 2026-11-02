#!/usr/bin/env python3
"""Orchestrate the unchanged school harness; keep one readable final result set."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import threading
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
METRICS = ['final_completeness_pct', 'fresh_pct', 'fresh_final_pct',
           'normal_update_coverage_pct', 'p50_ms', 'p95_ms', 'p99_ms']
TESTS = {
    't1': ['--clients', '20', '--duration', '20'],
    't2': ['--clients', '100', '--duration', '40'],
    't3': ['--clients', '100', '--duration', '60', '--slow-percent', '10', '--slow-ms', '500'],
    't4': ['--clients', '100', '--duration', '60', '--disconnect-percent', '20', '--disconnect-at', '15', '--disconnect-seconds', '5'],
    't5': ['--clients', '100', '--duration', '40'],
    # Additional documented stress experiment, separate from mandatory T1-T5.
    'bandwidth': ['--clients', '100', '--duration', '40'],
}


def summarize(output, runs):
    summaries = {}
    for name in TESTS:
        files = sorted((output / 'raw').glob(f'{name}_run*.json'))
        if not files:
            continue
        rows = [json.loads(p.read_text()) for p in files]
        summaries[name] = {
            'runs': len(rows),
            'final_completeness_runs': [r['final_completeness_pct'] for r in rows],
            'medians': {key: statistics.median(r[key] for r in rows) for key in METRICS},
            'duplicates': sum(r['duplicates'] for r in rows),
            'stale': sum(r['stale'] for r in rows),
            'connection_errors': sum(r['connection_errors'] for r in rows),
        }
        for population in ('normal_clients', 'slow_clients'):
            if all(population in row for row in rows):
                summaries[name][population] = {
                    key: statistics.median(row[population][key] for row in rows)
                    for key in ('p50_ms', 'p95_ms', 'fresh_pct', 'messages')}
        if all('recovery_p95_ms' in row for row in rows):
            summaries[name]['recovery_p95_ms'] = statistics.median(row['recovery_p95_ms'] for row in rows)
    comparison = {}
    before = [json.loads(p.read_text()) for p in sorted((output / 'comparison').glob('before_t5_run*.json'))]
    if before and 't5' in summaries:
        comparison = {
            key: {'before': statistics.median(row[key] for row in before),
                  'after': summaries['t5']['medians'][key]}
            for key in METRICS}
        with (output / 'comparison.csv').open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['metric', 'before_median', 'after_median'])
            writer.writerows((key, row['before'], row['after']) for key, row in comparison.items())
    document = {'tests': summaries, 'comparison_t5': comparison,
                'note': 'Medians are per metric across independent runs; individual runs remain in the raw archive.'}
    (output / 'summary.json').write_text(json.dumps(document, indent=2) + '\n')
    with (output / 'medians.csv').open('w', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(['test', *METRICS])
        writer.writerows([name, *[row['medians'][key] for key in METRICS]] for name, row in summaries.items())
    lines = ['# Final Ubuntu test results', '',
             'Start here. `medians.csv` contains the headline metrics; `summary.json` includes per-run completeness and isolation/recovery results. Full measurements and logs are in `raw_results.zip`.', '',
             '| Test | Final completeness, each run | Median completeness | Fresh finals | Revision coverage |',
             '|---|---|---:|---:|---:|']
    for name, row in summaries.items():
        m = row['medians']; scores = ', '.join(f'{x:.2f}%' for x in row['final_completeness_runs'])
        lines.append(f"| {name.upper()} | {scores} | {m['final_completeness_pct']:.2f}% | {m['fresh_final_pct']:.2f}% | {m['normal_update_coverage_pct']:.2f}% |")
    lines += ['', 'T1-T5 use the school public workloads without measurement changes. BANDWIDTH is an additional 512 kbit/s experiment, not a sixth required public test.', '',
              'Revision suppression under overload and finals recovered after an offline period explain why coverage/freshness need not be 100%. Check normal T1/T2 coverage separately. Public results do not guarantee hidden-test marks.', '',
              'The before/after comparison uses the earlier sender and the updated sender on the same VM and persistent filesystem with the same T5 settings. See `comparison.csv`.', '',
              'The archive includes exact commands, hashes, all raw CSV/JSON, network-profile verification, resource samples and check logs. Review `metadata.json` for check return codes. A file-presence check does not establish that team declarations or video/viva work are complete.']
    (output / 'SUMMARY.md').write_text('\n'.join(lines) + '\n')
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results/final')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--port', type=int, default=19877)
    parser.add_argument('--extended', action='store_true', help='also run the separate 512 kbit/s bandwidth experiment')
    parser.add_argument('--summarize', action='store_true', help='summarize an unpacked raw result set without rerunning tests')
    args = parser.parse_args()
    if args.runs < 3:
        parser.error('Use at least three independent runs for the assignment report')
    output = (ROOT / args.output).resolve()
    if args.summarize:
        summarize(output, args.runs); return
    if sys.platform != 'linux':
        parser.error('Run networking experiments inside Ubuntu, not on macOS')
    subprocess.run(['sudo', '-n', 'true'], check=True)  # Run sudo -v before starting.
    os.chdir(ROOT)
    for child in ('raw', 'logs'):
        (output / child).mkdir(parents=True, exist_ok=True)
    metadata = {'platform': platform.platform(), 'python': sys.version,
                'start_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'commands': {}, 'returncodes': {},
                'sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in [ROOT / 'solution_server.py', *(ROOT / 'server').glob('*.py'), ROOT / 'run_demo.py', ROOT / 'caption_source.py', ROOT / 'load_clients.py', ROOT / 'analyse_results.py', ROOT / 'tools/run_public_tests.py']}}
    resources, done = [], threading.Event()
    phase = 'checks'
    def sample():
        while not done.wait(1):
            for proc in Path('/proc').iterdir():
                if not proc.name.isdigit(): continue
                try:
                    if b'solution_server.py' not in (proc / 'cmdline').read_bytes().split(b'\0'): continue
                    fields = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
                    resources.append([phase, time.time(), proc.name, fields.get('VmRSS', '').strip()])
                except OSError: pass
    monitor = threading.Thread(target=sample, daemon=True); monitor.start()
    def execute(name, command):
        print(f'START {name}', flush=True)
        metadata['commands'][name] = command
        with (output / 'logs' / f'{name}.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
        metadata['returncodes'][name] = result.returncode
        print(f'END {name}: returncode={result.returncode}', flush=True)
        (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
        return result.returncode
    def reset():
        subprocess.run(['sudo', '-n', 'bash', 'network_profiles/reset.sh', 'lo'], check=True, stdout=subprocess.DEVNULL)
    try:
        if execute('unit_tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']):
            raise RuntimeError('Unit tests failed; public results would not validate a broken build')
        execute('startup', [sys.executable, 'submission_check.py', '--port', str(args.port + 1)])
        execute('submission_files', [sys.executable, 'submission_check.py', '--final', '--port', str(args.port + 1)])
        # Check the changed policy on the impaired link before the remaining runs.
        names = ['t2'] + (['bandwidth'] if args.extended else []) + ['t5', 't1', 't3', 't4']
        for name in names:
            phase = name; reset()
            if name == 't5':
                subprocess.run(['sudo', '-n', 'bash', 'network_profiles/delay_loss.sh', 'lo'], check=True)
            elif name == 'bandwidth':
                subprocess.run(['sudo', '-n', 'tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'tbf', 'rate', '512kbit', 'burst', '32kbit', 'latency', '400ms'], check=True)
            with (output / 'logs' / f'{name}_qdisc.txt').open('w') as stream:
                subprocess.run(['tc', '-s', 'qdisc', 'show', 'dev', 'lo'], stdout=stream, check=True)
            command = [sys.executable, '-u', 'run_demo.py', *TESTS[name], '--runs', str(args.runs), '--port', str(args.port), '--quiet-server', '--output-stem', str(output / 'raw' / name)]
            if execute(name, command):
                raise RuntimeError(f'{name} failed; see the log before treating partial results as complete')
            with (output / 'logs' / f'{name}_qdisc_after.txt').open('w') as stream:
                subprocess.run(['tc', '-s', 'qdisc', 'show', 'dev', 'lo'], stdout=stream, check=True)
    finally:
        reset(); done.set(); monitor.join(timeout=3)
        with (output / 'logs' / 'server_resources.csv').open('w', newline='') as stream:
            writer = csv.writer(stream); writer.writerow(['test', 'time', 'pid', 'rss']); writer.writerows(resources)
        with (output / 'logs' / 'network_after.txt').open('w') as stream:
            subprocess.run(['tc', 'qdisc', 'show', 'dev', 'lo'], stdout=stream)
        metadata['end_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    summarize(output, args.runs)
    with zipfile.ZipFile(output / 'raw_results.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for child in ('raw', 'logs', 'comparison'):
            for path in sorted((output / child).rglob('*')):
                if path.is_file(): archive.write(path, str(path.relative_to(output)))
        archive.write(output / 'metadata.json', 'metadata.json')
    for child in ('raw', 'logs', 'comparison'):
        shutil.rmtree(output / child, ignore_errors=True)
    print(f'FINISHED: {output / "SUMMARY.md"}; network reset', flush=True)

if __name__ == '__main__':
    main()
