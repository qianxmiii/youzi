"""运单 express_code 尾程快递指定。"""

from youzi_v2.last_mile_tracking import (
    express_code_to_carrier_hint,
    normalize_express_code,
)


def test_normalize_express_code_canonical():
    assert normalize_express_code("ups") == "UPS"
    assert normalize_express_code("FedEx") == "FEDEX"
    assert normalize_express_code("cwe") == "CWE"
    assert normalize_express_code("") is None
    assert normalize_express_code("自动识别") is None


def test_express_code_overrides_hint():
    assert express_code_to_carrier_hint("UPS") == "ups"
    assert express_code_to_carrier_hint("FEDEX") == "fedex"
    assert express_code_to_carrier_hint("CWE") == "conwest"
    assert express_code_to_carrier_hint("DPD") == "dpd"
