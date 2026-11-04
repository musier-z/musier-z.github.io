/* Local Chinese update controls; the original React bundle remains pinned. */
(() => {
  'use strict';
  const originalFetch = window.fetch.bind(window);
  const loaded = new Map();
  let panel, entry, state, timer, pending = false, active = false, disconnected = false;
  let previousFocus;
  // Read cache metadata without consuming or altering the application response.
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    const key = response.headers.get('X-Mirror-Key');
    if (key) {
      loaded.set(key, {
        checkedAt: response.headers.get('X-Mirror-Checked-At'),
        changedAt: response.headers.get('X-Mirror-Changed-At'),
        stale: ['stale', 'blocked'].includes(response.headers.get('X-Mirror-Cache'))
      });
      if (state) render();
    }
    return response;
  };
  const date = value => value ? new Date(value).toLocaleString('zh-CN', {hour12: false}) : '尚无记录';
  const interval = seconds => seconds >= 86400 ? `${seconds / 86400} 天` : seconds >= 3600 ? `${seconds / 3600} 小时` : `${seconds / 60} 分钟`;
  function setText(selector, text) { panel.querySelector(selector).textContent = text; }
  function render() {
    if (!panel || !state) return;
    const job = state.job;
    const running = job && job.running;
    const changed = state.records.filter(record => {
      const view = loaded.get(record.key);
      // Legacy cache entries have no changedAt; any later changedAt is new.
      return view && record.changedAt && record.changedAt > (view.changedAt || view.checkedAt || '');
    }).length;
    const oldOnScreen = [...loaded.values()].some(value => value.stale);
    const label = disconnected ? '更新状态离线' : state.blocked ? `数据更新 · ${state.blocked} 项受限` : state.failed ? `数据更新 · ${state.failed} 项重试` : running ? '数据更新中' : changed ? '有新数据' : '数据更新';
    entry.textContent = label;
    entry.dataset.warning = String(disconnected || state.failed > 0 || state.blocked > 0 || oldOnScreen);
    setText('.sync-state', disconnected ? '暂时无法连接本地服务' : state.schedulerRunning ? '自动更新已开启' : '自动更新已关闭');
    setText('.sync-intro', `已收录 ${state.total} 组公开数据；${state.refreshing} 组检查中或排队（最多 ${state.workers} 组并行），${state.stale} 组超过检查间隔，${state.failed} 组等待重试，${state.blocked || 0} 组访问受限。`);
    setText('.sync-checked', `上次调度检查：${date(state.lastSweepAt)}（本机时区）`);
    panel.querySelector('.sync-offline').hidden = !disconnected;
    panel.querySelector('.sync-warning').hidden = !(state.failed || oldOnScreen);
    panel.querySelector('.sync-blocked').hidden = !state.blocked;
    setText('.sync-warning', state.failed ? '部分数据未能完成更新，页面可能仍显示上次成功缓存。实时状态、候车时间请结合原始采样日期判断。' : '此次浏览曾读取过期缓存。更新检查成功后，可重新载入页面以应用数据。');
    setText('.sync-apply', changed ? `此次浏览已读取的数据中，有 ${changed} 组缓存内容发生变化。重新载入页面即可应用。` : '后台更新缓存；页面自带实时模块继续轮询。其他已打开图表可重新载入页面以应用数据。');
    const tbody = panel.querySelector('tbody');
    tbody.replaceChildren();
    state.groups.forEach(group => {
      const tr = document.createElement('tr');
      const values = [group.label, interval(group.intervalSeconds),
        group.total ? `${group.total} 组${group.blocked ? ` · ${group.blocked} 组受限` : ''}${group.failed ? ` · ${group.failed} 组重试` : group.stale ? ` · ${group.stale} 组到期` : ' · 已检查'}` : '按访问收录',
        group.total ? date(group.oldestCheckedAt) : '—'];
      values.forEach(value => { const td = document.createElement('td'); td.textContent = value; tr.append(td); });
      tbody.append(tr);
    });
    const failures = panel.querySelector('.sync-failures');
    failures.hidden = !state.failed;
    failures.querySelector('ul').replaceChildren();
    state.groups.filter(group => group.failed).forEach(group => {
      const li = document.createElement('li');
      li.textContent = `${group.label}：${group.failed} 组，最早重试 ${date(group.nextRetryAt)}。${(group.failureReasons || []).join('；')}`;
      failures.querySelector('ul').append(li);
    });
    let progress = '手动检查所有已收录的公开数据，图片除外。失败重试中的数据仍遵守退避时间。';
    if (job) {
      progress = `${running ? '正在检查' : job.cancelled ? '检查已中断' : '检查完成'} ${job.done}/${job.total}：内容变化 ${job.changed}，无变化 ${job.unchanged}，失败 ${job.failed}，退避等待 ${job.deferred}，访问受限 ${job.blocked || 0}。`;
    }
    setText('.sync-progress', progress);
    const button = panel.querySelector('.sync-refresh');
    const cooling = Date.parse(state.manualAvailableAt) > Date.parse(state.serverTime);
    button.disabled = pending || running || cooling || disconnected;
    button.textContent = running ? '正在检查…' : cooling ? '稍后可再次检查' : '立即检查更新';
  }
  async function poll() {
    if (active) return;
    active = true;
    clearTimeout(timer);
    try {
      const response = await originalFetch('/__local/refresh-status', {cache: 'no-store', signal: AbortSignal.timeout(10000)});
      if (!response.ok) throw new Error('status');
      state = await response.json();
      disconnected = false;
      render();
    } catch (_) {
      disconnected = true;
      if (state) render();
      else {
        entry.textContent = '更新状态离线';
        panel.querySelector('.sync-offline').hidden = false;
        setText('.sync-state', '暂时无法连接本地服务');
      }
    } finally {
      active = false;
      if (!document.hidden) timer = setTimeout(poll, panel.open && state?.job?.running ? 2000 : panel.open ? 10000 : 30000);
    }
  }
  function setup() {
    entry = document.createElement('button');
    entry.className = 'sync-entry';
    entry.type = 'button';
    entry.setAttribute('data-no-translate', '');
    entry.setAttribute('aria-haspopup', 'dialog');
    entry.textContent = '数据更新';
    panel = document.createElement('dialog');
    panel.className = 'sync-panel';
    panel.setAttribute('data-no-translate', '');
    panel.setAttribute('aria-labelledby', 'sync-title');
    panel.innerHTML = `
      <div class="sync-heading"><h2 id="sync-title">镜像数据更新</h2><button class="sync-close" aria-label="关闭数据更新面板">×</button></div>
      <p class="sync-state" role="status">正在读取更新状态…</p>
      <p class="sync-intro"></p><p class="sync-checked"></p>
      <p class="sync-offline sync-alert" hidden>服务停止或连接中断。服务恢复后将继续检查；目前无法确认数据新鲜度。</p>
      <p class="sync-warning sync-alert" hidden></p>
      <p class="sync-blocked sync-alert" hidden>原站部分接口限制自动访问，已停止这些接口的自动重试，手动检查也不会绕过限制。对应模块使用已有缓存；请前往原站确认当前信息。</p>
      <div class="sync-table-wrap"><table><caption>检查间隔与成功检查时间</caption><thead><tr><th>数据类型</th><th>间隔</th><th>状态</th><th>该类最早成功检查</th></tr></thead><tbody></tbody></table></div>
      <details class="sync-failures" hidden><summary>查看重试安排</summary><ul></ul></details>
      <p class="sync-note">以上是镜像检查原站的间隔，不代表原始数据的发布日期或统计日期。历史分页和车辆／用户详情按访问更新；人口地理数据每天检查。前端程序与翻译词库不在数据定时更新范围内。</p>
      <p class="sync-progress" role="status"></p>
      <p class="sync-apply"></p>
      <div class="sync-actions"><button class="sync-refresh" disabled>立即检查更新</button><button class="sync-reload">重新载入页面</button></div>
      <p class="sync-note">服务运行且联网时自动检查；断网或更新失败时保留成功缓存并逐步延长重试间隔。重新载入会重置当前页面的临时筛选。</p>`;
    document.body.append(entry, panel);
    entry.addEventListener('click', () => { previousFocus = document.activeElement; panel.showModal(); poll(); });
    panel.querySelector('.sync-close').addEventListener('click', () => panel.close());
    panel.addEventListener('close', () => previousFocus?.focus());
    panel.addEventListener('click', event => { if (event.target === panel) { const box = panel.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) panel.close(); } });
    panel.querySelector('.sync-reload').addEventListener('click', () => location.reload());
    panel.querySelector('.sync-refresh').addEventListener('click', async () => {
      pending = true; render();
      try {
        const response = await originalFetch('/__local/refresh', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Mirror-Action': 'refresh'}, body: '{}', signal: AbortSignal.timeout(10000)});
        if (!response.ok) throw new Error('refresh');
        await response.json();
        await poll();
      } catch (_) {
        setText('.sync-progress', '未能确认手动检查状态，将重新读取进度；请勿连续重复提交。');
      } finally { pending = false; if (state) render(); }
    });
    document.addEventListener('visibilitychange', () => { clearTimeout(timer); if (!document.hidden) poll(); });
    poll();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup, {once: true});
  else setup();
})();
