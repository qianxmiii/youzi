"""船名 / 航次 / 船名航次 字段工具测试。"""

from youzi_v2.services.vessel_voyage_fields import (
    compose_vessel_voyage,
    parse_vessel_voyage,
    resolve_voyage_identity,
)


def test_parse_vessel_voyage():
    assert parse_vessel_voyage("CSCL BOHAI SEA/076E") == ("CSCL BOHAI SEA", "076E")
    assert parse_vessel_voyage("NO SLASH") == ("NO SLASH", None)
    assert parse_vessel_voyage("") == (None, None)


def test_compose_vessel_voyage():
    assert compose_vessel_voyage("CSCL BOHAI SEA", "076E") == "CSCL BOHAI SEA/076E"
    assert compose_vessel_voyage("ONLY NAME", None) == "ONLY NAME"


def test_resolve_from_split_fields():
    vv, name, voy = resolve_voyage_identity(vessel_name="A SHIP", voyage_no="001W")
    assert vv == "A SHIP/001W"
    assert name == "A SHIP"
    assert voy == "001W"


def test_resolve_from_combined():
    vv, name, voy = resolve_voyage_identity(vessel_voyage="A SHIP/001W")
    assert vv == "A SHIP/001W"
    assert name == "A SHIP"
    assert voy == "001W"
