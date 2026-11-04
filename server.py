#!/usr/bin/env python3
"""Robotaxi Tracker Chinese mirror. Python standard library; no install required."""
import argparse
import concurrent.futures
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from refresh import RefreshCache, load_config

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
CACHE = ROOT / 'cache'
ORIGIN = 'https://robotaxitracker.com'
LOCK = threading.RLock()
TRANSLATION_LOCK = threading.Lock()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=8)
PUBLIC.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
DICTIONARY_FILE = ROOT / 'translations.json'
DICTIONARY = json.loads(DICTIONARY_FILE.read_text()) if DICTIONARY_FILE.exists() else {}
REFRESH = RefreshCache(CACHE, ORIGIN,
                       load_config(os.environ.get('REFRESH_CONFIG', str(ROOT / 'refresh-config.json'))),
                       json.loads((ROOT / 'read-queries.json').read_text()))

def request(url, body=None, headers=None, timeout=28):
    req = urllib.request.Request(url, data=body, headers={'User-Agent': 'Mozilla/5.0 Robotaxi-Chinese-Local-Mirror', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.headers.get('Content-Type', 'application/octet-stream')

def cache_key(path, body=None):
    return hashlib.sha256(path.encode() + (body or b'')).hexdigest()

def upstream(path, body=None, details=False):
    """Only called for public reads. Never forwards cookies or authorization."""
    result = REFRESH.get(path, body)
    return result if details else result[:2]

def translate_batch(texts):
    """Translate only public UI text; results are persisted for offline reuse."""
    result = {s: DICTIONARY[s] for s in texts if s in DICTIONARY}
    missing = list(dict.fromkeys(s for s in texts if s not in DICTIONARY and s.strip()))
    if not missing:
        return result
    # Delimiters keep React text node boundaries stable across a batched request.
    groups, current, size = [], [], 0
    for text in missing:
        if size + len(text) > 2300 and current:
            groups.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text) + 12
    if current:
        groups.append(current)
    def convert(group):
        source = '\n'.join(f'[{i}] {text}' for i, text in enumerate(group))
        query = urllib.parse.urlencode({'client': 'gtx', 'sl': 'en', 'tl': 'zh-CN', 'dt': 't', 'q': source})
        data, _ = request('https://translate.googleapis.com/translate_a/single?' + query, timeout=25)
        payload = json.loads(data)
        translated = ''.join(row[0] or '' for row in payload[0])
        parts = re.split(r'\[\s*(\d+)\s*\]\s*', translated)
        values = {}
        for i in range(1, len(parts) - 1, 2):
            index = int(parts[i])
            if index < len(group):
                values[group[index]] = parts[i+1].strip()
        if len(values) != len(group):
            # A separator can be dropped for single short strings.
            if len(group) == 1:
                values[group[0]] = re.sub(r'^\[0\]\s*', '', translated).strip()
        return values
    futures = [POOL.submit(convert, group) for group in groups]
    for f in futures:
        try:
            result.update(f.result())
        except Exception as exc:
            print('Translation retry needed:', str(exc)[:100], flush=True)
    with TRANSLATION_LOCK:
        DICTIONARY.update(result)
        temporary = DICTIONARY_FILE.with_suffix('.tmp')
        temporary.write_text(json.dumps(DICTIONARY, ensure_ascii=False, indent=2))
        temporary.replace(DICTIONARY_FILE)
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if len(args) > 1 and str(args[1]) not in ('200', '204', '304'):
            print(fmt % args, flush=True)

    def respond(self, data, kind='application/json; charset=utf-8', status=200, headers=None):
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False).encode()
        elif isinstance(data, str):
            data = data.encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-cache' if 'html' in kind or 'json' in kind or self.path.startswith(('/zh-cn.', '/refresh-ui.')) else 'public, max-age=3600')
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == '/__local/health':
            return self.respond({'ok': True, 'locale': 'zh-CN', 'translations': len(DICTIONARY), 'source': ORIGIN})
        if path == '/__local/refresh-status':
            return self.respond(REFRESH.status())
        if path == '/__local/translations':
            return self.respond(DICTIONARY)
        if path == '/__local/ui-strings':
            return self.respond((ROOT / 'ui-strings.json').read_bytes())
        if path.startswith('/__rt/') or path.startswith('/cdn-cgi/'):
            return self.respond({'ok': True})
        if path.startswith('/v1/api/auth/') or path.startswith('/v1/api/account'):
            return self.respond({'user': None, 'session': None, 'error': '中文镜像不连接原站账户。请前往原站登录。'}, status=401)
        if path.startswith(('/v1/', '/data/', '/map-styles/', '/vehicles/web/')):
            try:
                data, kind, headers = upstream(self.path, details=True)
                if path.startswith('/map-styles/'):
                    style = json.loads(data)
                    def chinese_label(value):
                        if isinstance(value, list):
                            if value == ['coalesce', ['get', 'name:en'], ['get', 'name']]:
                                return ['coalesce', ['get', 'name:zh'], ['get', 'name:zh-Hans'], ['get', 'name:en'], ['get', 'name']]
                            return [chinese_label(v) for v in value]
                        return value
                    for layer in style.get('layers', []):
                        layout = layer.get('layout', {})
                        if 'text-field' in layout:
                            layout['text-field'] = chinese_label(layout['text-field'])
                    data = json.dumps(style, ensure_ascii=False).encode()
                return self.respond(data, kind, headers=headers)
            except Exception as exc:
                return self.respond({'error': '暂时无法读取原站公开数据，请稍后重试。', 'detail': str(exc)[:100]}, status=502)
        target = (PUBLIC / urllib.parse.unquote(path).lstrip('/')).resolve()
        if not target.is_relative_to(PUBLIC.resolve()):
            return self.respond({'error': '无效路径'}, status=400)
        if path == '/zh-cn.js':
            target = ROOT / 'zh-cn.js'
        elif path == '/zh-cn.css':
            target = ROOT / 'zh-cn.css'
        elif path in ('/refresh-ui.js', '/refresh-ui.css'):
            target = ROOT / path.lstrip('/')
        elif path == '/translations.json':
            return self.respond(DICTIONARY)
        if target.is_file():
            kind = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            if target.suffix in ('.js', '.mjs'):
                kind = 'text/javascript; charset=utf-8'
            return self.respond(target.read_bytes(), kind)
        if path.startswith('/assets/') or path.endswith(('.png', '.svg', '.webp', '.jpg', '.jpeg', '.avif', '.gif', '.woff2', '.ico')):
            try:
                data, kind = request(ORIGIN + self.path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                return self.respond(data, kind)
            except Exception:
                return self.respond({'error': '资源暂时无法加载'}, status=404)
        return self.respond((ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        size = int(self.headers.get('Content-Length', 0))
        if size > 200000:
            return self.respond({'error': '请求过大'}, status=413)
        raw = self.rfile.read(size)
        # Origin check prevents arbitrary websites invoking the local bridge.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.respond({'error': '不支持跨站请求'}, status=403)
        if self.path == '/__local/refresh':
            # JSON + a same-origin custom header keep this action out of forms.
            if self.headers.get('X-Mirror-Action') != 'refresh':
                return self.respond({'error': '请从数据更新面板发起请求'}, status=403)
            job, started = REFRESH.manual()
            return self.respond({'started': started, 'job': job}, status=202 if started else 200)
        if self.path == '/__local/translate':
            try:
                texts = json.loads(raw).get('texts', [])
                texts = [s for s in texts if isinstance(s, str) and len(s) < 15000][:160]
                return self.respond(translate_batch(texts))
            except Exception as exc:
                return self.respond({'error': str(exc)[:100]}, status=502)
        if self.path == '/__local/translation-cache':
            try:
                data = json.loads(raw)
                valid = {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str) and len(k) < 15000 and len(v) < 20000}
                with TRANSLATION_LOCK:
                    DICTIONARY.update(valid)
                    temporary = DICTIONARY_FILE.with_suffix('.tmp')
                    temporary.write_text(json.dumps(DICTIONARY, ensure_ascii=False, indent=2))
                    temporary.replace(DICTIONARY_FILE)
                return self.respond({'saved': len(valid), 'total': len(DICTIONARY)})
            except Exception:
                return self.respond({'error': '翻译数据格式错误'}, status=400)
        if self.path == '/v1/api/compat/query':
            try:
                payload = json.loads(raw)
                # These are the site's public read queries, not arbitrary RPC.
                name = payload.get('name', '')
                allowed = json.loads((ROOT / 'read-queries.json').read_text())
                if name not in allowed:
                    return self.respond({'error': '中文镜像仅提供公开数据查询'}, status=403)
                canonical = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode()
                data, kind, headers = upstream(self.path, canonical, details=True)
                return self.respond(data, kind, headers=headers)
            except Exception as exc:
                return self.respond({'error': str(exc)[:120]}, status=502)
        return self.respond({'error': '此为简体中文镜像。账户登录、投稿和个人数据操作请前往原站。'}, status=403)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8080)))
    parser.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0' if os.environ.get('PORT') else '127.0.0.1'))
    args = parser.parse_args()
    print(f'Robotaxi Tracker 简体中文版：http://{args.host}:{args.port}', flush=True)
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    REFRESH.start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        REFRESH.close()
