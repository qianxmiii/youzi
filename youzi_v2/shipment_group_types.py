"""已废弃：分组类型体系已移除，请使用 shipment_group_rules。"""

from __future__ import annotations

from .shipment_group_rules import rules_meta

# 兼容旧 import；不再提供分组类型
GROUP_TYPES = frozenset()


def group_types_meta() -> list[dict[str, str]]:
    """@deprecated 使用 shipment_group_rules.rules_meta()"""
    return rules_meta()
