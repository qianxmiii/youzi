(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const api = window.YouziMobile.api;
  let active = false, visible = false, mode = 'all', summary = null, request;
  const tones = new Set(['EXPORT_CUSTOMS_EXCEPTION', 'IMPORT_CUSTOMS_EXCEPTION', 'WAREHOUSE_IN', 'EXPORT_CUSTOMS_RELEASE', 'DEPARTED_POL', 'ARRIVED_POD', 'DEST_TRANSIT_WAREHOUSE', 'TRUCK_DISPATCH_APPOINTED', 'LAST_MILE_HANDOVER', 'TRACK_SIGNED', 'missing', 'exception']);
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text != null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }
  function render() {
    $('home-cards').replaceChildren();
    $('home-messages').replaceChildren();
    for (const key of ['unsigned', 'arrived', 'signed', 'pending']) $('overview-' + key).textContent = '—';
    $('home-date').textContent = '';
    $('home-todo-count').textContent = '—';
    $('home-todo-description').textContent = '等待加载提醒';
    for (const key of ['all', 'today']) {
      $('home-' + key).className = key === mode ? '' : 'secondary';
      $('home-' + key).setAttribute('aria-pressed', String(key === mode));
    }
    $('home-heading').textContent = mode === 'all' ? '明细状态' : '今日动态';
    $('home-description').textContent = mode === 'all'
      ? '与电脑端全部明细状态统计口径一致，按运单当前状态计数。'
      : '按电脑本机日期及节点发生时间统计，同一运单可出现在多个今日节点中。';
    if (!summary) return;
    const todayCounts = Object.fromEntries(summary.todayItems.map((item) => [item.code, item.count]));
    const pending = summary.pendingCount ?? 0;
    $('overview-unsigned').textContent = summary.unsignedTotal;
    $('overview-arrived').textContent = todayCounts.TODAY_ARRIVED ?? 0;
    $('overview-signed').textContent = todayCounts.TODAY_ROUTE_SIGNED ?? 0;
    $('overview-pending').textContent = pending;
    $('home-date').textContent = summary.today;
    $('home-todo-count').textContent = pending;
    $('home-todo-description').textContent = pending ? `${pending} 条异常提醒待处理` : '当前没有待处理提醒';
    for (const item of summary.recentTodos || []) {
      const button = node('button', null, 'message-row'); button.type = 'button';
      const heading = node('div', null, 'message-heading');
      const time = item.triggeredAt || '';
      heading.append(node('strong', item.title || '异常跟进提醒'), node('time', time.startsWith(summary.today) ? time.slice(11, 16) : time.slice(5, 16)));
      button.append(heading, node('p', item.message));
      button.addEventListener('click', () => { location.hash = 'todos'; });
      $('home-messages').append(button);
    }
    if (!(summary.recentTodos || []).length) $('home-messages').append(node('p', '暂无待处理提醒', 'dashboard-empty'));
    $('home-status').textContent = mode === 'all' ? `未签收 ${summary.unsignedTotal} 票` : summary.today;
    for (const item of mode === 'all' ? summary.items : summary.todayItems) {
      const tone = tones.has(item.tone) ? item.tone : 'missing';
      const card = node('article', null, 'home-card tone-' + tone);
      card.append(node('h3', item.nameZh), node('strong', item.count));
      $('home-cards').append(card);
    }
    $('home-updated').textContent = '更新于 ' + new Date(summary.generatedAt).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
  }
  async function load() {
    if (!active || !visible) return;
    request?.abort();
    const controller = request = new AbortController();
    summary = null; render(); $('home-updated').textContent = '';
    $('dashboard-status').textContent = '正在更新工作台…';
    $('home-status').textContent = '正在加载统计…';
    try {
      const data = await api('home', undefined, { signal: controller.signal });
      if (!active || !visible || controller !== request || controller.signal.aborted) return;
      summary = data; render(); $('dashboard-status').textContent = '';
    } catch (error) {
      if (!active || !visible || controller !== request || controller.signal.aborted) return;
      $('home-status').textContent = error.name === 'AbortError' ? '连接超时，请点击刷新统计重试。' : error.message || '加载失败，请点击刷新统计重试。';
      $('dashboard-status').textContent = $('home-status').textContent;
    }
  }
  function route() {
    const next = active && ['', '#home'].includes(location.hash);
    if (next === visible) return;
    visible = next; request?.abort(); $('home-module').hidden = !visible;
    if (visible) { window.scrollTo(0, 0); void load(); }
  }
  window.addEventListener('mobile-auth-state', (event) => {
    active = event.detail.authenticated;
    if (!active) {
      request?.abort(); summary = null; mode = 'all'; visible = false;
      render();
      $('home-module').hidden = true; $('home-cards').replaceChildren();
      for (const id of ['home-status', 'home-updated', 'home-description', 'dashboard-status']) $(id).textContent = '';
    } else if (visible) void load();
    else route();
  });
  window.addEventListener('hashchange', route);
  for (const key of ['all', 'today']) $('home-' + key).addEventListener('click', () => { mode = key; render(); });
  $('home-refresh').addEventListener('click', () => { void load(); });
  for (const id of ['home-todo-all', 'home-todo-open', 'home-message-all']) $(id).addEventListener('click', () => { location.hash = 'todos'; });
  for (const key of ['preport', 'transit', 'todos', 'account']) $('quick-' + key).addEventListener('click', () => {
    location.hash = ['preport', 'transit'].includes(key) ? 'shipments/' + key : key;
  });
})();
