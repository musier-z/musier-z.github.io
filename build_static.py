#!/usr/bin/env python3
"""Build a static snapshot of the Chinese mirror for GitHub Pages.

Pages cannot run server.py, so this script reuses the same RefreshCache rules
(public reads only, blockedPaths, 401/403 stop, retry backoff, ETag/304, stale
fallback) to snapshot the public data the pinned frontend requests, then writes a
self-contained site into --out. static-shim.js maps the frontend's /v1, /data and
/map-styles requests onto the snapshot files at runtime.

    python3 build_static.py --out dist --base /

Seed endpoints come from static-endpoints.json (recorded from the real frontend by
tools/discover_endpoints.py) plus every /data/*.json referenced by the bundles.
Follow-up requests (next pages, post details, images) are derived only from URLs
present in the fetched data. Nothing is invented and no request is disguised.
"""
import argparse
import concurrent.futures
import hashlib
import json
import mimetypes
import re
import shutil
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from refresh import RefreshCache, identity, load_config, timestamp

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
ORIGIN = 'https://robotaxitracker.com'
ROUTES = ['/vehicles', '/map', '/cameras', '/government', '/government/crashes',
          '/government/incidents', '/government/austin', '/government/cpuc', '/government/citations',
          '/permits', '/permits/california', '/permits/arizona', '/permits/texas', '/fleet', '/miles',
          '/spotted', '/sentiment', '/cities', '/compare', '/cybercab', '/cybercab-event',
          '/leaderboards', '/pricing', '/wait-times', '/stats', '/news', '/about', '/methodology',
          '/privacy', '/terms', '/signin', '/signup', '/submit']
IMAGE_RE = re.compile(r'/v1/[a-z]+-cameras/images/[0-9a-f]{64}|/v1/api/news-feed/images/[0-9a-f]{64}|/vehicles/web/[A-Za-z0-9._/-]+\.(?:webp|jpe?g|png|avif)')
POST_RE = re.compile(r'"postId"\s*:\s*"(\d+)"')
SKIP_PUBLIC = {'_audit.html', '_smoke.html'}


