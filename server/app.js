const express = require('express');
const cors = require('cors');
const path = require('path');
let getQuoteHistory;
let addQuote;
let deleteQuoteById;
let clearQuoteHistory;
let getCalculationHistory;
let addCalculation;
let deleteCalculationById;
let clearCalculationHistory;

try {
  ({
    getQuoteHistory,
    addQuote,
    deleteQuoteById,
    clearQuoteHistory,
    getCalculationHistory,
    addCalculation,
    deleteCalculationById,
    clearCalculationHistory
  } = require('./db'));
} catch (err) {
  console.warn('SQLite 初始化失败，历史记录将使用内存模式:', err.message);
  const quoteHistory = [];
  const calculationHistory = [];

  getQuoteHistory = () => quoteHistory;
  addQuote = (record) => {
    const item = {
      ...record,
      id: record?.id || `quote_${Date.now()}`,
      timestamp: record?.timestamp || new Date().toISOString()
    };
    quoteHistory.unshift(item);
    if (quoteHistory.length > 100) quoteHistory.length = 100;
    return item.id;
  };
  deleteQuoteById = (id) => {
    const index = quoteHistory.findIndex((x) => String(x.id) === String(id));
    if (index >= 0) quoteHistory.splice(index, 1);
    return { changes: index >= 0 ? 1 : 0 };
  };
  clearQuoteHistory = () => {
    quoteHistory.length = 0;
    return { changes: 1 };
  };

  getCalculationHistory = () => calculationHistory;
  addCalculation = (record) => {
    const item = {
      id: record?.id || Date.now(),
      timestamp: record?.timestamp || new Date().toISOString(),
      data: record?.data || {},
      summary: record?.summary || '',
      details: record?.details || ''
    };
    calculationHistory.unshift(item);
    if (calculationHistory.length > 50) calculationHistory.length = 50;
    return item.id;
  };
  deleteCalculationById = (id) => {
    const index = calculationHistory.findIndex((x) => String(x.id) === String(id));
    if (index >= 0) calculationHistory.splice(index, 1);
    return { changes: index >= 0 ? 1 : 0 };
  };
  clearCalculationHistory = () => {
    calculationHistory.length = 0;
    return { changes: 1 };
  };
}

const app = express();
const PORT = process.env.PORT || 3000;
const ROOT = path.join(__dirname, '..');

app.use(cors());
app.use(express.json({ limit: '1mb' }));

// 静态资源：项目根目录（index.html、js/、css/ 等）
app.use(express.static(ROOT));

// ---------- 报价历史 API ----------
app.get('/api/quote-history', (req, res) => {
  try {
    const list = getQuoteHistory();
    res.json(list);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

app.post('/api/quote-history', (req, res) => {
  try {
    const record = req.body;
    if (!record || typeof record !== 'object') {
      return res.status(400).json({ error: '需要 JSON 对象' });
    }
    const id = addQuote(record);
    res.status(201).json({ id });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

app.delete('/api/quote-history/:id', (req, res) => {
  try {
    const { id } = req.params;
    const result = deleteQuoteById(id);
    res.json({ deleted: result.changes > 0 });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

app.delete('/api/quote-history', (req, res) => {
  try {
    clearQuoteHistory();
    res.json({ ok: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

// ---------- 计算历史 API ----------
app.get('/api/calculation-history', (req, res) => {
  try {
    const list = getCalculationHistory();
    res.json(list);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

app.post('/api/calculation-history', (req, res) => {
  try {
    const record = req.body;
    if (!record || typeof record !== 'object') {
      return res.status(400).json({ error: '需要 JSON 对象' });
    }
    const id = addCalculation(record);
    res.status(201).json({ id });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

app.delete('/api/calculation-history/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (Number.isNaN(id)) return res.status(400).json({ error: '无效 id' });
    const result = deleteCalculationById(id);
    res.json({ deleted: result.changes > 0 });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

app.delete('/api/calculation-history', (req, res) => {
  try {
    clearCalculationHistory();
    res.json({ ok: true });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: String(e.message) });
  }
});

// 未匹配的 API 返回 404
app.get('/api/*', (req, res) => {
  res.status(404).json({ error: 'Not Found' });
});

// 其余 GET 回退到 index（单页应用；静态文件已在 express.static 中处理）
app.get('*', (req, res) => {
  res.sendFile(path.join(ROOT, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`youzi server: http://localhost:${PORT}`);
  console.log('产品导入工具页已迁移到 FastAPI: http://127.0.0.1:3001/');
});
