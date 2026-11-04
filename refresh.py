"""Public-read cache with bounded refresh, conditional requests and stale fallback.

One manager/server process owns a cache directory. Metadata atomically points to
a complete payload, so an interrupted update cannot destroy the last good copy.
"""
import concurrent.futures
import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path


LABELS = {
    'camera': '摄像头最新发现', 'wait': '候车时间',
    'fleet': '车辆、排行榜与摄像头统计', 'news': '新闻',
    'hourly': '得州登记、服务范围、价格与舆情',
    'history': '历史统计、其他政府数据与周报',
    'geography': '人口地理与地图样式', 'archive': '历史分页与单条帖子',
}
DEFAULTS = {
    'enabled': True, 'workers': 3, 'schedulerSeconds': 15,
    'requestTimeoutSeconds': 25, 'retryBaseSeconds': 60,
    'retryMaxSeconds': 3600, 'manualCooldownSeconds': 60,
    'blockedPaths': [],
    'intervalsSeconds': dict(camera=60, wait=120, fleet=300, news=1800,
                             hourly=3600, history=21600, geography=86400, archive=86400),
}


def timestamp(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def epoch(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (ValueError, AttributeError, TypeError):
        return 0


def identity(path, body=None):
    parts = urllib.parse.urlsplit(path)
    if parts.scheme or parts.netloc or not path.startswith('/') or path.startswith('//'):
        raise ValueError('只允许原站公开数据路径')
    pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    # Only known cache-busting parameters are removed; filters and cursors stay.
    ignore = {'v'} if parts.path == '/v1/api/service-areas' else set()
    if parts.path == '/v1/api/texas-dmv' or parts.path.startswith('/v1/api/texas-dmv/'):
        ignore = {'version'}
    query = urllib.parse.urlencode(sorted((k, v) for k, v in pairs if k not in ignore))
    path = parts.path + ('?' + query if query else '')
    if body is not None:
        body = json.dumps(json.loads(body), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return path, body, hashlib.sha256(path.encode() + (body or b'')).hexdigest()


def category(path, body=None, kind=''):
    parts = urllib.parse.urlsplit(path)
    p = parts.path
    query = dict(urllib.parse.parse_qsl(parts.query))
    if kind.startswith('image/') or p.startswith('/vehicles/web/') or p.endswith(('.webp', '.jpg', '.jpeg', '.png', '.svg', '.avif', '.gif', '.ico')):
        return None, False
    if not p.startswith(('/v1/', '/data/', '/map-styles/')):
        return None, False
    if p.startswith(('/v1/api/auth/', '/v1/api/account')):
        return None, False
    if any(k in query for k in ('cursor', 'before', 'after', 'offset', 'page')) or '/x-sentiment/posts/' in p:
        return 'archive', False
    if p.startswith('/v1/camera-sightings') or '-cameras' in p:
        return ('fleet' if p.endswith(('/hourly', '/timeline', '/area-stats')) else 'camera'), True
    if '/wait-time/' in p:
        return 'wait', True
    if p == '/v1/api/compat/query':
        payload = json.loads(body or '{}')
        name = payload.get('name', '')
        if 'Pricing' in name:
            return 'hourly', True
        if any(k in payload.get('args', {}) for k in ('cursor', 'offset', 'page', 'paginationOpts')):
            return 'archive', False
        return 'fleet', ':getLeaderboard' in name
    if 'news-feed' in p:
        return 'news', True
    if ('/compat/vehicles' in p or '/leaderboards/' in p or '/events/' in p):
        return 'fleet', True
    if ('/texas-dmv' in p or '/x-sentiment' in p or '/service-area' in p
            or p.endswith(('/tesla-robotaxi-fleet.json', '/us-fleet-estimates.json'))):
        return 'hourly', True
    if '/population-' in p or p.startswith('/map-styles/'):
        return 'geography', True
    return ('history' if p.startswith('/data/') or '/nhtsa/' in p or '/cpuc/' in p else 'hourly'), True


def load_config(path=None):
    config = {**DEFAULTS, 'intervalsSeconds': DEFAULTS['intervalsSeconds'].copy()}
    if path:
        supplied = json.loads(Path(path).read_text())
        unknown = set(supplied) - set(config)
        if unknown:
            raise ValueError('未知刷新配置：' + ', '.join(sorted(unknown)))
        intervals = supplied.pop('intervalsSeconds', {})
        if set(intervals) - set(LABELS):
            raise ValueError('刷新分类无效')
        config.update(supplied)
        config['intervalsSeconds'].update(intervals)
    if not isinstance(config['enabled'], bool):
        raise ValueError('enabled 必须为布尔值')
    if not isinstance(config['blockedPaths'], list) or any(not isinstance(p, str) or not p.startswith('/') or urllib.parse.urlsplit(p).path != p or p.startswith('//') for p in config['blockedPaths']):
        raise ValueError('blockedPaths 必须为原站路径列表，不含查询参数')
    limits = {'workers': (1, 8), 'schedulerSeconds': (1, 300),
              'requestTimeoutSeconds': (1, 120), 'retryBaseSeconds': (1, 3600),
              'retryMaxSeconds': (1, 86400), 'manualCooldownSeconds': (1, 3600)}
    for key, (minimum, maximum) in limits.items():
        value = config[key]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError('刷新配置超出范围：' + key)
    for value in config['intervalsSeconds'].values():
        if type(value) is not int or not 30 <= value <= 604800:
            raise ValueError('更新间隔应为 30～604800 秒的整数')
    if config['retryMaxSeconds'] < config['retryBaseSeconds']:
        raise ValueError('最大重试间隔不能小于初始重试间隔')
    return config


def fetch_origin(origin, path, body, headers, timeout):
    headers = {'User-Agent': 'Mozilla/5.0 Robotaxi-Chinese-Local-Mirror', **headers}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(origin + path, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, b'', dict(exc.headers.items())
        raise


class RefreshCache:
    def __init__(self, directory, origin, config=None, allowed_queries=(), fetcher=None, clock=time.time):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.origin = origin
        self.config = config or load_config()
        self.allowed_queries = set(allowed_queries)
        self.fetcher = fetcher or fetch_origin
        self.clock = clock
        self.lock = threading.RLock()
        self.slots = threading.BoundedSemaphore(self.config['workers'])
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.config['workers'], thread_name_prefix='data-refresh')
        self.entries, self.inflight = {}, {}
        self.stop_event = threading.Event()
        self.wakeup_event = threading.Event()
        self.scheduler = None
        self.manual_thread = None
        self.job = None
        self.last_manual = None
        self.last_sweep = None
        self.start_time = timestamp(self.clock())
        self.load()

    def load(self):
        for file in sorted(self.directory.glob('*.json')):
            try:
                meta = json.loads(file.read_text())
                body = meta.get('body')
                path, body, key = identity(meta['path'], body.encode() if body is not None else None)
                if body is not None and (path != '/v1/api/compat/query' or json.loads(body).get('name') not in self.allowed_queries):
                    continue
                payload_file = meta.get('bodyFile') or file.stem + '.body'
                if Path(payload_file).name != payload_file:
                    continue
                if not (self.directory / payload_file).is_file():
                    if not meta.get('failures'):
                        continue
                    payload_file = None
                meta.update(path=path, body=body.decode() if body is not None else None, bodyFile=payload_file, _metaFile=file.name)
                old = self.entries.get(key)
                if not old or epoch(meta.get('checkedAt', meta.get('fetchedAt'))) >= epoch(old.get('checkedAt', old.get('fetchedAt'))):
                    self.entries[key] = meta
            except (ValueError, KeyError, OSError, TypeError):
                continue

    def policy(self, meta):
        group, background = category(meta['path'], meta.get('body'), meta.get('contentType', ''))
        return group, background, self.config['intervalsSeconds'].get(group, 0)

    def due_at(self, meta):
        _, _, ttl = self.policy(meta)
        if not ttl or self.is_blocked(meta):
            return float('inf')
        if meta.get('failures') and meta.get('nextRetryAt'):
            return epoch(meta['nextRetryAt'])
        return epoch(meta.get('checkedAt', meta.get('fetchedAt'))) + ttl

    def is_stale(self, meta):
        _, _, ttl = self.policy(meta)
        return bool(ttl and self.clock() >= epoch(meta.get('checkedAt', meta.get('fetchedAt'))) + ttl)

    def is_blocked(self, meta):
        return bool(meta.get('blocked') or urllib.parse.urlsplit(meta['path']).path in self.config['blockedPaths'])

    def _atomic(self, path, data):
        handle, temporary = tempfile.mkstemp(prefix='.refresh-', dir=self.directory)
        try:
            with os.fdopen(handle, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _save(self, key, meta, data=None):
        # Called with lock held. A single atomic metadata switch commits a pair.
        old = self.entries.get(key, {})
        if data is not None:
            meta['bodyFile'] = key + '.' + hashlib.sha256(data).hexdigest() + '.body'
            target = self.directory / meta['bodyFile']
            if not target.exists():
                self._atomic(target, data)
        meta['_metaFile'] = key + '.json'
        clean = {k: v for k, v in meta.items() if not k.startswith('_')}
        self._atomic(self.directory / meta['_metaFile'], json.dumps(clean, ensure_ascii=False, indent=2).encode())
        self.entries[key] = meta
        for field in ('bodyFile', '_metaFile'):
            if old.get(field) and old[field] != meta.get(field):
                try:
                    (self.directory / old[field]).unlink()
                except OSError:
                    pass

    @staticmethod
    def validate(path, data, kind, previous=None):
        if path.startswith(('/v1/', '/data/', '/map-styles/')) and not kind.startswith('image/') and not path.startswith('/vehicles/web/'):
            if 'json' not in kind.lower():
                raise ValueError('原站未返回 JSON，已保留上次成功数据')
            value = json.loads(data)
            if not isinstance(value, (dict, list)):
                raise ValueError('原站数据结构无效')
            if isinstance(value, dict) and (value.get('error') or value.get('ok') is False or value.get('success') is False):
                raise ValueError('原站返回错误信息，已保留上次成功数据')
            if previous is not None:
                old = json.loads(previous)
                if type(value) is not type(old):
                    raise ValueError('原站数据结构已变化，需要检查前端兼容性')
                # Keep collection/object fields required by the pinned frontend.
                if isinstance(old, dict):
                    for name, item in old.items():
                        if isinstance(item, (list, dict)) and (name not in value or type(value[name]) is not type(item)):
                            raise ValueError('原站字段结构已变化：' + name)

    def _refresh(self, key, path, body):
        with self.lock:
            old = self.entries.get(key, {}).copy()
            if self.is_blocked(old or {'path': path}):
                return {'key': key, 'outcome': 'blocked'}
            if old and epoch(old.get('nextRetryAt')) > self.clock():
                return {'key': key, 'outcome': 'deferred'}
            previous = (self.directory / old['bodyFile']).read_bytes() if old.get('bodyFile') else None
        headers = {}
        # POST query caches remain distinct and never use GET validators.
        if body is None and previous is not None:
            if old.get('etag'):
                headers['If-None-Match'] = old['etag']
            if old.get('lastModified'):
                headers['If-Modified-Since'] = old['lastModified']
        attempted = timestamp(self.clock())
        try:
            with self.slots:
                status, data, response_headers = self.fetcher(self.origin, path, body, headers, self.config['requestTimeoutSeconds'])
            response_headers = {k.lower(): v for k, v in response_headers.items()}
            if status == 304:
                if previous is None:
                    raise ValueError('原站返回未修改，但本地尚无缓存')
                data, kind = previous, old['contentType']
            elif status == 200:
                kind = response_headers.get('content-type', 'application/octet-stream')
                self.validate(path, data, kind, previous)
            else:
                raise ValueError('原站响应状态异常：' + str(status))
            now = timestamp(self.clock())
            changed = previous != data
            meta = {**old, 'path': path, 'body': body.decode() if body is not None else None,
                    'contentType': kind, 'fetchedAt': now if status == 200 else old.get('fetchedAt'),
                    'checkedAt': now, 'changedAt': now if changed else old.get('changedAt'),
                    'attemptedAt': attempted, 'failures': 0, 'lastError': None, 'nextRetryAt': None, 'blocked': False,
                    'etag': response_headers.get('etag', old.get('etag') if status == 304 else None),
                    'lastModified': response_headers.get('last-modified', old.get('lastModified') if status == 304 else None)}
            with self.lock:
                self._save(key, meta, data if changed or not old.get('bodyFile') else None)
            return {'key': key, 'outcome': 'changed' if changed else 'unchanged'}
        except Exception as exc:
            count = old.get('failures', 0) + 1
            blocked = isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403)
            delay = min(self.config['retryMaxSeconds'], self.config['retryBaseSeconds'] * 2 ** min(count - 1, 16))
            if isinstance(exc, urllib.error.HTTPError):
                message = '原站 HTTP ' + str(exc.code)
                retry = exc.headers.get('Retry-After') if exc.headers else None
                if retry:
                    try:
                        delay = max(delay, int(retry))
                    except ValueError:
                        try:
                            delay = max(delay, parsedate_to_datetime(retry).timestamp() - self.clock())
                        except (ValueError, TypeError):
                            pass
            else:
                message = str(exc)[:180]
            # Persist failure state even on a cold miss, to prevent request storms.
            meta = {**old, 'path': path, 'body': body.decode() if body is not None else None,
                    'attemptedAt': attempted, 'failures': count, 'lastError': message,
                    'nextRetryAt': None if blocked else timestamp(self.clock() + delay), 'blocked': blocked}
            with self.lock:
                self._save(key, meta)
            return {'key': key, 'outcome': 'blocked' if blocked else 'failed', 'error': message}

    def _submit(self, key, path, body):
        with self.lock:
            if key in self.inflight:
                return self.inflight[key]
            future = self.pool.submit(self._refresh, key, path, body)
            self.inflight[key] = future
            def complete(done):
                with self.lock:
                    self.inflight.pop(key, None)
                self.wakeup_event.set()
            future.add_done_callback(complete)
            return future

    def get(self, path, body=None):
        path, body, key = identity(path, body)
        with self.lock:
            meta = self.entries.get(key)
            if meta and meta.get('bodyFile'):
                data = (self.directory / meta['bodyFile']).read_bytes()
                if self.config['enabled'] and self.due_at(meta) <= self.clock():
                    self._submit(key, path, body)
                return data, meta['contentType'], self.headers(key, meta)
            if self.is_blocked(meta or {'path': path}):
                raise ValueError('原站限制自动访问，此数据尚无可用缓存')
            if meta and epoch(meta.get('nextRetryAt')) > self.clock():
                raise ValueError('原站暂不可用，已安排重试；此数据尚无可用缓存')
            future = self._submit(key, path, body)
        result = future.result()
        with self.lock:
            meta = self.entries.get(key, {})
            if not meta.get('bodyFile'):
                raise ValueError(result.get('error', '公开数据尚不可用'))
            return (self.directory / meta['bodyFile']).read_bytes(), meta['contentType'], self.headers(key, meta)

    def headers(self, key, meta):
        group, _, _ = self.policy(meta)
        return {'X-Mirror-Key': key,
                'X-Mirror-Cache': 'blocked' if self.is_blocked(meta) else ('stale' if self.is_stale(meta) else ('fresh' if group else 'immutable')),
                'X-Mirror-Checked-At': meta.get('checkedAt', meta.get('fetchedAt', '')) or '',
                'X-Mirror-Changed-At': meta.get('changedAt') or ''}

    def sweep(self):
        with self.lock:
            self.last_sweep = timestamp(self.clock())
            free = max(0, self.config['workers'] - len(self.inflight))
            candidates = sorted(((self.due_at(m), k, m) for k, m in self.entries.items()
                                 if self.policy(m)[1] and k not in self.inflight), key=lambda item: item[0])
            for due, key, meta in candidates[:free]:
                if due <= self.clock():
                    self._submit(key, meta['path'], meta.get('body').encode() if meta.get('body') is not None else None)

    def start(self):
        if not self.config['enabled'] or self.scheduler:
            return
        def run():
            while not self.stop_event.is_set():
                self.sweep()
                self.wakeup_event.wait(self.config['schedulerSeconds'])
                self.wakeup_event.clear()
        self.scheduler = threading.Thread(target=run, name='refresh-scheduler', daemon=True)
        self.scheduler.start()

    def manual(self):
        with self.lock:
            if self.job and self.job['running']:
                return self.job.copy(), False
            if self.last_manual is not None and self.clock() - self.last_manual < self.config['manualCooldownSeconds']:
                return self.job.copy(), False
            # Includes previously visited details/pages once; excludes immutable images.
            entries = [(k, m.copy()) for k, m in self.entries.items() if self.policy(m)[0]]
            entries.sort(key=lambda item: self.due_at(item[1]))
            self.last_manual = self.clock()
            self.job = {'startedAt': timestamp(self.clock()), 'finishedAt': None, 'running': True,
                        'total': len(entries), 'done': 0, 'changed': 0, 'unchanged': 0, 'failed': 0, 'deferred': 0, 'blocked': 0}
        def run():
            # Feed only a small window into the shared pool; automatic reads join it.
            pending = set()
            iterator = iter(entries)
            while not self.stop_event.is_set():
                while len(pending) < self.config['workers']:
                    try:
                        key, meta = next(iterator)
                    except StopIteration:
                        break
                    pending.add(self._submit(key, meta['path'], meta.get('body').encode() if meta.get('body') is not None else None))
                if not pending:
                    break
                done, pending = concurrent.futures.wait(pending, timeout=1, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    try:
                        outcome = future.result()['outcome']
                    except Exception:
                        outcome = 'failed'
                    with self.lock:
                        self.job['done'] += 1
                        self.job[outcome] += 1
            with self.lock:
                self.job['running'] = False
                self.job['finishedAt'] = timestamp(self.clock())
                self.job['cancelled'] = self.job['done'] < self.job['total']
        self.manual_thread = threading.Thread(target=run, name='manual-refresh', daemon=True)
        self.manual_thread.start()
        return self.job.copy(), True

    def status(self):
        with self.lock:
            groups = {k: {'id': k, 'label': name, 'intervalSeconds': self.config['intervalsSeconds'][k],
                          'total': 0, 'stale': 0, 'failed': 0, 'blocked': 0, 'refreshing': 0,
                          'oldestCheckedAt': None, 'latestCheckedAt': None, 'nextCheckAt': None,
                          'nextRetryAt': None, 'failureReasons': []}
                      for k, name in LABELS.items()}
            records = []
            for key, meta in self.entries.items():
                group, background, ttl = self.policy(meta)
                if not group:
                    continue
                checked = meta.get('checkedAt', meta.get('fetchedAt'))
                stale = self.is_stale(meta)
                blocked = self.is_blocked(meta)
                failed = bool(meta.get('failures')) and not blocked
                refreshing = key in self.inflight
                next_at = max(self.clock(), self.due_at(meta)) if not blocked else None
                record = {'key': key, 'category': group, 'checkedAt': checked,
                          'changedAt': meta.get('changedAt'), 'stale': stale,
                          'hasCache': bool(meta.get('bodyFile')), 'refreshing': refreshing, 'blocked': blocked,
                          'background': background, 'failures': meta.get('failures', 0),
                          'nextRetryAt': meta.get('nextRetryAt')}
                records.append(record)
                row = groups[group]
                row['total'] += 1
                row['stale'] += int(stale)
                row['failed'] += int(failed)
                row['blocked'] += int(blocked)
                row['refreshing'] += int(refreshing)
                if failed:
                    if meta.get('nextRetryAt'):
                        row['nextRetryAt'] = min(row['nextRetryAt'] or meta['nextRetryAt'], meta['nextRetryAt'])
                    error = meta.get('lastError', '')
                    reason = error if error.startswith('原站') else '网络连接或本地存储暂不可用'
                    if reason not in row['failureReasons']:
                        row['failureReasons'].append(reason)
                if checked:
                    row['oldestCheckedAt'] = min(row['oldestCheckedAt'] or checked, checked)
                    row['latestCheckedAt'] = max(row['latestCheckedAt'] or checked, checked)
                if background and self.config['enabled'] and not blocked:
                    row['nextCheckAt'] = min(row['nextCheckAt'] or timestamp(next_at), timestamp(next_at))
            rows = list(groups.values())
            return {'enabled': self.config['enabled'], 'schedulerRunning': bool(self.scheduler and self.scheduler.is_alive()),
                    'startedAt': self.start_time, 'serverTime': timestamp(self.clock()), 'lastSweepAt': self.last_sweep,
                    'workers': self.config['workers'], 'schedulerSeconds': self.config['schedulerSeconds'],
                    'total': len(records), 'stale': sum(r['stale'] for r in rows),
                    'failed': sum(r['failed'] for r in rows), 'refreshing': len(self.inflight),
                    'blocked': sum(r['blocked'] for r in rows),
                    'manualAvailableAt': timestamp((self.last_manual or 0) + self.config['manualCooldownSeconds']),
                    'job': self.job.copy() if self.job else None, 'groups': rows, 'records': records}

    def close(self):
        self.stop_event.set()
        self.wakeup_event.set()
        if self.scheduler:
            self.scheduler.join(timeout=2)
        if self.manual_thread:
            self.manual_thread.join(timeout=2)
        self.pool.shutdown(wait=True)
