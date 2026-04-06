# 产品导入独立服务（FastAPI）

## 1. 安装依赖

```bash
pip install -r tools/youzi_v2/requirements.txt
```

## 2. 启动服务

```bash
uvicorn tools.youzi_v2.app:app --host 127.0.0.1 --port 3001 --reload
```

## 3. 打开页面

```text
http://127.0.0.1:3001/
```

## 说明

- 后台首页：`/`（框架版后台管理）
- 工具页：`/tools/product-import`（箱单 -> 产品导入模版）
- 报价历史 CRUD API：`/api/quote-history`
- 本服务调用 `tools/product_import/generate_product_import.py` 完成转换。
- 模板默认读取 `tools/product_import/samples/*.xls`。
- 上传和输出临时文件在 `tools/youzi_v2/temp/`。
