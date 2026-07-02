"""承运商轨迹：运单 carrier_code 按 config vendors.id 匹配 vendor。"""

from __future__ import annotations

from youzi_v2.services.carrier_vendors import (
    build_vendor_maps,
    carrier_vendor_unassigned_reason,
    resolve_vendor_for_row,
)

_VENDORS = [
    {"id": "1724258253196189697", "name": "TXFBA", "platform": "txfba"},
    {"id": "998877", "name": "TOPDA", "aliases": ["拓达"]},
]


def test_resolve_vendor_by_carrier_code_id() -> None:
    by_name, by_id = build_vendor_maps(_VENDORS)
    vendor = resolve_vendor_for_row(
        {"carrier_code": "1724258253196189697", "supplier_name": ""},
        by_name,
        by_id,
    )
    assert vendor is not None
    assert vendor["name"] == "TXFBA"


def test_resolve_vendor_by_code_table_mapping() -> None:
    by_name, by_id = build_vendor_maps(_VENDORS)
    vendor = resolve_vendor_for_row(
        {"carrier_code": "TXFBA", "supplier_name": ""},
        by_name,
        by_id,
        code_to_carrier_id={"TXFBA": "1724258253196189697"},
    )
    assert vendor is not None
    assert vendor["name"] == "TXFBA"


def test_resolve_vendor_fallback_name_and_alias() -> None:
    by_name, by_id = build_vendor_maps(_VENDORS)
    assert resolve_vendor_for_row(
        {"carrier_code": "TOPDA", "supplier_name": ""},
        by_name,
        by_id,
    )["name"] == "TOPDA"
    assert resolve_vendor_for_row(
        {"carrier_code": "", "supplier_name": "拓达"},
        by_name,
        by_id,
    )["name"] == "TOPDA"


def test_unassigned_reason_mentions_vendor_id() -> None:
    by_name, by_id = build_vendor_maps(_VENDORS)
    msg = carrier_vendor_unassigned_reason(
        {"carrier_code": "unknown-id", "supplier_name": ""},
        by_name,
        by_id,
    )
    assert "vendors.id" in msg
