#!/usr/bin/env python3
"""Pre-cache public JSON datasets referenced by the mirrored frontend."""
import concurrent.futures
import json
import re
from pathlib import Path
from server import ROOT, PUBLIC, upstream

paths = set()
for file in (PUBLIC / 'assets').glob('*.js'):
    paths.update(re.findall(r'["`](/data/[A-Za-z0-9_./-]+\.json)["`]', file.read_text(errors='replace')))

def fetch(path):
    for attempt in range(3):
        try:
            data, _ = upstream(path)
            return {'path': path, 'ok': True, 'bytes': len(data)}
        except Exception as exc:
            error = str(exc)[:150]
    return {'path': path, 'ok': False, 'error': error}

if __name__ == '__main__':
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for item in pool.map(fetch, sorted(paths)):
            results.append(item)
            if not item['ok']:
                print('Failed', item['path'], item['error'], flush=True)
            elif len(results) % 10 == 0:
                print('Cached', len(results), '/', len(paths), flush=True)
    (ROOT / 'data-manifest.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print('Complete:', sum(item['ok'] for item in results), '/', len(results), flush=True)
