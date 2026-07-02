"""运单列表筛选：时间口径、缺失字段、签收/到港等业务条件。"""

from __future__ import annotations

from typing import Any

from .shipment_tracking_numbers_table import TABLE_NAME as TRACKING_NUMBERS_TABLE

TIME_FIELD_MAP: dict[str, str] = {    "createdTime": "created_time",
    "etd": "etd",
    "atd": "atd",
    "eta": "eta",
    "ata": "ata",
    "expectedDeliveryTime": "expected_delivery_time",
    "deliveredTime": "delivered_time",
    "updatedTime": "updated_time",
}

MISSING_FIELD_MAP: dict[str, str] = {
    "etd": "etd",
    "atd": "atd",
    "eta": "eta",
    "ata": "ata",
    "expectedDeliveryTime": "expected_delivery_time",
    "deliveredTime": "delivered_time",
}

DELIVERY_RISK_WARNING_SOON = "warning_soon"
DELIVERY_RISK_OVERDUE = "overdue"
DELIVERY_RISK_SEVERE = "severe_overdue"
VALID_DELIVERY_RISKS = frozenset(
    {DELIVERY_RISK_WARNING_SOON, DELIVERY_RISK_OVERDUE, DELIVERY_RISK_SEVERE}
)

WARNING_SOON_DAYS = 3
SEVERE_OVERDUE_DAYS = 7

# 关键词模糊匹配：运单号、柜号/提单号（tracking/carrier_id）、货件号、客户编号、供应商等
_KEYWORD_SHIPMENT_COLUMNS = (
    "shipment_no",
    "customer_no",
    "customer_shipment_id",
    "supplier_name",
    "carrier_id",
    "tracking_number",
    "amazon_ref_id",
    "vessel_voyage",
    "vessel_name",
    "voyage_no",
    "customer",
    "channel_code",
    "carrier_code",
    "address_code",
    "delivery_address",
)


def validate_time_field(field: str | None) -> str | None:
    key = (field or "").strip()
    if not key:
        return None
    col = TIME_FIELD_MAP.get(key)
    if not col:
        raise ValueError(f"不支持的时间口径: {field}")
    return col


def append_keyword_search(
    conditions: list[str],
    params: list[Any],
    keyword: str,
) -> None:
    q = f"%{keyword.strip()}%"
    parts = [f"s.{col} LIKE ?" for col in _KEYWORD_SHIPMENT_COLUMNS]
    parts.extend(
        [
            "cc.name_zh LIKE ?",
            "crc.name_zh LIKE ?",
            "crc_by_id.name_zh LIKE ?",
            f"""EXISTS (
                SELECT 1 FROM {TRACKING_NUMBERS_TABLE} stn
                WHERE stn.shipment_no = s.shipment_no
                  AND (
                    stn.tracking_number LIKE ?
                    OR stn.main_tracking_number LIKE ?
                  )
            )""",
        ]
    )
    conditions.append(f"({' OR '.join(parts)})")
    params.extend([q] * len(_KEYWORD_SHIPMENT_COLUMNS))
    params.extend([q, q, q, q, q])


def append_time_range(
    conditions: list[str],
    params: list[Any],
    *,
    column: str,
    time_from: str | None = None,
    time_to: str | None = None,
) -> None:
    col = validate_time_field(column)
    if not col:
        return
    start = (time_from or "").strip()[:10]
    end = (time_to or "").strip()[:10]
    if start:
        conditions.append(
            f"s.{col} IS NOT NULL AND TRIM(s.{col}) != '' "
            f"AND date(substr(s.{col}, 1, 10)) >= date(?)"
        )
        params.append(start)
    if end:
        conditions.append(
            f"s.{col} IS NOT NULL AND TRIM(s.{col}) != '' "
            f"AND date(substr(s.{col}, 1, 10)) <= date(?)"
        )
        params.append(end)


def append_missing_field(
    conditions: list[str],
    *,
    field: str,
    missing: bool = True,
) -> None:
    key = (field or "").strip()
    col = MISSING_FIELD_MAP.get(key)
    if not col:
        raise ValueError(f"不支持的缺失字段: {field}")
    if missing:
        conditions.append(f"(s.{col} IS NULL OR TRIM(s.{col}) = '')")
    else:
        conditions.append(f"s.{col} IS NOT NULL AND TRIM(s.{col}) != ''")


def append_not_delivered(conditions: list[str]) -> None:
    conditions.append(
        "(s.delivered_time IS NULL OR TRIM(s.delivered_time) = '') "
        "AND (s.status_code IS NULL OR UPPER(TRIM(s.status_code)) != 'DELIVERED')"
    )


def append_has_ata(conditions: list[str]) -> None:
    conditions.append("s.ata IS NOT NULL AND TRIM(s.ata) != ''")


def append_delivery_risk(
    conditions: list[str],
    params: list[Any],
    risk: str | None,
) -> None:
    key = (risk or "").strip()
    if not key:
        return
    if key not in VALID_DELIVERY_RISKS:
        raise ValueError(f"不支持的送仓风险: {risk}")
    base = (
        "(s.delivered_time IS NULL OR TRIM(s.delivered_time) = '') "
        "AND s.expected_delivery_time IS NOT NULL AND TRIM(s.expected_delivery_time) != ''"
    )
    if key == DELIVERY_RISK_WARNING_SOON:
        conditions.append(
            f"{base} AND date(substr(s.expected_delivery_time, 1, 10)) >= date('now') "
            f"AND date(substr(s.expected_delivery_time, 1, 10)) <= date('now', ?)"
        )
        params.append(f"+{WARNING_SOON_DAYS} days")
    elif key == DELIVERY_RISK_OVERDUE:
        conditions.append(
            f"{base} AND date(substr(s.expected_delivery_time, 1, 10)) < date('now') "
            f"AND date(substr(s.expected_delivery_time, 1, 10)) >= "
            f"date('now', ?)"
        )
        params.append(f"-{SEVERE_OVERDUE_DAYS} days")
    elif key == DELIVERY_RISK_SEVERE:
        conditions.append(
            f"{base} AND date(substr(s.expected_delivery_time, 1, 10)) < "
            f"date('now', ?)"
        )
        params.append(f"-{SEVERE_OVERDUE_DAYS} days")
