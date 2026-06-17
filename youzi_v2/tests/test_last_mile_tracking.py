"""尾程单号前缀剥离。"""

from youzi_v2.last_mile_tracking import (
    normalize_last_mile_tracking_number,
    normalize_tracking_field_value,
)


def test_ups_with_space():
    n, hint = normalize_last_mile_tracking_number("UPS 1ZA06B016813555890")
    assert n == "1ZA06B016813555890"
    assert hint == "ups"


def test_fedex_colon():
    n, hint = normalize_last_mile_tracking_number("FedEx: 123456789012")
    assert n == "123456789012"
    assert hint == "fedex"


def test_plain_number_unchanged():
    n, hint = normalize_last_mile_tracking_number("1ZA06B016813555890")
    assert n == "1ZA06B016813555890"
    assert hint == "ups"


def test_tracking_prefix_carrier_hints():
    from youzi_v2.last_mile_tracking import infer_last_mile_carrier_hint

    assert infer_last_mile_carrier_hint("871877368540") == "fedex"
    assert infer_last_mile_carrier_hint("1ZA06B016813555890") == "ups"
    assert infer_last_mile_carrier_hint("15502802948687") == "dpd"
    assert infer_last_mile_carrier_hint("C03IK469759415360001") == "conwest"
    assert infer_last_mile_carrier_hint("00340434660911997839") == "dhl"


def test_normalize_field_empty():
    assert normalize_tracking_field_value("") is None
    assert normalize_tracking_field_value("  UPS 1Z999  ") == "1Z999"


def test_cwe_prefix_strip():
    n, hint = normalize_last_mile_tracking_number("CWE C03IK469759415360001")
    assert n == "C03IK469759415360001"
    assert hint == "conwest"


def test_dpd_prefix_strip():
    n, hint = normalize_last_mile_tracking_number("DPD 12345678901234")
    assert n == "12345678901234"
    assert hint == "dpd"


def test_dpduk_compact_prefix():
    n, hint = normalize_last_mile_tracking_number("DPDUK98765432109876")
    assert n == "98765432109876"
    assert hint == "dpd"


def test_conwest_number_hint():
    from youzi_v2.last_mile_tracking import infer_last_mile_carrier_hint

    assert infer_last_mile_carrier_hint("C03IK469759415360001") == "conwest"


def test_conwest_expand_40_pieces():
    from youzi_v2.last_mile_tracking import expand_conwest_tracking_numbers

    seed = "C03IK469759415360001"
    nums = expand_conwest_tracking_numbers(seed, 40)
    assert len(nums) == 40
    assert nums[0] == "C03IK469759415360001"
    assert nums[-1] == "C03IK469759415360040"
    assert nums[1] == "C03IK469759415360002"


def test_conwest_17track_url_max_40():
    from youzi_v2.last_mile_tracking import build_conwest_17track_url, expand_conwest_tracking_numbers

    nums = expand_conwest_tracking_numbers("C03IK469759415360001", 50)
    url = build_conwest_17track_url(nums)
    assert url is not None
    assert "fc=100467" in url
    assert url.count(",") == 39
    assert "C03IK469759415360040" in url
    assert "C03IK469759415360041" not in url
