/* GitHub Pages (static) adapter. Loaded before every other script.
 * Maps the pinned frontend's public data requests to the snapshot written by
 * build_static.py, prefixes root-relative URLs with the Pages base path, and
 * answers the local-server endpoints (/__local/*) that a static host lacks. */
(() => {
  'use strict';
  const S = window.__MIRROR_STATIC__ || {base: '/', entries: {}, blocked: [], status: null};
  const BASE = S.base.endsWith('/') ? S.base : S.base + '/';
  const ORIGIN = 'https://robotaxitracker.com';
  const DATA = /^\/(v1|data|map-styles|vehicles\/web)\//;
  const SNAPSHOT = BASE + 'data-snapshot/';
  const nativeFetch = window.fetch.bind(window);
  const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {status, headers: {'Content-Type': 'application/json; charset=utf-8', ...headers}});

  function strip(path) {
    if (BASE === '/' || typeof path !== 'string') return path;
    const root = BASE.slice(0, -1);
    if (path === root) return '/';
    return path.startsWith(BASE) ? path.slice(root.length) : path;
  }
  window.__mirrorStrip = strip;
  window.__mirrorPath = () => strip(location.pathname);

  const enc = value => encodeURIComponent(value);
  const stable = value => Array.isArray(value) ? '[' + value.map(stable).join(',') + ']'
    : value && typeof value === 'object' ? '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stable(value[k])).join(',') + '}'
    : JSON.stringify(value);
  function ignored(path) {
    if (path === '/v1/api/service-areas') return ['v'];
    if (path === '/v1/api/texas-dmv' || path.startsWith('/v1/api/texas-dmv/')) return ['version'];
    return [];
  }
  // Must match canonical_key() in build_static.py.
  function canonical(url, body) {
    const path = strip(url.pathname);
    const skip = ignored(path);
    const pairs = [...url.searchParams].filter(([k]) => !skip.includes(k))
      .sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0);
    let key = path + (pairs.length ? '?' + pairs.map(([k, v]) => enc(k) + '=' + enc(v)).join('&') : '');
    if (body != null && body !== '') {
      try { key += '\n' + stable(JSON.parse(body)); } catch (_) { key += '\n' + body; }
    }
    return key;
  }
  function sameOrigin(raw) {
    try {
      const url = new URL(raw, location.href);
      return url.origin === location.origin ? url : null;
    } catch (_) { return null; }
  }
  // Root-relative URL for page assets → under the Pages base path.
  function rewrite(raw) {
    if (typeof raw !== 'string' || !raw.startsWith('/') || raw.startsWith('//')) return raw;
    const url = new URL(raw, location.origin);
    const path = strip(url.pathname);
    if (DATA.test(path)) {
      const entry = S.entries[canonical(url)];
      if (entry) return SNAPSHOT + entry.f;
      // Images not in this snapshot load from the original site, unchanged.
      if (/\/images\/|^\/vehicles\/web\/|^\/v1\/media\//.test(path)) return ORIGIN + path + url.search;
      return raw;
    }
    if (BASE === '/' || raw.startsWith(BASE)) return raw;
    return BASE + raw.slice(1);
  }
  window.__mirrorRewrite = rewrite;

  async function local(path, method) {
    if (path === '/__local/health') return json({ok: true, locale: 'zh-CN', mode: 'static', source: ORIGIN, builtAt: S.builtAt});
    if (path === '/__local/refresh-status') return json(S.status || {});
    if (path === '/__local/translations') return nativeFetch(BASE + 'translations.json');
    if (path === '/__local/ui-strings') return nativeFetch(BASE + 'ui-strings.json');
    if (path === '/__local/translation-cache') return json({saved: 0, mode: 'static'});
    if (path === '/__local/refresh' && method === 'POST') return json({error: '此静态版本由 GitHub Actions 定时更新，无法在页面上手动触发检查。'}, 403);
    return json({ok: true});
  }

  async function staticFetch(input, init) {
    const request = input instanceof Request ? input : null;
    const raw = request ? request.url : String(input instanceof URL ? input.href : input);
    const url = sameOrigin(raw);
    if (!url) {
      if (/google-analytics\.com|plausible\.io|cloudflareinsights\.com/.test(raw)) return new Response(null, {status: 204});
      return nativeFetch(input, init);
    }
    const path = strip(url.pathname);
    const method = ((init && init.method) || (request && request.method) || 'GET').toUpperCase();
    if (path.startsWith('/__local/')) return local(path, method);
    if (path.startsWith('/__rt/') || path.startsWith('/cdn-cgi/')) return json({ok: true});
    if (path.startsWith('/v1/api/auth/') || path.startsWith('/v1/api/account')) {
      return json({user: null, session: null, error: '中文镜像不连接原站账户。请前往原站登录。'}, 401);
    }
    if (DATA.test(path)) {
      let body = init && init.body;
      if (body == null && request && method !== 'GET' && method !== 'HEAD') body = await request.clone().text();
      if (body != null && typeof body !== 'string') body = String(body);
      if (method !== 'GET' && method !== 'HEAD' && path !== '/v1/api/compat/query') {
        return json({error: '此为简体中文镜像。账户登录、投稿和个人数据操作请前往原站。'}, 403);
      }
      const entry = S.entries[canonical(url, method === 'GET' || method === 'HEAD' ? null : body)];
      if (!entry) {
        const blocked = S.blocked.includes(path);
        return json({error: blocked ? '原站限制自动访问此数据，静态镜像未收录。请前往原站查看实时内容。' : '静态镜像未收录此数据，请前往原站查看。'}, blocked ? 503 : 404,
          {'X-Mirror-Cache': blocked ? 'blocked' : 'missing'});
      }
      const response = await nativeFetch(SNAPSHOT + entry.f, {signal: init && init.signal, cache: 'no-cache'});
      if (!response.ok) return response;
      return new Response(response.body, {status: 200, headers: {
        'Content-Type': entry.t, 'X-Mirror-Key': entry.k, 'X-Mirror-Cache': entry.s,
        'X-Mirror-Checked-At': entry.c || '', 'X-Mirror-Changed-At': entry.m || ''}});
    }
    if (BASE !== '/' && !url.pathname.startsWith(BASE)) {
      const target = BASE + url.pathname.slice(1) + url.search;
      return request ? nativeFetch(new Request(target, request), init) : nativeFetch(target, init);
    }
    return nativeFetch(input, init);
  }
  window.fetch = staticFetch;

  const xhrOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, raw, ...rest) {
    return xhrOpen.call(this, method, typeof raw === 'string' && String(method).toUpperCase() === 'GET' ? rewrite(raw) : raw, ...rest);
  };

  const URL_ATTRS = new Set(['src', 'href', 'poster', 'xlink:href']);
  const setAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function (name, value) {
    if (URL_ATTRS.has(String(name).toLowerCase()) && typeof value === 'string') value = rewrite(value);
    else if (String(name).toLowerCase() === 'srcset' && typeof value === 'string') value = value.split(',').map(part => { const [u, ...d] = part.trim().split(/\s+/); return [rewrite(u), ...d].join(' '); }).join(', ');
    return setAttribute.call(this, name, value);
  };
  for (const [Type, prop] of [[HTMLImageElement, 'src'], [HTMLSourceElement, 'src'], [HTMLScriptElement, 'src'], [HTMLLinkElement, 'href'], [HTMLAnchorElement, 'href'], [HTMLMediaElement, 'src']]) {
    const descriptor = Object.getOwnPropertyDescriptor(Type.prototype, prop);
    if (!descriptor || !descriptor.set) continue;
    Object.defineProperty(Type.prototype, prop, {...descriptor, set(value) { descriptor.set.call(this, rewrite(value)); }});
  }
  const open = window.open;
  window.open = function (raw, ...rest) { return open.call(this, rewrite(raw), ...rest); };
})();
