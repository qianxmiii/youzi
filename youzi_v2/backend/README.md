# 后端入口（backend）

## 模块名称

Youzi v2 后端 — FastAPI / ASGI

## 功能说明

当前主 API 入口为 **`youzi_v2/app.py`**（单文件路由 + Legacy Jinja 页面）。`backend/app/` 为可选 ASGI 封装，供未来拆分模块使用。

## 主要文件

| 路径 | 作用 |
|------|------|
| `../app.py` | FastAPI 应用、全部 REST 路由、Legacy 页面 |
| `app/__init__.py` | 可选 ASGI 模块 |
| `../schemas/` | Pydantic 请求/响应模型 |
| `../services/` | 业务逻辑 |
| `../db/` | 数据访问 |
| `../internal_tracking.py` | 内部轨迹解析 |
| `../tracking_sync_eligibility.py` | 同步 eligibility 规则 |

## 启动方式

```bash
# 仓库根目录
pip install -r youzi_v2/requirements.txt
uvicorn youzi_v2.app:app --host 0.0.0.0 --port 3001 --reload
```

## API 组织

- 新接口：`/api/v1/*`
- Legacy：`/api/health`、`/api/addresses*`、`/api/quote-history*` 等
- 页面：`/`、`/tools/product-import`（Jinja 模板）

完整列表见 [docs/api.md](../docs/api.md)。

## 注意事项

- 新增路由：在 `app.py` 添加端点 + `schemas/` 定义模型 + 更新 API 文档
- 承运商密钥只读根目录 `config/config.json`
- 后台任务在 `app.py` lifespan 中启动 `tracking_sync_scheduler`

## 相关文档

- [docs/architecture.md](../docs/architecture.md)
- [docs/deployment.md](../docs/deployment.md)
- [services/README.md](../services/README.md)
