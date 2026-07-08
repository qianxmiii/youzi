"""
物流轨迹查询：与仓库根目录 check_stale_shipments.query_logistics_api 相同协议。
POST {"odds": [...]} 到 config/config.json 的 base_url，解析 logisticsInfors。
每批固定 10 个运单号查询。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import requests

from ..internal_tracking import is_internal_no_tracking_desc
from .sync_log_format import format_api_payload_for_log

BATCH_SIZE = 10
DEFAULT_TIMEOUT = 30

LogFn = Callable[[str], None]


def _default_log(msg: str) -> None:
    print(msg, flush=True)


def load_logistics_config(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        raise FileNotFoundError(f"未找到物流 API 配置：{config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    base_url = (config.get("base_url") or "").strip()
    if not base_url:
        raise ValueError("config.json 缺少 base_url")
    return config


def query_logistics_batch(
    batch: list[dict[str, str]],
    base_url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[list[dict[str, Any]], str | None]:
    """查询单批（最多 BATCH_SIZE 条）。返回 (结果列表, 错误信息或 None)。"""
    odds = [item["tracking_number"] for item in batch]
    payload = json.dumps({"odds": odds}, ensure_ascii=False)
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(base_url, data=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            data = result.get("data", [])
            for d in data:
                match = next(
                    (x for x in batch if x["tracking_number"] == d.get("odd")),
                    None,
                )
                d["customer"] = match.get("customer", "") if match else ""
                d["channel"] = match.get("channel", "") if match else ""
                d["carrier"] = match.get("carrier", "") if match else ""
            return data, None
        return [], result.get("msg") or f"查询失败 code={result.get('code')}"
    except Exception as e:
        return [], str(e)


def query_logistics_api(
    tracking_list: list[dict[str, str]],
    base_url: str,
    *,
    batch_size: int = BATCH_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
    log: LogFn | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    按批查询轨迹（默认每批 10 单），控制台输出批次进度。
    返回 (API 成功条目列表, 错误信息列表)。
    """
    out_log = log or _default_log
    batch_size = max(1, batch_size)
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    total = len(tracking_list)
    total_batches = (total + batch_size - 1) // batch_size if total else 0

    out_log(f"[轨迹同步] 共 {total} 单，每批 {batch_size} 单，共 {total_batches} 批")

    for batch_index, i in enumerate(range(0, total, batch_size), start=1):
        batch = tracking_list[i : i + batch_size]
        from_no = i + 1
        to_no = min(i + batch_size, total)
        sample = batch[0]["tracking_number"]
        if len(batch) > 1:
            sample = f"{sample} … {batch[-1]['tracking_number']}"
        out_log(
            f"[轨迹同步] 第 {batch_index}/{total_batches} 批 "
            f"({from_no}-{to_no}/{total})，本批 {len(batch)} 单: {sample}"
        )

        data, err = query_logistics_batch(batch, base_url, timeout=timeout)
        if err:
            out_log(f"[轨迹同步] 第 {batch_index}/{total_batches} 批失败: {err}")
            errors.append(err)
        else:
            all_results.extend(data)
            out_log(
                f"[轨迹同步] 第 {batch_index}/{total_batches} 批完成，"
                f"本批返回 {len(data)} 条"
            )
            for item in data:
                sn = (item.get("odd") or "").strip()
                if sn:
                    out_log(
                        f"[轨迹同步] {sn} 返回报文 {format_api_payload_for_log(item)}"
                    )

    out_log(f"[轨迹同步] API 查询结束，累计返回 {len(all_results)} 条")
    return all_results, errors


def latest_from_logs(logs: list[tuple[str, str]]) -> tuple[str, str]:
    """API 返回的 logisticsInfors 通常最新一条在首位；跳过仓库占位节点。"""
    for t, d in logs:
        if not is_internal_no_tracking_desc(d):
            return t, d
    return "", ""


def logs_from_api_item(item: dict[str, Any]) -> list[tuple[str, str]]:
    """将 API 单条结果的 logisticsInfors 转为 (tracking_time, tracking_desc)。

    含入仓占位节点（Your goods are in the warehouse），供轨迹列表展示与入仓时间回写；
    运单摘要最新轨迹仍由 latest_from_logs 跳过占位文案。
    """
    from ..db.datetime_util import normalize_tracking_time

    out: list[tuple[str, str]] = []
    for log in item.get("logisticsInfors") or []:
        node_time = normalize_tracking_time(log.get("nodeTime") or "")
        node_desc = (log.get("nodeDesc") or "").strip()
        if node_time and node_desc:
            out.append((node_time, node_desc))
    return out


def shipment_no_from_api_item(item: dict[str, Any]) -> str:
    return (item.get("odd") or item.get("tracking_number") or "").strip()


# 内部物流 API data[].status：2=转运中，3=已签收
_INTERNAL_API_STATUS: dict[str, str] = {
    "2": "IN_TRANSIT",
    "3": "DELIVERED",
}


def status_code_from_api_item(item: dict[str, Any]) -> str | None:
    """将报文 status 转为运单 status_code；未知值返回 None（不覆盖库内状态）。"""
    raw = item.get("status")
    if raw is None:
        return None
    key = str(raw).strip()
    return _INTERNAL_API_STATUS.get(key)


def status_label_from_api_item(item: dict[str, Any]) -> str:
    code = status_code_from_api_item(item)
    if code == "IN_TRANSIT":
        return "转运中"
    if code == "DELIVERED":
        return "已签收"
    raw = item.get("status")
    return f"status={raw}" if raw is not None else ""
