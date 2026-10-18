'use strict';
const el = (id) => document.getElementById(id);
let initialized = false;
let busy = false;

async function api(path, body, options = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  if (options.signal?.aborted) controller.abort();
  const timer = setTimeout(abort, 15000);
  try {
  const response = await fetch('/api/mobile/' + path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: body === undefined ? {} : { 'Content-Type': 'application/json', 'X-Youzi-Mobile': '1' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: controller.signal,
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401 && ['请先登录', '请重新登录'].includes(data.detail)) {
      showState({ initialized: true, authenticated: false });
    }
    throw new Error(data.detail || '操作未完成，请重试');
  }
  return data;
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', abort);
  }
}

function clearPasswords() {
  document.querySelectorAll('input[type="password"]').forEach((input) => { input.value = ''; });
}

function showState(state) {
  initialized = state.initialized;
  clearPasswords();
  el('credentials').hidden = state.authenticated;
  if (!state.authenticated) el('account').hidden = true;
  el('account-name').textContent = state.authenticated ? state.username : '';
  el('title').textContent = state.authenticated ? '欢迎回来' : initialized ? '登录个人工作台' : '设置你的个人账号';
  el('intro').textContent = state.authenticated ? '你的个人手机入口已准备好。' : initialized ? '使用你在本机设置的账号和密码登录。' : '账号使用 3–48 位字母、数字、下划线或连字符，密码至少 12 个字符。仅首次需要设置。';
  el('confirm-group').hidden = initialized;
  el('confirm-password').required = !initialized;
  el('password').minLength = initialized ? 1 : 12;
  el('password').autocomplete = initialized ? 'current-password' : 'new-password';
  el('submit').textContent = initialized ? '登录' : '创建个人账号';
  el('retry').hidden = true;
  window.dispatchEvent(new CustomEvent('mobile-auth-state', { detail: { authenticated: state.authenticated } }));
}

async function perform(action) {
  if (busy) return;
  busy = true;
  el('notice').textContent = '';
  document.querySelectorAll('#credentials button, #account button, #retry').forEach((button) => { button.disabled = true; });
  try { await action(); }
  catch (error) { el('notice').textContent = error.name === 'AbortError' ? '连接超时，请检查网络后重试' : error instanceof Error ? error.message : '无法连接，请检查本地服务是否运行'; }
  finally {
    busy = false;
    document.querySelectorAll('#credentials button, #account button, #retry').forEach((button) => { button.disabled = false; });
  }
}

async function refresh() {
  try { showState(await api('auth/status')); }
  catch (error) {
    el('credentials').hidden = true;
    el('account').hidden = true;
    el('account-name').textContent = '';
    clearPasswords();
    window.dispatchEvent(new CustomEvent('mobile-auth-state', { detail: { authenticated: false } }));
    el('title').textContent = '暂时无法连接';
    el('intro').textContent = '请确认电脑上的手机模块服务正在运行。';
    el('retry').hidden = false;
    throw error;
  }
}

el('credentials-form').addEventListener('submit', (event) => {
  event.preventDefault();
  void perform(async () => {
    const body = { username: el('username').value.trim(), password: el('password').value };
    if (!initialized && body.password !== el('confirm-password').value) throw new Error('两次密码输入不一致');
    const setup = !initialized;
    try { await api(setup ? 'auth/setup' : 'auth/login', body); }
    finally { clearPasswords(); }
    await refresh();
    if (setup) el('notice').textContent = '账号已创建，请使用刚才设置的密码登录。';
  });
});
el('logout').addEventListener('click', () => { void perform(async () => { await api('auth/logout', {}); await refresh(); }); });
el('password-form').addEventListener('submit', (event) => {
  event.preventDefault();
  void perform(async () => {
    if (el('new-password').value !== el('repeat-password').value) throw new Error('两次新密码输入不一致');
    try {
      await api('auth/password', { current_password: el('current-password').value, new_password: el('new-password').value });
    } finally { clearPasswords(); }
    await refresh();
    el('notice').textContent = '密码已修改，所有会话已退出，请重新登录。';
  });
});
el('retry').addEventListener('click', () => { void perform(refresh); });
document.addEventListener('visibilitychange', () => { if (!document.hidden) void perform(refresh); });
window.addEventListener('pageshow', (event) => { if (event.persisted) void perform(refresh); });
window.YouziMobile = { api };
void perform(refresh);
