"""覆盖或追加 DPS 港前和在途运单内部备注。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

from ..db.datetime_util import now_str
from ..db.shipment_order_status import PRE_PORT_STATUSES, TRANSIT_WORKSPACE_STATUSES
from .shipment_query_config import load_config_json, query_shipments_by_order, resolve_dps_authorization, shipment_odd
from .sync_coordination import DpsAuthorizationExpired, serialized_sync

CONFIG_KEYS = ("dps_updateRemark", "dps_update_remark")
DEFAULT_URL = "https://logistics.worlddps.com/prod-api/tenant/order/updateRemark"
DEFAULT_TIMEOUT = 30
REMARK_EDITABLE_STATUSES = PRE_PORT_STATUSES | TRANSIT_WORKSPACE_STATUSES


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


@serialized_sync
def update_shipment_remarks(repo, config_path: Path, ids: list[str], remark: str, mode: str = "replace") -> dict[str, Any]:
    item_ids = list(dict.fromkeys(str(item_id).strip() for item_id in ids if str(item_id).strip()))
    if not item_ids or len(item_ids) > 200:
        raise ValueError("请选择 1 至 200 票运单")
    normalized = _normalize_remark(remark)
    if mode == "append" and not normalized:
        raise ValueError("请输入要追加的备注")
    rows = []
    results: dict[str, dict[str, str]] = {}
    for item_id in item_ids:
        row = repo.get_by_id(item_id)
        if row is None:
            if mode == "append":
                results[item_id] = _result({"id": item_id}, "failed", "运单不存在，请刷新列表")
                continue
            raise ValueError("所选运单不存在，请刷新后重试")
        if row.get("statusCode") not in REMARK_EDITABLE_STATUSES:
            if mode == "append":
                results[item_id] = _result(row, "failed", "当前运单状态无法修改内部备注")
                continue
            raise ValueError("所选包含无法修改内部备注的运单，请刷新后重试")
        if not str(row.get("waybillId") or "").strip():
            if mode == "append":
                results[item_id] = _result(row, "failed", "缺少 DPS 运单 ID，请先更新运单")
                continue
            raise ValueError(f"{row.get('shipmentNo') or '所选运单'} 缺少 DPS ID，请先更新运单")
        if mode == "append" and not row.get("shipmentNo"):
            results[item_id] = _result(row, "failed", "缺少运单号，无法读取最新备注")
            continue
        rows.append(row)

    settings = _settings(config_path)
    if not settings["authorization"]:
        raise ValueError("缺少 DPS 鉴权配置")
    if settings["method"] not in {"PUT", "POST"}:
        raise ValueError("dps_updateRemark.method 仅支持 PUT 或 POST")
    if mode == "append":
        results.update(_append_remarks(repo, config_path, settings, rows, normalized))
        items = [results[item_id] for item_id in item_ids]
        return {
            "total": len(items),
            "updated": sum(item["status"] == "success" for item in items),
            "failed": sum(item["status"] == "failed" for item in items),
            "unknown": sum(item["status"] == "unknown" for item in items),
            "remarkResults": items,
        }

    try:
        response = _write_dps(settings, rows, normalized)
    except requests.RequestException:
        raise ValueError("DPS 请求异常，结果可能已生效，请核对后再操作") from None
    if response.status_code != 200:
        raise ValueError(f"DPS 内部备注更新失败 HTTP {response.status_code}")
    _write_local(repo, rows, normalized)
    return {"total": len(rows), "updated": len(rows), "failed": 0}


def _write_dps(settings, rows, remark):
    body = {
        "remark": remark,
        "commerceWaybillIds": list(dict.fromkeys(str(row["waybillId"]).strip() for row in rows)),
    }
    return requests.request(
        settings["method"], settings["url"], json=body,
        headers={"Authorization": settings["authorization"], "Content-Type": "application/json"},
        timeout=settings["timeout"], allow_redirects=False,
    )


def _write_local(repo, rows, remark):
    database = repo._database
    with database.lock:
        try:
            database.conn.executemany(
                "UPDATE shipments SET remark=?, updated_time=? WHERE id=?",
                [(remark, now_str(), row["id"]) for row in rows],
            )
            database.conn.commit()
        except Exception:
            database.conn.rollback()
            raise ValueError("远端已成功，本地备注更新失败，请刷新运单核对") from None


def _result(row, status, message):
    return {"id": row["id"], "shipmentNo": row.get("shipmentNo") or "—", "status": status, "message": message}


def _read_dps_remarks(rows, config_path):
    """匹配运单号和远端 ID。缺少备注字段时不能假定为空。"""
    remarks = {}
    for start in range(0, len(rows), 50):
        chunk = rows[start:start + 50]
        parsed, error = query_shipments_by_order([row["shipmentNo"] for row in chunk], config_path)
        if error or not parsed:
            continue
        for remote in parsed.get("rows", []):
            if not isinstance(remote, dict) or "remark" not in remote:
                continue
            value = remote["remark"]
            if value is None or isinstance(value, str):
                key = (shipment_odd(remote), str(remote.get("id") or "").strip())
                remarks[key] = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    return remarks


def _remote_key(row):
    return row["shipmentNo"], str(row["waybillId"]).strip()


def _append_remarks(repo, config_path, settings, rows, addition):
    try:
        latest = _read_dps_remarks(rows, config_path)
    except DpsAuthorizationExpired:
        raise ValueError("DPS 授权已失效，请更新授权后重试") from None
    except FileNotFoundError:
        raise ValueError("缺少 DPS 查询配置，未提交追加") from None
    groups: dict[str, list] = {}
    results = {}
    for row in rows:
        previous = latest.get(_remote_key(row))
        if previous is None:
            results[row["id"]] = _result(row, "failed", "未能读取 DPS 最新备注，未提交")
            continue
        separator = "" if previous.endswith("\n") else "\n"
        combined = previous + separator + addition if previous.strip() else addition
        if len(combined) > 5000:
            results[row["id"]] = _result(row, "failed", "追加后超过 5000 字符，未提交")
            continue
        groups.setdefault(combined, []).append(row)

    uncertain = []
    for combined, group in groups.items():
        try:
            response = _write_dps(settings, group, combined)
        except requests.RequestException:
            uncertain.extend((row, combined) for row in group)
            continue
        if response.status_code == 200:
            _record_append_success(repo, results, group, combined)
        elif 200 <= response.status_code < 300 or response.status_code in {408, 409} or response.status_code >= 500:
            uncertain.extend((row, combined) for row in group)
        else:
            for row in group:
                results[row["id"]] = _result(row, "failed", f"DPS 备注更新失败 HTTP {response.status_code}")

    if uncertain:
        try:
            readback = _read_dps_remarks([row for row, _ in uncertain], config_path)
        except (DpsAuthorizationExpired, ValueError, OSError, requests.RequestException):
            readback = {}
        for row, expected in uncertain:
            if readback.get(_remote_key(row)) == expected:
                _record_append_success(repo, results, [row], expected)
            else:
                results[row["id"]] = _result(row, "unknown", "回读未能确认是否已追加，请到 DPS 核对")
    return results


def _record_append_success(repo, results, rows, remark):
    message = "已追加"
    try:
        _write_local(repo, rows, remark)
    except ValueError as exc:
        message = str(exc)
    for row in rows:
        results[row["id"]] = _result(row, "success", message)
