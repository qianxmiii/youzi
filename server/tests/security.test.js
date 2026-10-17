const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const vm = require('node:vm');
const express = require('express');
const mountPublicAssets = require('../public-assets');

test('static resources exclude private files and traversal paths', async (t) => {
  const temp = path.join(__dirname, '../../temp');
  fs.mkdirSync(temp, { recursive: true });
  const root = fs.mkdtempSync(path.join(temp, 'public-assets-test-'));
  const files = {
    'js/app.js': '/* public */',
    'css/app.css': '/* public */',
    'config/style.js': '/* public */',
    'data/data.js': '/* public */',
    'config/config.json': '{}',
    'data/private_data.js': '/* synthetic private fixture */',
    'youzi_v2/data/youzi_v2.db': 'synthetic',
    'logs/test.log': 'synthetic',
    '.git/config': 'synthetic',
  };
  for (const [name, content] of Object.entries(files)) {
    const filename = path.join(root, name);
    fs.mkdirSync(path.dirname(filename), { recursive: true });
    fs.writeFileSync(filename, content);
  }
  const app = express();
  mountPublicAssets(app, root);
  app.use((req, res) => res.sendStatus(404));
  const server = http.createServer(app);
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  t.after(() => new Promise((resolve) => server.close(resolve)));
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const url of ['/js/app.js', '/css/app.css', '/config/style.js', '/data/data.js']) {
    assert.equal((await fetch(base + url)).status, 200, url);
  }
  for (const url of [
    '/config/config.json', '/data/private_data.js', '/youzi_v2/data/youzi_v2.db',
    '/logs/test.log', '/.git/config', '/js/%2e%2e/config/config.json',
    '/js/..%2fconfig%2fconfig.json', '/js/..%5cconfig%5cconfig.json',
  ]) {
    assert.equal((await fetch(base + url)).status, 404, url);
  }
});

test('quote history renders stored HTML as text and binds IDs without inline scripts', () => {
  const source = fs.readFileSync(path.join(__dirname, '../../js/logistics.js'), 'utf8');
  const start = source.indexOf('function escapeQuoteHistoryText(');
  const end = source.indexOf('\n/**', source.indexOf('function renderQuoteHistoryTable(', start));
  const rows = [];
  const clicks = [];
  const tbody = { innerHTML: '', appendChild: (row) => rows.push(row) };
  const context = {
    document: {
      getElementById: () => tbody,
      createElement: () => {
        const handlers = {};
        return {
          innerHTML: '', handlers,
          querySelector: (selector) => ({ addEventListener: (event, fn) => { handlers[selector] = fn; } }),
        };
      },
    },
    normalizeQuoteHistoryTimestamp: (value) => value,
    updateQuoteHistoryPagination: () => {},
    loadQuoteToForm: (id) => clicks.push(['load', id]),
    deleteQuoteHistory: (id) => clicks.push(['delete', id]),
  };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  const payload = '<img src=x onerror="globalThis.injected=1">';
  const id = "');globalThis.injected=1;//";
  const record = { id };
  for (const field of ['timestamp', 'address', 'country', 'quantity', 'weight', 'volume', 'priceUsd', 'totalPriceUsd']) {
    record[field] = payload;
  }
  context.renderQuoteHistoryTable([record]);
  assert.equal(rows.length, 1);
  assert.ok(rows[0].innerHTML.includes('&lt;img'));
  assert.ok(!rows[0].innerHTML.includes('<img'));
  assert.ok(!rows[0].innerHTML.includes('onclick='));
  assert.ok(!rows[0].innerHTML.includes(id));
  rows[0].handlers['[data-quote-action="load"]']();
  rows[0].handlers['[data-quote-action="delete"]']();
  assert.deepEqual(clicks, [['load', id], ['delete', id]]);
  assert.equal(context.injected, undefined);
});
