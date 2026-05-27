"""多船公司船期 Provider 测试。"""

from youzi_v2.services.maritime_schedule import (
    fetch_vessel_schedule,
    list_schedule_providers,
    resolve_schedule_provider,
)
from youzi_v2.services.maritime_schedule import search_carrier_vessels
from youzi_v2.services.vessel_voyage_fields import shipment_voyage_match_sql
from youzi_v2.services.maritime_schedule.providers.cosco_elines import (
    _parse_vessel_search_rows,
    parse_elines_purpo_rows,
)

SAMPLE_ROWS = [
    {
        "id": 1,
        "loopAbbrv": "AAS2",
        "vesselCode": "T93",
        "vesselName": "COSCO PRINCE RUPERT",
        "voy": "0P518E1MA/0P519W1MA",
        "protName": "Hai Phong",
        "arrDtlocAct": "2026-05-18 14:21",
        "depDtlocAct": "2026-05-19 16:46",
    },
    {
        "id": 4,
        "vesselCode": "T93",
        "protName": "Yantian",
        "arrDtlocCos": "2026-05-28 15:00",
        "depDtlocCos": "2026-05-29 16:00",
    },
]


def test_list_providers():
    items = list_schedule_providers()
    assert any(p["id"] == "cosco_elines" for p in items)


def test_resolve_by_alias():
    p = resolve_schedule_provider("中远海运")
    assert p.info.shipping_company == "COSCO"


def test_parse_elines_rows():
    out = parse_elines_purpo_rows(
        SAMPLE_ROWS,
        shipping_company="COSCO",
        source_label="COSCO eLines",
    )
    assert out["vesselCode"] == "T93"
    assert len(out["portCalls"]) == 2


def test_parse_vessel_search_rows():
    items = _parse_vessel_search_rows(
        {
            "code": "200",
            "data": {
                "content": [
                    {"code": "CCF", "description": "COSCO AMERICA", "chineseDescription": None}
                ]
            },
        },
        label="COSCO",
    )
    assert items[0]["vesselCode"] == "CCF"
    assert items[0]["vesselName"] == "COSCO AMERICA"


def test_search_carrier_vessels_cosco():
    items = search_carrier_vessels("COSCO", "COSCO AMERICA")
    assert any(x["vesselCode"] == "CCF" for x in items)


def test_shipment_voyage_match_includes_vessel_name_only():
    sql, params = shipment_voyage_match_sql(
        "COSCO SHIPPING STAR/029W/029E",
        "COSCO SHIPPING STAR",
        "029W/029E",
    )
    assert "vessel_voyage = ?" in sql
    assert "COSCO SHIPPING STAR" in params
    assert "COSCO SHIPPING STAR/029W/029E" in params


def test_fetch_routes_unknown_carrier():
    try:
        fetch_vessel_schedule("UNKNOWN_LINE", "X01")
        assert False, "should raise"
    except ValueError as exc:
        assert "暂不支持" in str(exc)
