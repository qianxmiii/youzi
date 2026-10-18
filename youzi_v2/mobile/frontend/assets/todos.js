(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const api = window.YouziMobile.api;
  let active = false, visible = false, page = 1, total = 0, scope = 'pending', search = '';
  let request, mutation, generation = 0, scroll = 0;
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text != null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  }
  function errorText(error) { return error.name === 'AbortError' ? '连接超时，请刷新确认处理结果。' : error.message || '加载失败，请重试。'; }
  async function update(row, action, button) {
    if (mutation || !active || !visible) return;
    const current = generation;
    const controller = mutation = new AbortController();
    button.disabled = true;
    $('todo-status').textContent = '正在保存…';
    try {
      await api('todos/' + encodeURIComponent(row.id) + '/' + action, {}, { signal: controller.signal });
      if (active && visible && generation === current) await load();
    } catch (error) {
      if (active && visible && generation === current) $('todo-status').textContent = errorText(error);
    } finally {
      if (mutation === controller) mutation = null;
      button.disabled = false;
    }
  }
  async function load() {
    if (!active || !visible) return;
    request?.abort();
    const controller = request = new AbortController();
    $('todo-status').textContent = '正在加载待办…';
    $('todo-retry').hidden = true;
    $('todo-list').replaceChildren(); $('todo-page').textContent = '';
    $('todo-prev').disabled = $('todo-next').disabled = true;
    try {
      const data = await api('todos?' + new URLSearchParams({ scope, search, page: String(page), page_size: '20' }), undefined, { signal: controller.signal });
      if (!active || !visible || request !== controller || controller.signal.aborted) return;
      total = data.total;
      if (!data.items.length && page > 1) { page = Math.max(1, Math.ceil(total / 20)); return load(); }
      for (const row of data.items) {
        const card = node('article', null, 'todo-card');
        const heading = node('div', null, 'card-heading');
        heading.append(node('strong', row.shipmentNo), node('span', row.resolvedAt ? '已完成' : row.readAt ? '已读 · 待处理' : '未读 · 待处理', 'status-pill'));
        card.append(heading, node('p', [row.customer, row.exceptionNameZh || row.exceptionCode].filter(Boolean).join(' · ')), node('p', row.message), node('small', '提醒时间 ' + (row.triggeredAt || '未记录')));
        if (row.resolvedAt) card.append(node('p', '完成时间 ' + row.resolvedAt, 'data-hint'));
        const actions = node('div', null, 'todo-actions');
        if (row.shipmentAvailable) {
          const open = node('button', '查看运单', 'secondary'); open.type = 'button';
          open.addEventListener('click', () => { location.hash = 'todo-shipment/' + (row.workspace || 'transit') + '/' + encodeURIComponent(row.shipmentId); });
          actions.append(open);
        }
        if (!row.resolvedAt) {
          if (!row.readAt) {
            const read = node('button', '标为已读', 'secondary'); read.type = 'button';
            read.addEventListener('click', () => { void update(row, 'read', read); }); actions.append(read);
          }
          const resolve = node('button', '完成本次跟进'); resolve.type = 'button';
          resolve.addEventListener('click', () => { void update(row, 'resolve', resolve); }); actions.append(resolve);
        }
        card.append(actions); $('todo-list').append(card);
      }
      $('todo-status').textContent = total ? `符合筛选 ${total} 条 · 全部待处理 ${data.pendingCount} 条` : `暂无符合筛选的异常跟进提醒 · 全部待处理 ${data.pendingCount} 条`;
      $('todo-page').textContent = `${page} / ${Math.max(1, Math.ceil(total / 20))}`;
      $('todo-prev').disabled = page <= 1; $('todo-next').disabled = page * 20 >= total;
      window.scrollTo(0, scroll);
    } catch (error) {
      if (!active || !visible || request !== controller || controller.signal.aborted) return;
      $('todo-status').textContent = errorText(error); $('todo-retry').hidden = false;
    }
  }
  function route() {
    const next = active && location.hash === '#todos';
    if (visible === next) return;
    if (visible) scroll = window.scrollY || 0;
    visible = next; generation++; request?.abort(); mutation?.abort(); mutation = null;
    $('todos-module').hidden = !visible;
    if (visible) void load();
  }
  window.addEventListener('mobile-auth-state', (event) => {
    active = event.detail.authenticated;
    if (!active) {
      generation++; request?.abort(); mutation?.abort(); mutation = null;
      visible = false; page = 1; total = 0; scope = 'pending'; search = ''; scroll = 0;
      $('todos-module').hidden = true; $('todo-list').replaceChildren();
      $('todo-status').textContent = ''; $('todo-page').textContent = '';
      $('todo-search').value = ''; $('todo-scope').value = 'pending';
    } else route();
  });
  window.addEventListener('hashchange', route);
  $('todo-scope').addEventListener('change', () => { scope = $('todo-scope').value; page = 1; scroll = 0; void load(); });
  $('todo-search-form').addEventListener('submit', (event) => { event.preventDefault(); search = $('todo-search').value.trim(); page = 1; scroll = 0; void load(); });
  $('todo-prev').addEventListener('click', () => { if (page > 1) { page--; scroll = 0; void load(); } });
  $('todo-next').addEventListener('click', () => { if (page * 20 < total) { page++; scroll = 0; void load(); } });
  $('todo-retry').addEventListener('click', () => { void load(); });
})();
