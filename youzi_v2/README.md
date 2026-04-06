# 产品导入独立服务（FastAPI）

## 1. 安装依赖

在仓库根目录执行：

```bash
pip install -r youzi_v2/requirements.txt
```

## 2. 启动服务

在仓库根目录执行：

```bash
uvicorn youzi_v2.app:app --host 127.0.0.1 --port 3001 --reload
```

## 3. 打开页面

```text
http://127.0.0.1:3001/
```

## 说明

- 后台首页：`/`（框架版后台管理）
- 工具栏「箱单转换」在后台右侧视图内；`/tools/product-import` 会重定向到 `/`
- 报价历史 CRUD API：`/api/quote-history`
- `index.html` 报价历史：保存走 `POST /api/quote-history/index`，默认请求 `http://127.0.0.1:3001`（可在页面设置 `window.YOUZI_V2_ORIGIN` 覆盖）。需同时启动 youzi_v2 后端。
- 本服务调用 `tools/product_import/generate_product_import.py` 完成转换。
- 模板默认读取 `tools/product_import/samples/*.xls`。
- 上传和输出临时文件在 `youzi_v2/temp/`。
- SQLite 数据在 `youzi_v2/data/`（已加入 `.gitignore`）。
