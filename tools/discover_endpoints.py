#!/usr/bin/env python3
"""Discover the public data requests the pinned frontend makes on each route.

Run against a local `python3 server.py --port 8765` (needs `pip install playwright`
and a Chrome/Chromium). Writes static-endpoints.json, which build_static.py snapshots.
Only records requests the original frontend itself issues; nothing is invented.
"""
import json
import sys
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765'
ROUTES = ['/', '/vehicles', '/map', '/cameras', '/government', '/government/crashes',
          '/government/incidents', '/government/austin', '/government/cpuc', '/government/citations',
          '/permits', '/permits/california', '/permits/arizona', '/permits/texas', '/fleet', '/miles',
          '/spotted', '/sentiment', '/cities', '/compare', '/cybercab', '/cybercab-event',
          '/leaderboards', '/pricing', '/wait-times', '/stats', '/news', '/about', '/methodology',
          '/privacy', '/terms']
EXTRA = [r for r in sys.argv[2:]]
PREFIXES = ('/v1/', '/data/', '/map-styles/')


def main():
    found = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1366, 'height': 900})

        def record(request):
            url = urllib.parse.urlsplit(request.url)
            if url.netloc != urllib.parse.urlsplit(BASE).netloc or not url.path.startswith(PREFIXES):
                return
            if url.path.startswith(('/v1/api/auth/', '/v1/api/account')):
                return
            path = url.path + ('?' + url.query if url.query else '')
            body = request.post_data if request.method == 'POST' else None
            key = (path, body)
            if key not in found:
                found[key] = {"path": path, "body": body}
        page.on('request', record)
        for route in ROUTES + EXTRA:
            try:
                page.goto(BASE + route, wait_until='load', timeout=60000)
                for _ in range(6):
                    page.mouse.wheel(0, 1500)
                    time.sleep(1.5)
                time.sleep(4)
            except Exception as exc:
                print('route failed', route, exc, flush=True)
            print(route, len(found), flush=True)
        browser.close()
    # Per-snapshot follow-ups (images, next pages, post details) are derived by
    # build_static.py from the fetched data, so they are not pinned here.
    dynamic = ('/images/', 'cursor=', '/x-sentiment/posts/', '/vehicles/web/')
    items = sorted((e for e in found.values() if not any(d in e['path'] for d in dynamic)), key=lambda x: (x['path'], x['body'] or ''))
    (ROOT / 'static-endpoints.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n')
    print('endpoints:', len(items))


if __name__ == '__main__':
    main()
