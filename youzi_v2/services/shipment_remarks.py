"""覆盖 DPS 港前运单内部备注，远端成功后再回写本地。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from ..db.datetime_util import now_str
from ..db.shipment_order_status import PRE_PORT_STATUSES
from .shipment_query_config import load_config_json, resolve_dps_authorization

CONFIG_KEYS = ("dps_updateRemark", "dps_update_remark")
DEFAULT_URL = "https://logistics.worlddps.com/prod-api/tenant/order/updateRemark"
DEFAULT_TIMEOUT = 30


def _settings(config_path: Path) -> dict[str, Any]:
    config = load_config_json(config_path)
    block: dict[str, Any] = {}
    for key in CONFIG_KEYS:
        candidate = config.get(key)
        if isinstance(candidate, dict):
            block = candidate
            break
    try:
        timeout = int(block.get("timeout") or DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    return {
        "url": str(block.get("url") or DEFAULT_URL).strip(),
        "method": str(block.get("method") or "PUT").strip().upper(),
        "authorization": resolve_dps_authorization(config, block),
        "timeout": timeout,
    }


def _normalize_remark(value: str) -> str:
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) > 5000:
        raise ValueError("内部备注最多 5000 个字符")
    return text


def update_shipment_remarks(repo, config_path: Path, ids: list[str], remark: str) -> dict[str, int]:
    item_ids = list(dict.fromkeys(str(item_id).strip() for item_id in ids if str(item_id).strip()))
    if not item_ids or len(item_ids) > 200:
        raise ValueError("请选择 1 至 200 票运单")
    normalized = _normalize_remark(remark)
    rows = []
    for item_id in item_ids:
        row = repo.get_by_id(item_id)
        if row is None:
            raise ValueError("所选运单不存在，请刷新后重试")
        if row.get("statusCode") not in PRE_PORT_STATUSES:
            raise ValueError("所选包含非港前运单，请刷新后重试")
        if not str(row.get("waybillId") or "").strip():
            raise ValueError(f"{row.get('shipmentNo') or '所选运单'} 缺少 DPS ID，请先更新运单")
        rows.append(row)

    settings = _settings(config_path)
    if not settings["authorization"]:
        raise ValueError("缺少 DPS 鉴权配置")
    if settings["method"] not in {"PUT", "POST"}:
        raise ValueError("dps_updateRemark.method 仅支持 PUT 或 POST")
    body = {
        "remark": normalized,
        "commerceWaybillIds": list(dict.fromkeys(str(row["waybillId"]).strip() for row in rows)),
    }
    try:
        response = requests.request(
            settings["method"],
            settings["url"],
            json=body,
            headers={"Authorization": settings["authorization"], "Content-Type": "application/json"},
            timeout=settings["timeout"],
            allow_redirects=False,
        )
    except requests.RequestException:
        raise ValueError("DPS 请求异常，结果可能已生效，请核对后再操作") from None
    if response.status_code != 200:
        raise ValueError(f"DPS 内部备注更新失败 HTTP {response.status_code}")

    database = repo._database
    with database.lock:
        try:
            database.conn.executemany(
                "UPDATE shipments SET remark=?, updated_time=? WHERE id=?",
                [(normalized, now_str(), row["id"]) for row in rows],
            )
            database.conn.commit()
        except Exception:
            database.conn.rollback()
            raise ValueError("远端已成功，本地备注更新失败，请刷新运单核对") from None
    return {"total": len(rows), "updated": len(rows), "failed": 0}
