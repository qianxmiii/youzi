(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const api = window.YouziMobile.api;
  let active = false;
  let workspace = 'transit';
  let status = '2';
  let customer = '';
  let viewKey = '';
  let listKey = '';
  const saved = {};
  let page = 1;
  let query = '';
  let total = 0;
  let selectedId = '';
  let source = 'internal';
  let trackingPage = 1;
  let listRequest, detailRequest, trackingRequest;
  const coarseLabels = { IN_TRANSIT: '转运中', DELIVERED: '已签收', INSPECTION: '查验', UNKNOWN: '未知', '2': '转运中', '3': '已签收', '0': '已下单', '01': '提货中', '1': '已入仓', '4': '已取消' };

  function node(tag, text, className) {
    const value = document.createElement(tag);
    if (text != null) value.textContent = String(text);
    if (className) value.className = className;
    return value;
  }
  function label(row) { return (row.workspace === 'preport' ? row.statusLabel : row.routeStatusLabel) || row.statusLabel || coarseLabels[row.statusCode] || row.statusCode || '未知状态'; }
  function errorText(error) { return error.name === 'AbortError' ? '加载超时，请检查网络后重试' : error.message || '加载失败，请重试'; }
  function cancelRequests() { listRequest?.abort(); detailRequest?.abort(); trackingRequest?.abort(); }

  function clear() {
    active = false;
    cancelRequests();
    page = 1; query = ''; selectedId = ''; total = 0; workspace = 'transit'; status = '2'; customer = '';
    viewKey = ''; listKey = '';
    for (const key of Object.keys(saved)) delete saved[key];
    $('account').hidden = true; $('mobile-navigation').hidden = true;
    $('shipment-search').value = '';
    $('shipment-customer').replaceChildren(); $('shipment-customer').value = '';
    for (const id of ['shipment-list', 'shipment-detail', 'tracking-list']) $(id).replaceChildren();
    for (const id of ['list-status', 'detail-status', 'tracking-status', 'list-page']) $(id).textContent = '';
    $('shipments-module').hidden = true;
    history.replaceState(null, '', location.pathname + location.search);
  }

  async function loadList() {
    if (!active) return;
    listRequest?.abort();
    const request = listRequest = new AbortController();
    listKey = '';
    $('list-status').textContent = '正在加载运单…';
    $('list-retry').hidden = true;
    $('shipment-list').replaceChildren();
    $('list-page').textContent = '';
    $('list-prev').disabled = $('list-next').disabled = true;
    try {
      const data = await api('shipments?' + new URLSearchParams({ workspace, status, customer, search: query, page: String(page), page_size: '20' }), undefined, { signal: request.signal });
      if (!active || request !== listRequest || request.signal.aborted) return;
      const customers = $('shipment-customer');
      const all = node('option', '全部客户'); all.value = '';
      customers.replaceChildren(all);
      for (const name of new Set([...(data.customers || []), ...(customer ? [customer] : [])])) {
        const option = node('option', name); option.value = name; customers.append(option);
      }
      customers.value = customer;
      total = data.total;
      if (!data.items.length && page > 1) { page = Math.max(1, Math.ceil(total / 20)); return loadList(); }
      for (const row of data.items) {
        const button = node('button', null, 'shipment-card');
        button.type = 'button';
        const heading = node('div', null, 'card-heading');
        heading.append(node('strong', row.shipmentNo), node('span', label(row), 'status-pill'));
        button.append(heading, node('p', [row.customer, row.channelNameZh || row.channelCode].filter(Boolean).join(' · ') || '客户 / 渠道未填写'));
        const reference = row.customerShipmentId || row.customerNo;
        if (reference) button.append(node('p', reference, 'reference'));
        button.append(node('p', workspace === 'preport' ? ['收货仓 ' + (row.originWarehouseCode || '未填写'), '计费重 ' + (row.chargedWeight ?? '未填写')].join(' · ') : row.latestTrackingDesc || row.latestCarrierDesc || '暂无轨迹摘要', 'card-summary'));
        button.append(node('small', '本地更新 ' + (row.updatedTime || '未记录')));
        button.addEventListener('click', () => { saveList(); location.hash = 'shipments/' + workspace + '/' + encodeURIComponent(row.id); });
        $('shipment-list').append(button);
      }
      listKey = JSON.stringify([workspace, status, customer, query, page]);
      window.scrollTo(0, saved[workspace]?.scroll || 0);
      $('list-status').textContent = total ? `共 ${total} 条运单` : (query || customer) ? '没有符合当前筛选的运单，请调整客户、状态或关键词。' : '暂无运单数据。';
      $('list-page').textContent = `${page} / ${Math.max(1, Math.ceil(total / 20))}`;
      $('list-prev').disabled = page <= 1;
      $('list-next').disabled = page * 20 >= total;
    } catch (error) {
      if (!active || request !== listRequest || request.signal.aborted) return;
      $('list-status').textContent = errorText(error);
      $('list-retry').hidden = false;
    }
  }

  function renderDetail(row) {
    const container = $('shipment-detail');
    container.replaceChildren(node('h2', row.shipmentNo), node('span', label(row), 'status-pill'));
    const fields = [
      ['收货仓', row.originWarehouseCode], ['计费重', row.chargedWeight],
      ['客户', row.customer], ['客户编号', row.customerNo], ['货件号', row.customerShipmentId],
      ['关联单号', row.refShipmentNo], ['渠道', row.channelNameZh || row.channelCode],
      ['承运商', row.workspace === 'preport' ? null : row.carrierNameZh || row.carrierCode], ['国家', row.countryCode],
      ['派送仓库', row.addressCode], ['邮编', row.zipcode], ['件数', row.ctns],
      ['品名', row.productName], ['转单号', row.trackingNumber], ['船名航次', row.vesselVoyage],
      ['预计开船', row.etd], ['实际开船', row.atd], ['预计到港', row.eta], ['实际到港', row.ata],
      ['预计送仓', row.expectedDeliveryTime], ['入仓时间', row.warehouseEntryTime], ['签收时间', row.deliveredTime],
    ];
    const list = node('dl', null, 'detail-fields');
    for (const [name, value] of fields) {
      if (value == null || value === '') continue;
      const pair = node('div'); pair.append(node('dt', name), node('dd', value)); list.append(pair);
    }
    container.append(list, node('p', '本地更新：' + (row.updatedTime || '未记录'), 'data-hint'));
    if (row.workspace === 'preport') return;
    for (const [title, time, description] of [
      ['最新内部轨迹', row.latestTrackingTime, row.latestTrackingDesc],
      ['最新承运商轨迹', row.latestCarrierTime, row.latestCarrierDesc],
    ]) {
      if (!description) continue;
      container.append(node('h3', title), node('p', time || '时间未记录', 'data-hint'), node('p', description));
    }
  }

  async function loadDetail(id) {
    detailRequest?.abort(); trackingRequest?.abort();
    selectedId = id; source = 'internal'; trackingPage = 1;
    const request = detailRequest = new AbortController();
    $('shipment-detail').replaceChildren(); $('tracking-list').replaceChildren();
    $('detail-status').textContent = '正在加载详情…';
    $('tracking-section').hidden = true; $('detail-retry').hidden = true;
    try {
      const row = await api('shipments/' + encodeURIComponent(id), undefined, { signal: request.signal });
      if (!active || request !== detailRequest || request.signal.aborted) return;
      renderDetail(row);
      $('detail-status').textContent = '';
      if (row.workspace !== 'preport') {
        $('tracking-section').hidden = false;
        await loadTracking(false);
      }
    } catch (error) {
      if (!active || request !== detailRequest || request.signal.aborted) return;
      $('detail-status').textContent = errorText(error); $('detail-retry').hidden = false;
    }
  }

  async function loadTracking(append) {
    if (!active || !selectedId) return;
    trackingRequest?.abort();
    const request = trackingRequest = new AbortController();
    $('tracking-status').textContent = '正在加载轨迹…';
    $('tracking-more').hidden = true; $('tracking-retry').hidden = true;
    for (const key of ['internal', 'carrier']) {
      $('tracking-' + key).className = source === key ? '' : 'secondary';
      $('tracking-' + key).setAttribute('aria-pressed', String(source === key));
    }
    if (!append) $('tracking-list').replaceChildren();
    try {
      const data = await api('shipments/' + encodeURIComponent(selectedId) + '/tracking?' + new URLSearchParams({ source, page: String(trackingPage), page_size: '30' }), undefined, { signal: request.signal });
      if (!active || request !== trackingRequest || request.signal.aborted) return;
      for (const entry of data.items) {
        const item = node('li');
        item.append(node('time', entry.trackingTime || '时间未记录'), node('p', entry.trackingDesc || '暂无说明'));
        $('tracking-list').append(item);
      }
      $('tracking-status').textContent = data.total ? `共 ${data.total} 条，按时间倒序` : '暂无该来源的轨迹记录。';
      $('tracking-more').hidden = trackingPage * 30 >= data.total;
    } catch (error) {
      if (!active || request !== trackingRequest || request.signal.aborted) return;
      $('tracking-status').textContent = errorText(error); $('tracking-retry').hidden = false;
    }
  }

  function saveList() {
    saved[workspace] = { page, query, status, customer, scroll: window.scrollY || 0 };
  }
  function route() {
    if (!active) return;
    const home = ['', '#home'].includes(location.hash);
    if (home || location.hash === '#todos') {
      if (viewKey === workspace + '/') saveList();
      cancelRequests(); viewKey = home ? 'home' : 'todos';
      $('account').hidden = true; $('shipments-module').hidden = true;
      $('mobile-navigation').hidden = false;
      $('title').textContent = home ? '欢迎回来' : '我的待办'; $('intro').textContent = home ? '查看物流动态，安排今天的跟进' : '查看和处理异常跟进提醒';
      for (const key of ['home', 'shipments', 'account', 'todos']) {
        const selected = key === (home ? 'home' : 'todos');
        $('nav-' + key).className = selected ? '' : 'secondary';
        $('nav-' + key).setAttribute('aria-current', selected ? 'page' : 'false');
      }
      return;
    }
    const account = location.hash === '#account';
    const match = /^#(?:shipments|todo-shipment)\/(preport|transit)(?:\/(.+))?$/.exec(location.hash);
    const target = match ? match[1] : workspace;
    const detail = Boolean(match?.[2]);
    $('account').hidden = !account;
    $('shipments-module').hidden = account;
    $('mobile-navigation').hidden = detail;
    $('shipment-list-panel').hidden = detail;
    $('shipment-detail-panel').hidden = !detail;
    $('title').textContent = account ? '我的' : detail ? '运单详情' : '运单查询';
    $('intro').textContent = account ? '个人账号与登录管理' : detail ? '查看电脑已有的运单信息' : '港前与在途分类和电脑端一致';
    for (const key of ['shipments', 'account']) {
      $('nav-' + key).className = (account === (key === 'account')) ? '' : 'secondary';
      $('nav-' + key).setAttribute('aria-current', account === (key === 'account') ? 'page' : 'false');
    }
    $('nav-todos').className = 'secondary'; $('nav-todos').setAttribute('aria-current', 'false');
    $('nav-home').className = 'secondary'; $('nav-home').setAttribute('aria-current', 'false');
    const nextKey = account ? 'account' : target + '/' + (match?.[2] || '');
    if (nextKey === viewKey) return;
    if (viewKey === workspace + '/') saveList();
    cancelRequests();
    viewKey = nextKey;
    if (account) { window.scrollTo(0, 0); return; }
    if (target !== workspace) {
      workspace = target;
      const previous = saved[workspace];
      page = previous?.page || 1; query = previous?.query || '';
      status = previous?.status || (workspace === 'transit' ? '2' : 'all');
      customer = previous?.customer || '';
      $('shipment-customer').replaceChildren();
      $('shipment-customer').value = customer;
    }
    $('shipment-search').value = query;
    const select = $('shipment-status');
    select.replaceChildren();
    for (const value of workspace === 'preport' ? ['all', '0', '01', '1', '4'] : ['2', '3', 'all']) {
      const option = node('option', value === 'all' ? '全部状态' : coarseLabels[value]);
      option.value = value; select.append(option);
    }
    select.value = status;
    for (const key of ['preport', 'transit']) {
      $('workspace-' + key).className = workspace === key ? '' : 'secondary';
      $('workspace-' + key).setAttribute('aria-pressed', String(workspace === key));
    }
    if (detail) {
      window.scrollTo(0, 0);
      try { void loadDetail(decodeURIComponent(match[2])); }
      catch { $('detail-status').textContent = '运单地址无效，请返回列表。'; }
    } else {
      selectedId = '';
      if (listKey !== JSON.stringify([workspace, status, customer, query, page])) void loadList();
      else window.scrollTo(0, saved[workspace]?.scroll || 0);
    }
  }
  window.addEventListener('mobile-auth-state', (event) => {
    if (!event.detail.authenticated) { clear(); return; }
    active = true; route();
  });
  for (const key of ['preport', 'transit']) $('workspace-' + key).addEventListener('click', () => { location.hash = 'shipments/' + key; });
  $('nav-shipments').addEventListener('click', () => { location.hash = 'shipments/' + workspace; });
  $('nav-account').addEventListener('click', () => { location.hash = 'account'; });
  $('nav-todos').addEventListener('click', () => { location.hash = 'todos'; });
  $('nav-home').addEventListener('click', () => { location.hash = 'home'; });
  $('shipment-customer').addEventListener('change', () => { customer = $('shipment-customer').value; page = 1; saveList(); saved[workspace].scroll = 0; void loadList(); });
  $('shipment-status').addEventListener('change', () => { status = $('shipment-status').value; page = 1; saveList(); saved[workspace].scroll = 0; void loadList(); });
  window.addEventListener('hashchange', route);
  $('search-form').addEventListener('submit', (event) => { event.preventDefault(); query = $('shipment-search').value.trim(); page = 1; saveList(); saved[workspace].scroll = 0; void loadList(); });
  $('list-prev').addEventListener('click', () => { if (page > 1) { page--; void loadList(); } });
  $('list-next').addEventListener('click', () => { if (page * 20 < total) { page++; void loadList(); } });
  $('list-retry').addEventListener('click', () => { void loadList(); });
  $('detail-retry').addEventListener('click', () => { if (selectedId) void loadDetail(selectedId); });
  $('detail-back').addEventListener('click', () => { location.hash = location.hash.startsWith('#todo-shipment/') ? 'todos' : 'shipments/' + workspace; });
  for (const key of ['internal', 'carrier']) $('tracking-' + key).addEventListener('click', () => { source = key; trackingPage = 1; void loadTracking(false); });
  $('tracking-more').addEventListener('click', () => { trackingPage++; void loadTracking(true); });
  $('tracking-retry').addEventListener('click', () => { void loadTracking(trackingPage > 1); });
})();
