"""DPS 运单同步：可配置的 insert/update 字段白名单。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "shipment_dps_sync_fields.json"

# 映射逻辑在 shipment_dps_mapper.py；此处仅列可配置的业务字段（不含 shipment_no）
KNOWN_SYNC_FIELDS = frozenset(
    {
        "customer",
        "customer_no",
        "channel_code",
        "country_code",
        "address_type",
        "address_code",
        "zipcode",
        "ctns",
        "product_name",
        "origin_warehouse_code",
        "supplier_name",
        "carrier_code",
        "carrier_id",
        "waybill_id",
        "tracking_number",
        "customer_shipment_id",
        "amazon_ref_id",
        "bill_of_lading_no",
        "container_no",
        "expected_delivery_time",
        "delivered_time",
        "status_code",
        "payment_status",
        "latest_tracking_time",
        "latest_tracking_desc",
    }
)


@dataclass(frozen=True)
class DpsSyncFieldRule:
    shipment_field: str
    label: str
    dps_source: str
    on_insert: bool
    on_update: bool


@dataclass(frozen=True)
class DpsSyncFieldsConfig:
    insert_fields: frozenset[str]
    update_fields: frozenset[str]
    rules: tuple[DpsSyncFieldRule, ...]

    def to_api_list(self) -> list[dict[str, Any]]:
        return [
            {
                "shipmentField": r.shipment_field,
                "label": r.label,
                "dpsSource": r.dps_source,
                "onInsert": r.on_insert,
                "onUpdate": r.on_update,
            }
            for r in self.rules
        ]


def _parse_field_rule(name: str, block: dict[str, Any]) -> DpsSyncFieldRule:
    return DpsSyncFieldRule(
        shipment_field=name,
        label=str(block.get("label") or name),
        dps_source=str(block.get("dpsSource") or ""),
        on_insert=bool(block.get("onInsert", True)),
        on_update=bool(block.get("onUpdate", True)),
    )


def load_dps_sync_fields_config(path: Path | None = None) -> DpsSyncFieldsConfig:
    cfg_path = path or _CONFIG_PATH
    if not cfg_path.is_file():
        return _default_config()
    with cfg_path.open("r", encoding="utf-8") as f:
        raw: dict[str, Any] = json.load(f)
    fields_raw = raw.get("fields")
    if not isinstance(fields_raw, dict):
        return _default_config()

    rules: list[DpsSyncFieldRule] = []
    for name, block in fields_raw.items():
        if name.startswith("_") or not isinstance(block, dict):
            continue
        if name not in KNOWN_SYNC_FIELDS:
            continue
        rules.append(_parse_field_rule(name, block))

    if not rules:
        return _default_config()

    insert = frozenset(r.shipment_field for r in rules if r.on_insert)
    update = frozenset(r.shipment_field for r in rules if r.on_update)
    return DpsSyncFieldsConfig(
        insert_fields=insert,
        update_fields=update,
        rules=tuple(rules),
    )


def _default_config() -> DpsSyncFieldsConfig:
    rules = tuple(
        DpsSyncFieldRule(
            shipment_field=name,
            label=name,
            dps_source="",
            on_insert=True,
            on_update=True,
        )
        for name in sorted(KNOWN_SYNC_FIELDS)
    )
    all_fields = frozenset(KNOWN_SYNC_FIELDS)
    return DpsSyncFieldsConfig(
        insert_fields=all_fields,
        update_fields=all_fields,
        rules=rules,
    )


@lru_cache(maxsize=1)
def get_dps_sync_fields_config() -> DpsSyncFieldsConfig:
    return load_dps_sync_fields_config()


def filter_dps_payload(
    payload: dict[str, Any],
    *,
    is_new: bool,
    config: DpsSyncFieldsConfig | None = None,
) -> dict[str, Any]:
    """按 onInsert / onUpdate 过滤映射结果。"""
    cfg = config or get_dps_sync_fields_config()
    allowed = cfg.insert_fields if is_new else cfg.update_fields
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "shipment_no":
            out[key] = value
            continue
        if key in allowed:
            out[key] = value
    return out


def config_file_path() -> Path:
    return _CONFIG_PATH
