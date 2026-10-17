"""DPS 收货仓（receiveWarehouseName → config.dps_warehouse 地址文案）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .shipment_query_config import load_config_json

RECEIVE_WAREHOUSE_KEY_SHENZHEN = "SHENZHEN"
RECEIVE_WAREHOUSE_KEY_YIWU = "YIWU"

RECEIVE_WAREHOUSE_LABEL_ZH: dict[str, str] = {
    RECEIVE_WAREHOUSE_KEY_SHENZHEN: "深圳仓",
    RECEIVE_WAREHOUSE_KEY_YIWU: "义乌仓",
}

# (config key, 匹配收货仓名称子串)
_RECEIVE_WAREHOUSE_MATCH_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (RECEIVE_WAREHOUSE_KEY_SHENZHEN, ("深圳仓", "深圳")),
    (RECEIVE_WAREHOUSE_KEY_YIWU, ("义乌仓", "义乌")),
)


def resolve_receive_warehouse_key(origin_warehouse_name: str | None) -> str | None:
    """将运单收货仓名称映射为 config.dps_warehouse 的键（SHENZHEN / YIWU）。"""
    text = (origin_warehouse_name or "").strip()
    if not text:
        return None
    upper = text.upper().replace(" ", "")
    if upper in (RECEIVE_WAREHOUSE_KEY_SHENZHEN, RECEIVE_WAREHOUSE_KEY_YIWU):
        return upper
    for key, hints in _RECEIVE_WAREHOUSE_MATCH_RULES:
        for hint in hints:
            if hint in text:
                return key
    return None


def receive_warehouse_label_zh(warehouse_key: str | None) -> str:
    key = (warehouse_key or "").strip().upper()
    return RECEIVE_WAREHOUSE_LABEL_ZH.get(key, key or "—")


def load_dps_warehouse_addresses(config_path: Path) -> dict[str, str]:
    """读取 config.json → dps_warehouse（键 SHENZHEN/YIWU，值为收货地址多行文本）。"""
    config = load_config_json(config_path)
    raw = config.get("dps_warehouse")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        key = str(k).strip().upper()
        if not key:
            continue
        if isinstance(v, str) and v.strip():
            out[key] = v.strip()
    return out


def require_receive_warehouse_address(
    config_path: Path,
    warehouse_key: str,
) -> str:
    key = warehouse_key.strip().upper()
    addresses = load_dps_warehouse_addresses(config_path)
    text = addresses.get(key, "").strip()
    if not text:
        label = receive_warehouse_label_zh(key)
        raise ValueError(
            f"config.json 的 dps_warehouse.{key} 未配置收货地址（{label}）"
        )
    return text


def format_receive_address_block(warehouse_key: str, address_text: str) -> str:
    label = receive_warehouse_label_zh(warehouse_key)
    body = (address_text or "").strip()
    return f"收货仓：{label}\n收货地址：\n{body}"


def collect_shipments_receive_warehouse(
    rows: list[dict[str, Any]],
) -> tuple[str, str]:
    """
    从运单 API 行中解析唯一收货仓键。
    返回 (warehouse_key, 示例 originWarehouseCode 原文)。
    """
    keys: set[str] = set()
    samples: dict[str, str] = {}
    missing: list[str] = []

    for row in rows:
        shipment_no = str(row.get("shipmentNo") or row.get("id") or "").strip() or "运单"
        origin = str(row.get("originWarehouseCode") or "").strip()
        key = resolve_receive_warehouse_key(origin)
        if not key:
            missing.append(f"{shipment_no}（收货仓：{origin or '空'}）")
            continue
        keys.add(key)
        samples.setdefault(key, origin)

    if missing:
        hint = "；".join(missing[:5])
        if len(missing) > 5:
            hint += f" 等 {len(missing)} 票"
        raise ValueError(
            f"无法识别收货仓，请确认 DPS 已同步 receiveWarehouseName（深圳仓/义乌仓）。{hint}"
        )

    if not keys:
        raise ValueError("所选运单均无收货仓信息")

    if len(keys) > 1:
        parts = [
            f"{receive_warehouse_label_zh(k)}（{samples.get(k, k)}）" for k in sorted(keys)
        ]
        raise ValueError(f"所选运单收货仓不一致，请分开下载：{'、'.join(parts)}")

    key = next(iter(keys))
    return key, samples.get(key, receive_warehouse_label_zh(key))
