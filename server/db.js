const Database = require('better-sqlite3');
const path = require('path');

const dbPath = path.join(__dirname, 'youzi.db');
const db = new Database(dbPath);

// 建表：报价历史（与前端 quoteHistory 一致，整条存 JSON）
db.exec(`
  CREATE TABLE IF NOT EXISTS quote_history (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    data TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_quote_created ON quote_history(created_at DESC);
`);

// 建表：计算历史（与前端 calculationHistory 一致）
db.exec(`
  CREATE TABLE IF NOT EXISTS calculation_history (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL,
    data TEXT NOT NULL,
    summary TEXT,
    details TEXT
  );
  CREATE INDEX IF NOT EXISTS idx_calc_created ON calculation_history(created_at DESC);
`);

const QUOTE_MAX = 100;
const CALC_MAX = 50;

/**
 * 报价历史：获取全部（按时间倒序）
 */
function getQuoteHistory() {
  const rows = db.prepare(
    'SELECT id, created_at, data FROM quote_history ORDER BY created_at DESC'
  ).all();
  return rows.map(r => {
    const item = JSON.parse(r.data);
    item.id = r.id;
    item.timestamp = r.created_at;
    return item;
  });
}

/**
 * 报价历史：新增一条
 */
function addQuote(record) {
  const id = record.id || `quote_${Date.now()}`;
  const created_at = record.timestamp || new Date().toISOString();
  const data = JSON.stringify(record);
  db.prepare('INSERT INTO quote_history (id, created_at, data) VALUES (?, ?, ?)').run(id, created_at, data);
  // 保持最多 QUOTE_MAX 条，删最旧的
  const count = db.prepare('SELECT COUNT(*) as c FROM quote_history').get();
  if (count.c > QUOTE_MAX) {
    const toDelete = db.prepare(
      'SELECT id FROM quote_history ORDER BY created_at ASC LIMIT ?'
    ).all(count.c - QUOTE_MAX);
    const del = db.prepare('DELETE FROM quote_history WHERE id = ?');
    toDelete.forEach(row => del.run(row.id));
  }
  return id;
}

/**
 * 报价历史：按 id 删除
 */
function deleteQuoteById(id) {
  return db.prepare('DELETE FROM quote_history WHERE id = ?').run(id);
}

/**
 * 报价历史：清空
 */
function clearQuoteHistory() {
  return db.prepare('DELETE FROM quote_history').run();
}

/**
 * 计算历史：获取全部（按时间倒序）
 */
function getCalculationHistory() {
  const rows = db.prepare(
    'SELECT id, created_at, data, summary, details FROM calculation_history ORDER BY created_at DESC'
  ).all();
  return rows.map(r => ({
    id: r.id,
    timestamp: r.created_at,
    data: JSON.parse(r.data),
    summary: r.summary,
    details: r.details
  }));
}

/**
 * 计算历史：新增一条
 */
function addCalculation(record) {
  const id = record.id || Date.now();
  const created_at = record.timestamp || new Date().toISOString();
  const data = JSON.stringify(record.data);
  const summary = record.summary || '';
  const details = record.details || '';
  db.prepare(
    'INSERT INTO calculation_history (id, created_at, data, summary, details) VALUES (?, ?, ?, ?, ?)'
  ).run(id, created_at, data, summary, details);
  // 保持最多 CALC_MAX 条
  const count = db.prepare('SELECT COUNT(*) as c FROM calculation_history').get();
  if (count.c > CALC_MAX) {
    const toDelete = db.prepare(
      'SELECT id FROM calculation_history ORDER BY created_at ASC LIMIT ?'
    ).all(count.c - CALC_MAX);
    const del = db.prepare('DELETE FROM calculation_history WHERE id = ?');
    toDelete.forEach(row => del.run(row.id));
  }
  return id;
}

/**
 * 计算历史：按 id 删除
 */
function deleteCalculationById(id) {
  return db.prepare('DELETE FROM calculation_history WHERE id = ?').run(id);
}

/**
 * 计算历史：清空
 */
function clearCalculationHistory() {
  return db.prepare('DELETE FROM calculation_history').run();
}

module.exports = {
  getQuoteHistory,
  addQuote,
  deleteQuoteById,
  clearQuoteHistory,
  getCalculationHistory,
  addCalculation,
  deleteCalculationById,
  clearCalculationHistory
};
