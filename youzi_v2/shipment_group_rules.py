"""运单分组规则类型与元数据（见 docs/design/shipment-groups-design.md）。"""

from __future__ import annotations

from typing import Any

RULE_TYPE_BATCH_DELIVERY_DEADLINE = "BATCH_DELIVERY_DEADLINE"
RULE_TYPE_GROUP_ARRIVED_PAYMENT = "GROUP_ARRIVED_PAYMENT"
RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING = "SINGLE_IN_TRANSIT_ETA_WARNING"
# 旧规则名，迁移后不再写入
RULE_TYPE_LAST_BATCH_ARRIVED_PAYMENT = "LAST_BATCH_ARRIVED_PAYMENT"

RULE_TYPES = frozenset(
    {
        RULE_TYPE_BATCH_DELIVERY_DEADLINE,
        RULE_TYPE_GROUP_ARRIVED_PAYMENT,
        RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING,
    }
)

RULE_TYPE_LABELS: dict[str, str] = {
    RULE_TYPE_BATCH_DELIVERY_DEADLINE: "签收期限提醒",
    RULE_TYPE_GROUP_ARRIVED_PAYMENT: "整组到港催款",
    RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING: "单票在途到港预警",
}

RULE_TYPE_DESCRIPTIONS: dict[str, str] = {
    RULE_TYPE_BATCH_DELIVERY_DEADLINE: "同组首票签收后，未签收运单在期限前/超期提醒",
    RULE_TYPE_GROUP_ARRIVED_PAYMENT: "组内全部到港且未付清时提醒催款",
    RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING: "客户仅有一票在途时，按 ETA 提前 N 天提醒到港",
}

PAYMENT_STATUS_LABELS: dict[str, str] = {
    "UNPAID": "未付",
    "PARTIAL": "部分",
    "PAID": "已付",
}


def payment_status_label(status: str | None) -> str:
    key = (status or "").strip().upper()
    return PAYMENT_STATUS_LABELS.get(key, key or "未付")

DEFAULT_RULE_THRESHOLDS: dict[str, tuple[int | None, int | None]] = {
    RULE_TYPE_BATCH_DELIVERY_DEADLINE: (30, 7),
    RULE_TYPE_GROUP_ARRIVED_PAYMENT: (None, None),
    RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING: (None, 10),
}


def normalize_rule_type(value: str | None) -> str:
    key = (value or "").strip().upper()
    if key == RULE_TYPE_LAST_BATCH_ARRIVED_PAYMENT:
        return RULE_TYPE_GROUP_ARRIVED_PAYMENT
    if key not in RULE_TYPES:
        raise ValueError(
            f"ruleType 无效：{value}，须为 {', '.join(sorted(RULE_TYPES))}"
        )
    return key


def rule_type_label(value: str | None) -> str:
    key = normalize_rule_type(value) if value else ""
    return RULE_TYPE_LABELS.get(key, value or "")


def rules_meta() -> list[dict[str, str]]:
    return [
        {
            "value": key,
            "label": RULE_TYPE_LABELS[key],
            "description": RULE_TYPE_DESCRIPTIONS.get(key, ""),
        }
        for key in sorted(RULE_TYPES)
    ]


def validate_rule_payload(rule_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化单条规则配置。"""
    rt = normalize_rule_type(rule_type)
    enabled = bool(payload.get("enabled", True))
    threshold = payload.get("threshold_days", payload.get("thresholdDays"))
    warning = payload.get("warning_days", payload.get("warningDays"))
    trigger_status = (payload.get("trigger_status") or payload.get("triggerStatus") or "").strip()
    config_json = payload.get("config_json") or payload.get("configJson") or "{}"
    if not isinstance(config_json, str):
        import json

        config_json = json.dumps(config_json, ensure_ascii=False)

    threshold_days: int | None
    warning_days: int | None
    if threshold is None or threshold == "":
        threshold_days = DEFAULT_RULE_THRESHOLDS[rt][0]
    else:
        threshold_days = int(threshold)
    if warning is None or warning == "":
        warning_days = DEFAULT_RULE_THRESHOLDS[rt][1]
    else:
        warning_days = int(warning)

    if rt == RULE_TYPE_BATCH_DELIVERY_DEADLINE:
        if threshold_days is None or threshold_days <= 0:
            raise ValueError("BATCH_DELIVERY_DEADLINE 需要有效的 thresholdDays")
        if warning_days is None or warning_days < 0:
            raise ValueError("BATCH_DELIVERY_DEADLINE 需要有效的 warningDays")
        if warning_days > threshold_days:
            raise ValueError("warningDays 不能大于 thresholdDays")
    elif rt == RULE_TYPE_SINGLE_IN_TRANSIT_ETA_WARNING:
        if warning_days is None or warning_days <= 0:
            raise ValueError("SINGLE_IN_TRANSIT_ETA_WARNING 需要有效的 warningDays（提前到港提醒天数）")
        threshold_days = None

    return {
        "ruleType": rt,
        "enabled": enabled,
        "thresholdDays": threshold_days,
        "warningDays": warning_days,
        "triggerStatus": trigger_status,
        "configJson": config_json,
    }
