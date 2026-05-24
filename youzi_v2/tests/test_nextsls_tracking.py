"""NextSLS 轨迹解析单元测试。"""

from youzi_v2.services.carrier_vendors import (
    _extract_carrier_id,
    _extract_outer_tracking_number,
    _maybe_repair_text,
    _nextsls_mode,
    _nextsls_number_param,
    _parse_nextsls_json,
    parse_nextsls_shipment,
)

SAMPLE_SHIPMENT = {
    "client_reference": "DPSECO260327063",
    "traces": [
        {"time": "2026-04-18 14:34:03", "info": "已开船 5/31到港"},
        {"time": "2026-04-08 09:50:24", "info": "已下单"},
    ],
}


def test_nextsls_mode_app():
    assert (
        _nextsls_mode({"apiUrl": "https://hbqexp.nextsls.com/tracking/app"})
        == "app"
    )


def test_nextsls_number_param_from_url():
    assert (
        _nextsls_number_param(
            {"apiUrl": "https://tracking.nextsls.com/rest/trace/tracking/lists"}
        )
        == "number"
    )
    assert _nextsls_number_param({"apiUrl": "https://tracking.nextsls.com/trace"}) == "numbers"


def test_parse_nextsls_shipment_newest_first():
    logs = parse_nextsls_shipment(SAMPLE_SHIPMENT)
    assert logs[0][0] == "2026-04-18 14:34:03"
    assert "开船" in logs[0][1]


def test_extract_carrier_id_shipment_id():
    assert _extract_carrier_id({"shipment_id": " SHP-99 "}) == "SHP-99"
    assert _extract_carrier_id({"jobNum": "J1"}) == "J1"


def test_extract_outer_tracking_number():
    assert (
        _extract_outer_tracking_number(
            {"outer_carrier_tracking_number": "UPS 1ZK351H66829979895"}
        )
        == "1ZK351H66829979895"
    )
    assert _extract_outer_tracking_number({"outer_carrier_tracking_number": ""}) == ""


def test_repair_utf8_mojibake_nextsls_trace():
    garbled = "æµ·è¿å®éå·²å¼è¹"
    fixed = _maybe_repair_text(garbled)
    assert "海运" in fixed
    assert "æµ·" not in fixed


def test_parse_nextsls_json_returns_carrier_id():
    payload = {
        "status": 1,
        "data": {
            "shipment": {
                **SAMPLE_SHIPMENT,
                "shipment_id": "NSLS-12345",
                "outer_carrier_tracking_number": "UPS 1ZK351H66829979895",
            }
        },
    }
    logs, err, carrier_id, tracking_number = _parse_nextsls_json(payload)
    assert err is None
    assert carrier_id == "NSLS-12345"
    assert tracking_number == "1ZK351H66829979895"
    assert len(logs) == 2
