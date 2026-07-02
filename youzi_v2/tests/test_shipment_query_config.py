"""运单查询 URL、分页与报文解析。"""

from __future__ import annotations

import json
from pathlib import Path

from youzi_v2.services.shipment_query_config import (
    build_shipment_query_by_order_url,
    build_shipment_query_by_person_url,
    load_shipment_query_by_order_config,
    load_shipment_query_by_person_config,
    normalize_shipment_nos,
    parse_shipment_query_response,
    query_shipments_by_order,
    query_shipments_by_person,
    shipment_odd,
)


def test_load_shipment_query_by_person_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "shipment_queryByPerson": {
                    "url": "https://example.com/list?pageSize=10&salesAssistantId=1",
                    "Authorization": "Bearer person-token",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cfg = load_shipment_query_by_person_config(cfg_path)
    assert "salesAssistantId=1" in cfg["url"]
    assert cfg["authorization"] == "Bearer person-token"
    assert cfg["pageSize"] == 10


def test_load_shipment_query_by_order_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "shipment_queryByOrder": {
                    "url": "https://example.com/list?pageSize=10",
                    "Authorization": "Bearer order-token",
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    cfg = load_shipment_query_by_order_config(cfg_path)
    assert cfg["authorization"] == "Bearer order-token"
    assert cfg["pageSize"] == 10


def test_build_shipment_query_by_person_url() -> None:
    url = build_shipment_query_by_person_url(
        "https://example.com/list?pageSize=10&pageNum=99&status=3",
        page_num=2,
        transit_time_start="2026-06-01 00:00:00",
        transit_time_end="2026-06-30 23:59:59",
    )
    assert "pageSize=10" in url
    assert "status=3" in url
    assert "pageNum=2" in url
    assert "transitTimeStart=2026-06-01%2000%3A00%3A00" in url
    assert "transitTimeEnd=2026-06-30%2023%3A59%3A59" in url
    assert "pageNum=99" not in url


def test_default_transit_time_range_june() -> None:
    from datetime import datetime

    from youzi_v2.services.shipment_query_config import default_transit_time_range

    start, end = default_transit_time_range(datetime(2026, 6, 18, 12, 0, 0))
    assert start == "2026-06-01 00:00:00"
    assert end == "2026-06-30 23:59:59"


def test_build_shipment_query_by_order_url() -> None:
    url = build_shipment_query_by_order_url(
        "https://example.com/list?pageSize=10",
        ["DPSECO260610178", "DPSECO260629039"],
        page_num=1,
    )
    assert (
        url
        == "https://example.com/list?pageSize=10&odds=DPSECO260610178%20DPSECO260629039&pageNum=1"
    )


def test_parse_shipment_query_response() -> None:
    parsed = parse_shipment_query_response(
        {
            "total": 2,
            "rows": [{"odd": "A"}, {"odd": "B"}],
            "code": 200,
            "msg": "查询成功",
        }
    )
    assert parsed["total"] == 2
    assert shipment_odd(parsed["rows"][0]) == "A"


def test_query_shipments_by_person_paginates(monkeypatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "shipment_queryByPerson": {
                    "url": "https://example.com/list?pageSize=10",
                    "Authorization": "token",
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[int] = []

    def fake_page(config_path, *, page_num=1, transit_time_start=None, transit_time_end=None, timeout=30):
        calls.append(page_num)
        rows = (
            [{"odd": f"SN{i:02d}"} for i in range(10)]
            if page_num == 1
            else [{"odd": f"SN{i:02d}"} for i in range(10, 12)]
        )
        return {"code": 200, "msg": "ok", "total": 12, "rows": rows}, None

    monkeypatch.setattr(
        "youzi_v2.services.shipment_query_config.query_shipments_by_person_page",
        fake_page,
    )

    result, err = query_shipments_by_person(cfg_path)
    assert err is None
    assert result is not None
    assert len(result["rows"]) == 12
    assert calls == [1, 2]


def test_query_shipments_by_order_paginates(monkeypatch, tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "shipment_queryByOrder": {
                    "url": "https://example.com/list?pageSize=10",
                    "Authorization": "token",
                }
            }
        ),
        encoding="utf-8",
    )
    calls: list[int] = []

    def fake_page(shipment_nos, config_path, *, page_num=1, timeout=30):
        calls.append(page_num)
        if page_num == 1:
            return {
                "code": 200,
                "msg": "ok",
                "total": 15,
                "rows": [{"odd": f"SN{i:02d}"} for i in range(10)],
            }, None
        return {
            "code": 200,
            "msg": "ok",
            "total": 15,
            "rows": [{"odd": f"SN{i:02d}"} for i in range(10, 15)],
        }, None

    monkeypatch.setattr(
        "youzi_v2.services.shipment_query_config.query_shipments_by_order_page",
        fake_page,
    )

    result, err = query_shipments_by_order(["A"], cfg_path)
    assert err is None
    assert result is not None
    assert len(result["rows"]) == 15
    assert calls == [1, 2]


def test_normalize_shipment_nos_dedupe_and_comma() -> None:
    assert normalize_shipment_nos("A, B\nA, C") == ["A", "B", "C"]