def canonical_key(path, body=None):
    """Must match canonical() in static-shim.js."""
    parts = urllib.parse.urlsplit(path)
    p = parts.path
    ignore = set()
    if p == '/v1/api/service-areas':
        ignore = {'v'}
    elif p == '/v1/api/texas-dmv' or p.startswith('/v1/api/texas-dmv/'):
        ignore = {'version'}
    pairs = sorted((k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if k not in ignore)
    q = lambda s: urllib.parse.quote(s, safe="-_.!~*'()")
    key = p + ('?' + '&'.join(q(k) + '=' + q(v) for k, v in pairs) if pairs else '')
    if body:
        key += '\n' + json.dumps(json.loads(body), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return key


def chinese_map_style(data):
    """Same label rewrite server.py applies to /map-styles/."""
    style = json.loads(data)
    def label(value):
        if isinstance(value, list):
            if value == ['coalesce', ['get', 'name:en'], ['get', 'name']]:
                return ['coalesce', ['get', 'name:zh'], ['get', 'name:zh-Hans'], ['get', 'name:en'], ['get', 'name']]
            return [label(v) for v in value]
        return value
    for layer in style.get('layers', []):
        layout = layer.get('layout', {})
        if 'text-field' in layout:
            layout['text-field'] = label(layout['text-field'])
    return json.dumps(style, ensure_ascii=False).encode()


class Snapshot:
    def __init__(self, cache_dir):
        self.config = load_config(str(ROOT / 'refresh-config.json'))
        self.allowed = json.loads((ROOT / 'read-queries.json').read_text())
        self.cache = RefreshCache(cache_dir, ORIGIN, self.config, self.allowed)
        self.results = {}
        self.blocked = set()
        self.stats = {'fetched': 0, 'reused': 0, 'failed': 0, 'blocked': 0}

    def fetch(self, path, body=None):
        """Return (data, meta) honoring the refresh policy; None when unavailable."""
        if body is not None:
            if path.split('?')[0] != '/v1/api/compat/query' or json.loads(body).get('name') not in self.allowed:
                return None
            body = body.encode() if isinstance(body, str) else body
        path, body, key = identity(path, body)
        cache = self.cache
        with cache.lock:
            meta = cache.entries.get(key)
            blocked = cache.is_blocked(meta or {'path': path})
            due = meta is None or not meta.get('bodyFile') or cache.due_at(meta) <= cache.clock()
        if blocked:
            self.blocked.add(urllib.parse.urlsplit(path).path)
            self.stats['blocked'] += 1
        elif due:
            outcome = cache._refresh(key, path, body)
            if outcome['outcome'] == 'blocked':
                self.blocked.add(urllib.parse.urlsplit(path).path)
                self.stats['blocked'] += 1
            elif outcome['outcome'] in ('failed', 'deferred'):
                self.stats['failed'] += 1
                print('  ! ', outcome['outcome'], path, outcome.get('error', ''), flush=True)
            else:
                self.stats['fetched'] += 1
        else:
            self.stats['reused'] += 1
        with cache.lock:
            meta = cache.entries.get(key)
            if not meta or not meta.get('bodyFile'):
                return None
            data = (cache.directory / meta['bodyFile']).read_bytes()
            item = (data, dict(meta), key, cache.headers(key, meta))
        self.results[canonical_key(path, body)] = item
        return item

    def run(self, seeds, max_pages, max_images):
        removed = self.cache.prune_failed_misses()
        if removed:
            print('pruned', removed, 'failed cache misses without body', flush=True)
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.config['workers'])
        def batch(items):
            return [r for r in pool.map(lambda e: (e, self.fetch(*e)), items)]
        done = batch(seeds)
        # Derived: follow nextCursor of unfiltered feeds, and post details.
        derived, pages = [], []
        for (path, body), item in done:
            if not item:
                continue
            text = item[0].decode('utf-8', 'replace')
            if path.startswith('/v1/api/x-sentiment') and '/posts/' not in path:
                derived += [('/v1/api/x-sentiment/posts/' + pid, None) for pid in dict.fromkeys(POST_RE.findall(text))]
            if path.startswith('/v1/camera-sightings?') and 'cursor=' not in path and '/timeline' not in path:
                pages.append((path, item))
        batch(list(dict.fromkeys(derived)))
        for path, item in pages:
            for _ in range(max_pages):
                try:
                    cursor = json.loads(item[0]).get('nextCursor')
                except ValueError:
                    cursor = None
                if not cursor:
                    break
                parts = urllib.parse.urlsplit(path)
                query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != 'cursor'] + [('cursor', cursor)]
                item = self.fetch(parts.path + '?' + urllib.parse.urlencode(query))
                if not item:
                    break
        # Images referenced by the snapshot (latest first, bounded).
        # Fetch with fewer workers and stop early on a 429 streak so one rate-limit
        # wave does not leave hundreds of failure-only metas in the Actions cache.
        images = []
        for data, meta, _, _ in list(self.results.values()):
            if 'json' in meta.get('contentType', ''):
                images += IMAGE_RE.findall(data.decode('utf-8', 'replace'))
        images = list(dict.fromkeys(images))[:max_images]
        consecutive_429 = 0
        stopped = False
        for path in images:
            if stopped:
                # Still publish images already in the Actions cache; do not hit origin.
                path_n, body_n, key = identity(path)
                with self.cache.lock:
                    meta = self.cache.entries.get(key)
                    if not meta or not meta.get('bodyFile'):
                        continue
                    data = (self.cache.directory / meta['bodyFile']).read_bytes()
                    item = (data, dict(meta), key, self.cache.headers(key, meta))
                self.results[canonical_key(path)] = item
                self.stats['reused'] += 1
                continue
            item = self.fetch(path)
            err = ''
            with self.cache.lock:
                meta = self.cache.entries.get(identity(path)[2], {})
                err = meta.get('lastError') or ''
            if 'HTTP 429' in err and not (item and item[0]):
                consecutive_429 += 1
                if consecutive_429 >= 5:
                    print('  !  stopping origin image fetch after repeated HTTP 429; keeping cached images', flush=True)
                    stopped = True
            else:
                consecutive_429 = 0
        pool.shutdown()


def seeds():
    items = [(e['path'], e.get('body')) for e in json.loads((ROOT / 'static-endpoints.json').read_text())]
    for file in sorted((PUBLIC / 'assets').glob('*.js')):
        for path in re.findall(r'["`](/data/[A-Za-z0-9_./-]+\.json)["`]', file.read_text(errors='replace')):
            items.append((path, None))
        for path in re.findall(r'(/vehicles/web/[A-Za-z0-9_.-]+\.(?:webp|png|jpe?g|avif))', file.read_text(errors='replace')):
            items.append((path, None))
    return list(dict.fromkeys(items))


def rewrite_bundle(text, base):
    """Point the pinned Vite/TanStack bundle at a sub-path (only when base != '/')."""
    text = text.replace('`/assets/', '`' + base + 'assets/').replace('"/assets/', '"' + base + 'assets/').replace('url(/assets/', 'url(' + base + 'assets/')
    text = text.replace('return`/`+e', 'return`' + base + '`+e')
    text = re.sub(r'\(\{routeTree:([A-Za-z_$][\w$]*),', lambda m: '({routeTree:' + m.group(1) + ',basepath:' + json.dumps(base.rstrip('/')) + ',', text)
    return text


