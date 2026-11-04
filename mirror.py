#!/usr/bin/env python3
"""Fetch public frontend assets and retain their exact hashed filenames."""
import concurrent.futures
import json
from pathlib import Path
import re
import sys
from server import ROOT, PUBLIC, ORIGIN, request

def asset_references(text):
    refs = set(re.findall(r'(?:\./|/)?assets/[A-Za-z0-9_./-]+\.(?:js|mjs|css|woff2)', text))
    refs |= {'assets/' + s for s in re.findall(r'["`\']\./([A-Za-z0-9_.-]+\.(?:js|mjs|css|woff2))["`\']', text)}
    refs |= set(re.findall(r'["`\'](/[\w/-]+\.(?:svg|png|webp|jpg|jpeg|avif|gif))["`\']', text))
    return {r.removeprefix('./').lstrip('/') for r in refs}

def download(path):
    target = PUBLIC / path
    if target.exists():
        data = target.read_bytes()
    else:
        for attempt in range(3):
            try:
                data, _ = request(ORIGIN + '/' + path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                break
            except Exception:
                if attempt == 2:
                    raise
    refs = asset_references(data.decode('utf-8', errors='replace')) if target.suffix in ('.js', '.mjs', '.css', '.html') else set()
    return refs

if __name__ == '__main__':
    original = Path('/tmp/robotaxi-original.html').read_text()
    pending = asset_references(original) | {'assets/index-bWtXtLiO.js', 'favicon-32.png', 'icon-96.png', 'apple-touch-icon.png', 'autolane-logo.svg'}
    done, failures = set(), []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        while pending:
            batch = sorted(pending - done)
            if not batch:
                break
            done.update(batch)
            pending = set()
            jobs = {pool.submit(download, p): p for p in batch}
            for f in concurrent.futures.as_completed(jobs):
                path = jobs[f]
                try:
                    pending.update(f.result() - done)
                except Exception as exc:
                    failures.append(path)
                    print('FAILED', path, str(exc)[:100], flush=True)
            print('Mirrored', len(done) - len(failures), 'assets;', len(pending), 'next;', len(failures), 'failed', flush=True)
    (ROOT / 'mirror-manifest.json').write_text(json.dumps({'source': ORIGIN, 'capturedAt': '2026-11-03', 'assets': sorted(done - set(failures)), 'failed': failures}, indent=2))
    # Extract static read-query names from the original compiled frontend.
    names = set()
    for file in (PUBLIC / 'assets').glob('*.js'):
        source = file.read_text(errors='replace')
        names.update(re.findall(r'["`]((?:queries|query)/[A-Za-z0-9_/:.-]+)["`]', source))
    (ROOT / 'read-queries.json').write_text(json.dumps(sorted(names), indent=2))
    print('Done. Public query names:', len(names), flush=True)
