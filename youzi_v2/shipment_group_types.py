"""运单分组类型枚举、中文标签与规则适用性（见 docs/design/shipment-groups-design.md）。"""

from __future__ import annotations

GROUP_TYPES = frozenset(
    {
        "MANUAL",
        "CUSTOMER_BATCH",
        "ORDER_BATCH",
        "VESSEL_BATCH",
        "PORT_BATCH",
        "PAYMENT_BATCH",
    }
)

GROUP_TYPE_LABELS: dict[str, str] = {
    "MANUAL": "手动分组",
    "CUSTOMER_BATCH": "客户批次",
    "ORDER_BATCH": "订单批次",
    "VESSEL_BATCH": "船次批次",
    "PORT_BATCH": "到港批次",
    "PAYMENT_BATCH": "收款批次",
}

GROUP_TYPE_DESCRIPTIONS: dict[str, str] = {
    "MANUAL": "临时跟进、运营人工整理的任意组合",
    "CUSTOMER_BATCH": "同一客户的一批货，统一跟进签收、罚款和收款",
    "ORDER_BATCH": "同一客户订单或平台订单下的多票运单",
    "VESSEL_BATCH": "同一船名航次的一批海运货",
    "PORT_BATCH": "同一目的港或同一 ETA 窗口内的货",
    "PAYMENT_BATCH": "以催款、账期、尾款为核心管理的一组运单",
}

BATCH_DELIVERY_DEADLINE_GROUP_TYPES = frozenset(
    {"CUSTOMER_BATCH", "ORDER_BATCH", "MANUAL"}
)
LAST_BATCH_ARRIVED_PAYMENT_GROUP_TYPES = frozenset(
    {"VESSEL_BATCH", "PORT_BATCH", "PAYMENT_BATCH", "MANUAL"}
)

RULE_TYPE_BATCH_DELIVERY_DEADLINE = "BATCH_DELIVERY_DEADLINE"
RULE_TYPE_LAST_BATCH_ARRIVED_PAYMENT = "LAST_BATCH_ARRIVED_PAYMENT"

_RULE_APPLICABILITY: dict[str, frozenset[str]] = {
    RULE_TYPE_BATCH_DELIVERY_DEADLINE: BATCH_DELIVERY_DEADLINE_GROUP_TYPES,
    RULE_TYPE_LAST_BATCH_ARRIVED_PAYMENT: LAST_BATCH_ARRIVED_PAYMENT_GROUP_TYPES,
}

GROUP_TYPE_ORDER: tuple[str, ...] = (
    "MANUAL",
    "CUSTOMER_BATCH",
    "ORDER_BATCH",
    "VESSEL_BATCH",
    "PORT_BATCH",
    "PAYMENT_BATCH",
)


def normalize_group_type(value: str | None, *, default: str = "MANUAL") -> str:
    key = (value or default).strip().upper()
    if key not in GROUP_TYPES:
        raise ValueError(f"groupType 无效：{value}")
    return key


def normalize_group_types(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for raw in values:
        key = normalize_group_type(raw)
        if key not in out:
            out.append(key)
    return out


def normalize_types_payload(
    *,
    primary_type: str | None = None,
    group_types: list[str] | None = None,
    legacy_group_type: str | None = None,
) -> tuple[str, list[str]]:
    """解析 primaryType + groupTypes；兼容旧字段 groupType。"""
    if group_types:
        types = normalize_group_types(group_types)
        if not types:
            raise ValueError("groupTypes 至少包含一项")
        primary = normalize_group_type(
            primary_type or legacy_group_type or types[0],
        )
        if primary not in types:
            raise ValueError("primaryType 必须包含在 groupTypes 中")
        return primary, types
    primary = normalize_group_type(primary_type or legacy_group_type or "MANUAL")
    return primary, [primary]


def sort_group_types(types: list[str] | frozenset[str]) -> list[str]:
    order = {key: idx for idx, key in enumerate(GROUP_TYPE_ORDER)}
    return sorted({t.strip().upper() for t in types if t}, key=lambda k: order.get(k, 99))


def group_type_label(value: str | None) -> str:
    key = (value or "MANUAL").strip().upper()
    return GROUP_TYPE_LABELS.get(key, key)


def rule_applies_to_group_types(
    rule_type: str,
    group_types: set[str] | frozenset[str] | list[str] | None,
) -> bool:
    allowed = _RULE_APPLICABILITY.get((rule_type or "").strip().upper())
    if not allowed:
        return False
    active = frozenset((group_types or {"MANUAL"}))
    return bool(active & allowed)


def rule_applies_to_group_type(rule_type: str, group_type: str | None) -> bool:
    """单类型判断（兼容旧调用）。"""
    return rule_applies_to_group_types(rule_type, {group_type or "MANUAL"})


def group_types_meta() -> list[dict[str, str]]:
    return [
        {
            "value": key,
            "label": GROUP_TYPE_LABELS[key],
            "description": GROUP_TYPE_DESCRIPTIONS.get(key, ""),
        }
        for key in GROUP_TYPE_ORDER
    ]
