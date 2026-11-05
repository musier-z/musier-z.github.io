import concurrent.futures
import copy
import hashlib
import json
import tempfile
import threading
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from refresh import RefreshCache, category, epoch, identity, load_config, timestamp


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1800000000
        self.calls = []
        self.response = (200, b'{"items":[1]}', {'Content-Type': 'application/json', 'ETag': 'v1'})
        self.cache = RefreshCache(self.temp.name, 'https://example.test',
                                  allowed_queries=['queries/trips:getPricingAnalytics'],
                                  fetcher=self.fetch, clock=lambda: self.now)
        self.addCleanup(self.cache.close)

    def fetch(self, origin, path, body, headers, timeout):
        self.calls.append((path, body, headers.copy()))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def wait_pending(self):
        with self.cache.lock:
            futures = list(self.cache.inflight.values())
        for future in futures:
            future.result(timeout=3)

    def wait_job(self):
        deadline = time.monotonic() + 3
        while self.cache.status()['job']['running'] and time.monotonic() < deadline:
            threading.Event().wait(.005)
        self.assertFalse(self.cache.status()['job']['running'])
        return self.cache.status()['job']

    def test_fresh_cache_avoids_network(self):
        first = self.cache.get('/v1/camera-sightings')
        self.now += 59
        self.assertEqual(first[0], self.cache.get('/v1/camera-sightings')[0])
        self.assertEqual(1, len(self.calls))

    def test_expired_serves_old_without_waiting_and_refreshes(self):
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        entered, release = threading.Event(), threading.Event()
        def blocked(*args):
            entered.set()
            self.assertTrue(release.wait(3))
            return 200, b'{"items":[2]}', {'Content-Type': 'application/json'}
        self.cache.fetcher = blocked
        old = self.cache.get('/v1/camera-sightings')
        self.assertEqual('stale', old[2]['X-Mirror-Cache'])
        self.assertEqual(b'{"items":[1]}', old[0])
        self.assertTrue(entered.wait(1))
        release.set()
        self.wait_pending()
        self.assertEqual(b'{"items":[2]}', self.cache.get('/v1/camera-sightings')[0])

    def test_concurrent_cold_requests_coalesce(self):
        entered, release = threading.Event(), threading.Event()
        def blocked(*args):
            self.calls.append(args)
            entered.set()
            release.wait(3)
            return self.response
        self.cache.fetcher = blocked
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as callers:
            futures = [callers.submit(self.cache.get, '/v1/camera-sightings') for _ in range(10)]
            self.assertTrue(entered.wait(1))
            release.set()
            results = [f.result(timeout=3) for f in futures]
        self.assertEqual(1, len(self.calls))
        self.assertTrue(all(r[0] == results[0][0] for r in results))

    def test_conditional_304_preserves_payload_and_changed_time(self):
        first = self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.response = (304, b'', {'ETag': 'v1'})
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        result = self.cache.get('/v1/camera-sightings')
        self.assertEqual({'If-None-Match': 'v1'}, self.calls[-1][2])
        self.assertEqual(first[0], result[0])
        self.assertEqual(first[2]['X-Mirror-Changed-At'], result[2]['X-Mirror-Changed-At'])
        self.assertNotEqual(first[2]['X-Mirror-Checked-At'], result[2]['X-Mirror-Checked-At'])

    def test_unchanged_200_does_not_report_content_change(self):
        first = self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        self.assertEqual(first[2]['X-Mirror-Changed-At'], self.cache.get('/v1/camera-sightings')[2]['X-Mirror-Changed-At'])

    def test_invalid_responses_keep_old_data(self):
        self.cache.get('/v1/camera-sightings')
        cases = [
            (200, b'<html>failed</html>', {'Content-Type': 'text/html'}),
            (200, b'broken', {'Content-Type': 'application/json'}),
            (200, b'{"error":"offline"}', {'Content-Type': 'application/json'}),
            (200, b'{"different":[]}', {'Content-Type': 'application/json'}),
            (200, b'null', {'Content-Type': 'application/json'}),
            (503, b'{}', {'Content-Type': 'application/json'}),
        ]
        for response in cases:
            self.now += 4000
            self.response = response
            self.cache.get('/v1/camera-sightings')
            self.wait_pending()
            self.assertEqual(b'{"items":[1]}', self.cache.get('/v1/camera-sightings')[0])
        self.assertEqual(6, next(iter(self.cache.entries.values()))['failures'])

    def test_retry_backoff_and_recovery(self):
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.response = TimeoutError('timeout')
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        meta = next(iter(self.cache.entries.values()))
        self.assertEqual(self.now + 60, epoch(meta['nextRetryAt']))
        self.now += 59
        self.cache.get('/v1/camera-sightings')
        self.assertEqual(2, len(self.calls))
        self.now += 2
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        self.assertEqual(self.now + 120, epoch(next(iter(self.cache.entries.values()))['nextRetryAt']))
        self.now += 121
        self.response = (200, b'{"items":[]}', {'Content-Type': 'application/json'})
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        self.assertEqual(0, self.cache.status()['failed'])
        self.assertEqual(b'{"items":[]}', self.cache.get('/v1/camera-sightings')[0])

    def test_retry_after_is_respected(self):
        self.response = urllib.error.HTTPError('https://example.test', 429, 'rate limited', {'Retry-After': '7200'}, None)
        with self.assertRaises(ValueError):
            self.cache.get('/v1/camera-sightings')
        self.assertEqual(self.now + 7200, epoch(next(iter(self.cache.entries.values()))['nextRetryAt']))
        with self.assertRaises(ValueError):
            self.cache.get('/v1/camera-sightings')
        self.assertEqual(1, len(self.calls))

    def test_access_denied_stops_automatic_and_manual_retry(self):
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.response = urllib.error.HTTPError('https://example.test', 403, 'automated_client', {}, None)
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        self.now += 90000
        self.cache.sweep()
        self.assertEqual('blocked', self.cache.get('/v1/camera-sightings')[2]['X-Mirror-Cache'])
        self.cache.manual()
        self.assertEqual(1, self.wait_job()['blocked'])
        self.assertEqual(2, len(self.calls))
        self.assertEqual(1, self.cache.status()['blocked'])
        self.assertEqual(0, self.cache.status()['failed'])
        self.cache.entries.clear()
        self.cache.load()
        self.assertEqual(1, self.cache.status()['blocked'])

    def test_configured_denied_path_never_requests_origin(self):
        self.cache.config = copy.deepcopy(self.cache.config)
        self.cache.config['blockedPaths'] = ['/v1/waymo-cameras']
        with self.assertRaises(ValueError):
            self.cache.get('/v1/waymo-cameras?cameras=tally')
        self.assertEqual(0, len(self.calls))

    def test_post_args_remain_isolated_and_never_get_validators(self):
        one = b'{"name":"queries/trips:getPricingAnalytics","args":{"provider":"tesla"}}'
        two = b'{"args":{"provider":"waymo"},"name":"queries/trips:getPricingAnalytics"}'
        self.cache.get('/v1/api/compat/query', one)
        self.cache.get('/v1/api/compat/query', two)
        self.assertEqual(2, len(self.cache.entries))
        self.now += 3601
        self.cache.get('/v1/api/compat/query', one)
        self.wait_pending()
        self.assertEqual({}, self.calls[-1][2])

    def test_camera_image_hash_paths_are_not_camera_category(self):
        cases = [
            '/v1/cybercab-cameras/images/' + 'a' * 64,
            '/v1/waymo-cameras/images/' + 'b' * 64,
            '/v1/avride-cameras/images/' + 'c' * 64,
            '/v1/api/news-feed/images/' + 'd' * 64,
        ]
        for path in cases:
            self.assertEqual((None, False), category(path))
            self.assertEqual((None, False), category(path, kind='image/webp'))
        self.assertEqual(('camera', True), category('/v1/camera-sightings'))
        self.assertEqual(('camera', True), category('/v1/waymo-cameras?cameras=tally'))
        self.assertEqual(('fleet', True), category('/v1/camera-sightings/timeline'))

    def test_prune_failed_misses_keeps_bodied_failures(self):
        self.response = TimeoutError('offline')
        with self.assertRaises(ValueError):
            self.cache.get('/v1/camera-sightings')
        self.assertEqual(1, self.cache.status()['failed'])
        # Cold miss: no body — pruned.
        self.assertEqual(1, self.cache.prune_failed_misses())
        self.assertEqual(0, self.cache.status()['failed'])
        self.assertEqual(0, len(self.cache.entries))
        # Seed a success, then fail while keeping body — not pruned.
        self.response = (200, b'{"items":[1]}', {'Content-Type': 'application/json'})
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.response = TimeoutError('offline')
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        self.assertEqual(1, self.cache.status()['failed'])
        self.assertTrue(self.cache.status()['records'][0]['hasCache'])
        self.assertEqual(0, self.cache.prune_failed_misses())
        self.assertEqual(1, self.cache.status()['failed'])

    def test_status_can_filter_to_snapshot_keys(self):
        self.cache.get('/v1/camera-sightings')
        other = '/v1/camera-sightings?kind=waymo'
        self.cache.get(other)
        all_keys = list(self.cache.entries)
        self.assertEqual(2, self.cache.status()['total'])
        keep = {all_keys[0]}
        filtered = self.cache.status(keys=keep)
        self.assertEqual(1, filtered['total'])
        self.assertEqual([all_keys[0]], [r['key'] for r in filtered['records']])

    def test_known_cache_busters_only_are_ignored(self):

        self.assertEqual(identity('/v1/api/service-areas?v=old')[2], identity('/v1/api/service-areas?v=new')[2])
        self.assertEqual(identity('/v1/api/texas-dmv/vins?version=a')[2], identity('/v1/api/texas-dmv/vins?version=b')[2])
        self.assertNotEqual(identity('/v1/camera-sightings?kind=waymo')[2], identity('/v1/camera-sightings?kind=zoox')[2])
        self.assertNotEqual(identity('/data/x.json?v=1')[2], identity('/data/x.json?v=2')[2])
        self.assertNotEqual(identity('/v1/camera-sightings?cursor=1')[2], identity('/v1/camera-sightings?cursor=2')[2])
        self.assertEqual(identity('/v1/camera-sightings?kind=x&market=y')[2], identity('/v1/camera-sightings?market=y&kind=x')[2])

    def test_legacy_metadata_migrates_without_redownload_when_fresh(self):
        path = '/v1/api/service-areas?v=old'
        key = hashlib.sha256(path.encode()).hexdigest()
        directory = Path(self.temp.name)
        (directory / (key + '.body')).write_bytes(b'{"items":[1]}')
        (directory / (key + '.json')).write_text(json.dumps({'path': path, 'body': None, 'contentType': 'application/json', 'fetchedAt': timestamp(self.now)}))
        self.cache.load()
        self.assertEqual(b'{"items":[1]}', self.cache.get('/v1/api/service-areas?v=new')[0])
        self.assertEqual(0, len(self.calls))
        self.now += 3601
        self.cache.get('/v1/api/service-areas?v=new')
        self.wait_pending()
        self.assertFalse((directory / (key + '.json')).exists())
        self.assertIsNone(next(iter(self.cache.entries.values()))['changedAt'])

    def test_atomic_metadata_failure_preserves_last_good_payload(self):
        first = self.cache.get('/v1/camera-sightings')[0]
        self.now += 61
        self.response = (200, b'{"items":[99]}', {'Content-Type': 'application/json'})
        atomic = self.cache._atomic
        failed = []
        def fail_once(path, data):
            if str(path).endswith('.json') and not failed:
                failed.append(True)
                raise OSError('interrupted commit')
            return atomic(path, data)
        with patch.object(self.cache, '_atomic', side_effect=fail_once):
            self.cache.get('/v1/camera-sightings')
            self.wait_pending()
        self.assertEqual(first, self.cache.get('/v1/camera-sightings')[0])
        self.cache.entries.clear()
        self.cache.load()
        self.assertEqual(first, self.cache.get('/v1/camera-sightings')[0])

    def test_cold_failure_backoff_survives_restart(self):
        self.response = TimeoutError('offline')
        with self.assertRaises(ValueError):
            self.cache.get('/v1/camera-sightings')
        self.cache.entries.clear()
        self.cache.load()
        self.assertEqual(1, self.cache.status()['failed'])
        with self.assertRaises(ValueError):
            self.cache.get('/v1/camera-sightings')
        self.assertEqual(1, len(self.calls))
        self.now += 61
        with self.assertRaises(ValueError):
            self.cache.get('/v1/camera-sightings')
        self.cache.entries.clear()
        self.cache.load()
        self.assertEqual(1, self.cache.status()['failed'])
        self.assertFalse(self.cache.status()['records'][0]['hasCache'])

    def test_scheduler_skips_images_and_old_pages(self):
        self.cache.get('/v1/camera-sightings')
        self.cache.get('/v1/camera-sightings?cursor=old')
        self.response = (200, b'image', {'Content-Type': 'image/webp'})
        self.cache.get('/vehicles/web/hash.webp')
        self.response = (200, b'{"items":[1]}', {'Content-Type': 'application/json'})
        self.calls.clear()
        self.now += 90000
        self.cache.sweep()
        self.wait_pending()
        self.assertEqual(['/v1/camera-sightings'], [c[0] for c in self.calls])

    def test_manual_updates_cached_data_excludes_images_and_coalesces_job(self):
        self.cache.get('/v1/camera-sightings')
        self.cache.get('/v1/camera-sightings?cursor=old')
        self.response = (200, b'image', {'Content-Type': 'image/webp'})
        self.cache.get('/vehicles/web/hash.webp')
        self.response = (200, b'{"items":[2]}', {'Content-Type': 'application/json'})
        job, started = self.cache.manual()
        self.assertTrue(started)
        self.assertEqual(2, job['total'])
        self.assertFalse(self.cache.manual()[1])
        done = self.wait_job()
        self.assertEqual(2, done['changed'])
        self.assertFalse(self.cache.manual()[1])

    def test_manual_does_not_bypass_retry_after(self):
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.response = TimeoutError('offline')
        self.cache.get('/v1/camera-sightings')
        self.wait_pending()
        self.cache.manual()
        self.assertEqual(1, self.wait_job()['deferred'])
        self.assertEqual(2, len(self.calls))

    def test_disabled_auto_refresh_still_allows_manual(self):
        self.cache.config = copy.deepcopy(self.cache.config)
        self.cache.config['enabled'] = False
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        self.cache.start()
        self.cache.get('/v1/camera-sightings')
        self.assertEqual(1, len(self.calls))
        self.assertFalse(self.cache.status()['schedulerRunning'])
        self.cache.manual()
        self.wait_job()
        self.assertEqual(2, len(self.calls))

    def test_category_intervals_follow_data_purpose(self):
        cases = {'/v1/waymo-cameras?cameras=tally': 'camera',
                 '/v1/waymo-cameras/hourly': 'fleet',
                 '/v1/api/wait-time/unified?provider=tesla': 'wait',
                 '/v1/api/news-feed': 'news', '/v1/api/texas-dmv': 'hourly',
                 '/v1/api/nhtsa/summary': 'history', '/data/ca-dmv-summary.json': 'history',
                 '/data/population-grid.json': 'geography'}
        for path, group in cases.items():
            self.assertEqual(group, category(path)[0])
        self.assertEqual(('fleet', False), category('/v1/api/compat/query', '{"name":"queries/vehicles:getVehicleTimeline"}'))

    def test_config_rejects_unsafe_values(self):
        file = Path(self.temp.name) / 'config-test.json'
        for value in [{'workers': 100}, {'intervalsSeconds': {'camera': 0}}, {'enabled': 'true'}, {'intervalsSeconds': {'typo': 60}}]:
            file.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                load_config(file)

    def test_distinct_requests_respect_concurrency_limit(self):
        gate, entered = threading.Event(), threading.Event()
        guard = threading.Lock()
        counts = {'active': 0, 'maximum': 0, 'total': 0}
        def blocked(*args):
            with guard:
                counts['active'] += 1
                counts['total'] += 1
                counts['maximum'] = max(counts['maximum'], counts['active'])
                if counts['active'] == 3:
                    entered.set()
            gate.wait(3)
            with guard:
                counts['active'] -= 1
            return self.response
        self.cache.fetcher = blocked
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as callers:
            futures = [callers.submit(self.cache.get, '/v1/camera-sightings?market=' + str(i)) for i in range(10)]
            self.assertTrue(entered.wait(1))
            gate.set()
            for future in futures:
                future.result(timeout=3)
        self.assertEqual(3, counts['maximum'])
        self.assertEqual(10, counts['total'])

    def test_scheduler_refreshes_without_browser_requests(self):
        self.cache.get('/v1/camera-sightings')
        self.now += 61
        completed = threading.Event()
        def updated(*args):
            completed.set()
            return 200, b'{"items":[2]}', {'Content-Type': 'application/json'}
        self.cache.fetcher = updated
        self.cache.start()
        self.assertTrue(completed.wait(1))
        self.wait_pending()
        self.assertTrue(self.cache.status()['schedulerRunning'])
        self.assertEqual(0, self.cache.status()['stale'])


if __name__ == '__main__':
    unittest.main()