def write_site(out, base, snap):
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(PUBLIC, out, ignore=lambda d, names: [n for n in names if n in SKIP_PUBLIC or n.startswith('._')])
    for name in ('zh-cn.css', 'refresh-ui.css', 'refresh-ui.js', 'translations.json', 'ui-strings.json', 'static-shim.js'):
        shutil.copy2(ROOT / name, out / name)
    zh = (ROOT / 'zh-cn.js').read_text()
    zh = zh.replace('.test(url.pathname)', '.test(__mirrorStrip(url.pathname))').replace('location.pathname', '__mirrorPath()')
    (out / 'zh-cn.js').write_text(zh)
    if base != '/':
        for file in list((out / 'assets').glob('*.js')) + list((out / 'assets').glob('*.mjs')) + list((out / 'assets').glob('*.css')):
            text = file.read_text(errors='surrogateescape')
            new = rewrite_bundle(text, base)
            if new != text:
                file.write_text(new, errors='surrogateescape')
    # Data snapshot.
    data_dir = out / 'data-snapshot'
    data_dir.mkdir()
    entries = {}
    for ckey, (data, meta, key, headers) in sorted(snap.results.items()):
        kind = meta.get('contentType', 'application/octet-stream')
        path = urllib.parse.urlsplit(meta['path']).path
        if path.startswith('/map-styles/'):
            data = chinese_map_style(data)
        ext = '.json' if 'json' in kind else (mimetypes.guess_extension(kind.split(';')[0].strip()) or '.bin')
        name = hashlib.sha256(ckey.encode()).hexdigest()[:32] + ext
        (data_dir / name).write_bytes(data)
        entries[ckey] = {'f': name, 't': kind, 'k': key, 's': headers['X-Mirror-Cache'],
                         'c': headers['X-Mirror-Checked-At'], 'm': headers['X-Mirror-Changed-At']}
    built = timestamp()
    # Only report keys actually published in this snapshot; orphan failure metas
    # left in the Actions cache must not inflate "等待重试" on the static panel.
    snapshot_keys = {key for _, _, key, _ in snap.results.values()}
    status = snap.cache.status(keys=snapshot_keys)
    hourly = 3600
    for group in status.get('groups', []):
        group['intervalSeconds'] = max(group['intervalSeconds'], hourly)
    status.update(schedulerRunning=True, job=None, refreshing=0, records=status.get('records', []),
                  manualAvailableAt='9999-12-31T00:00:00Z', lastSweepAt=built, staticBuild=True)
    payload = {'base': base, 'builtAt': built, 'origin': ORIGIN, 'entries': entries,
               'blocked': sorted(snap.blocked), 'status': status}
    (out / 'mirror-static.js').write_text('window.__MIRROR_STATIC__=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n')
    # Entry HTML for every public route (Pages has no SPA fallback except 404.html).
    html = (ROOT / 'index.html').read_text()
    head = ('<script src="{b}mirror-static.js?t={t}"></script>\n  <script src="{b}static-shim.js?v=1"></script>\n'
            '  <link rel="stylesheet" href="{b}static-mode.css?v=1">\n  ').format(b=base, t=int(time.time()))
    html = re.sub(r'(href|src)="/(?!/)', lambda m: m.group(1) + '="' + base, html)
    html = html.replace('<link rel="icon"', head + '<link rel="icon"', 1)
    shutil.copy2(ROOT / 'static-mode.css', out / 'static-mode.css')
    (out / 'index.html').write_text(html)
    (out / '404.html').write_text(html)
    for route in ROUTES:
        target = out / route.strip('/') / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html)
    (out / '.nojekyll').write_text('')
    (out / 'build-info.json').write_text(json.dumps({
        'builtAt': built, 'source': ORIGIN, 'attribution': 'Robotaxi Tracker by Ethan McKanna; Simplified Chinese mirror.',
        'entries': len(entries), 'blockedPaths': sorted(snap.blocked), 'stats': snap.stats}, ensure_ascii=False, indent=2))
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', default='dist')
    parser.add_argument('--base', default='/')
    parser.add_argument('--cache', default=str(ROOT / 'cache'))
    parser.add_argument('--max-pages', type=int, default=5)
    parser.add_argument('--max-images', type=int, default=400)
    parser.add_argument('--min-entries', type=int, default=30, help='fail the build if fewer data files are available')
    args = parser.parse_args()
    base = '/' + args.base.strip('/') + '/' if args.base.strip('/') else '/'
    started = time.time()
    snap = Snapshot(args.cache)
    snap.run(seeds(), args.max_pages, args.max_images)
    entries = write_site(Path(args.out).resolve(), base, snap)
    print('snapshot:', len(entries), 'files', snap.stats, 'blocked:', sorted(snap.blocked),
          'in %.0fs' % (time.time() - started), flush=True)
    if len(entries) < args.min_entries:
        raise SystemExit('too few data files; refusing to publish an empty snapshot')


if __name__ == '__main__':
    main()
