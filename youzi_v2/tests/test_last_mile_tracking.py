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
    assert url.count(",") == 39


def test_extract_last_mile_from_track_desc():
    from youzi_v2.last_mile_tracking import extract_last_mile_from_track_desc

    hit = extract_last_mile_from_track_desc(
        "货物已交快递派送，FedEx 877617962361，请留意查收"
    )
    assert hit is not None
    assert hit[0] == "877617962361"
    assert hit[1] == "fedex"

    hit2 = extract_last_mile_from_track_desc("UPS 1ZA06B016813555890 out for delivery")
    assert hit2 is not None
    assert hit2[0] == "1ZA06B016813555890"
    assert hit2[1] == "ups"

    assert extract_last_mile_from_track_desc("Arriving at the destination") is None
    assert extract_last_mile_from_track_desc("FedEx 123") is None


def test_pick_latest_last_mile_prefers_newest_track():
    from youzi_v2.last_mile_tracking import pick_latest_last_mile_from_track_rows

    rows = [
        {
            "id": "t1",
            "tracking_time": "2026-06-01 10:00:00",
            "tracking_desc": "FedEx 877617962361",
            "created_time": "2026-06-01 10:00:00",
        },
        {
            "id": "t2",
            "tracking_time": "2026-06-10 12:00:00",
            "tracking_desc": "UPS 1ZA06B016813555890",
            "created_time": "2026-06-10 12:00:00",
        },
    ]
    picked = pick_latest_last_mile_from_track_rows(rows)
    assert picked is not None
    assert picked[0] == "1ZA06B016813555890"
    assert picked[1] == "ups"
    assert picked[2]["id"] == "t2"
