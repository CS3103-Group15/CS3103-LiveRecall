#!/usr/bin/env python3
"""Create a clean source/results ZIP, excluding environments and ad-hoc files."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ['solution_server.py', 'requirements.txt', 'client/index.html', 'client/app.js',
            'README.md', 'AI_USAGE.md', 'CONTRIBUTIONS.md', 'report.pdf',
            'results/final/SUMMARY.md', 'results/final/summary.json', 'results/final/raw_results.zip']
ROOT_FILES = {'solution_server.py', 'requirements.txt', 'caption_source.py', 'load_clients.py',
              'run_demo.py', 'analyse_results.py', 'submission_check.py', 'monitor_server.py',
              'sample_transcript.txt', 'PUBLIC_TESTS.md', 'README.md', 'AI_USAGE.md', 'CONTRIBUTIONS.md', 'report.pdf'}
DIRECTORIES = ['server', 'client', 'tests', 'tools', 'docs', 'network_profiles', 'results/final']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-team-draft', action='store_true', help='make a review package while contribution agreement is pending')
    args = parser.parse_args()
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    if missing: parser.error('Missing required files: ' + ', '.join(missing))
    pending = 'Pending team agreement' in (ROOT / 'CONTRIBUTIONS.md').read_text()
    if pending and not args.allow_team_draft:
        parser.error('Team contributions are not agreed. Fill CONTRIBUTIONS.md or use --allow-team-draft for a clearly labelled review package.')
    target = args.output or ROOT / 'dist' / ('LiveRecall_Review_Package.zip' if pending else 'LiveRecall_Submission.zip')
    target = target.resolve(); target.parent.mkdir(parents=True, exist_ok=True)
    paths = {ROOT / name for name in ROOT_FILES if (ROOT / name).is_file()}
    for directory in DIRECTORIES:
        for p in (ROOT / directory).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc', '.pyo'}:
                paths.add(p)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    manifest = {'based_on_commit': commit.stdout.strip() if commit.returncode == 0 else None,
                'source': 'Current working tree, including uncommitted changes',
                'team_contributions_pending': pending, 'sha256': hashes,
                'excluded': ['.git', '.venv', '__pycache__', 'ad-hoc results', 'credentials and unrelated VM files']}
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(paths): archive.write(p, str(p.relative_to(ROOT)))
        archive.writestr('PACKAGE_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    print(target)
    if pending: print('Review package: team contribution details still need agreement; the required video/viva are separate human deliverables.')

if __name__ == '__main__':
    main()
