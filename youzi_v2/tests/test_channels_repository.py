"""渠道管理仓储测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from youzi_v2.db.channel_seeds import CHANNEL_SEEDS
from youzi_v2.db.channels_repository import ChannelsRepository
from youzi_v2.db.connection import Database


@pytest.fixture
def repo(tmp_path: Path) -> ChannelsRepository:
    return ChannelsRepository(Database(tmp_path / "test.db"))


def test_seed_defaults_replaces_all(repo: ChannelsRepository) -> None:
    listed_before = repo.list_rows(limit=500)
    assert listed_before["total"] == len(CHANNEL_SEEDS)
    # 掺入一条自定义渠道，确认会被清空
    repo.create({"code": "CUSTOM-ONLY", "nameZh": "自定义", "category": "空运"})
    assert repo.get_row("CUSTOM-ONLY") is not None

    res = repo.seed_defaults()
    assert res["total"] == len(CHANNEL_SEEDS)
    assert res["inserted"] == len(CHANNEL_SEEDS)
    assert res["deleted"] >= len(CHANNEL_SEEDS)
    assert repo.get_row("CUSTOM-ONLY") is None

    listed = repo.list_rows(limit=500)
    assert listed["total"] == len(CHANNEL_SEEDS)
    row = repo.get_row("STS-LAX")
    assert row is not None
    assert row["nameZh"] == "海卡经济达-洛杉矶"
    assert row["dpsChannelName"] == "海卡经济达-洛杉矶"
    assert row["nameEn"] == "Sea Truck Standard Service - LAX"
    assert row["country"] == "美国"
    assert row["category"] == "普船"
    fast = repo.get_row("STR-LAX")
    assert fast is not None
    assert fast["nameZh"] == "海卡快速达-洛杉矶"
    assert fast["dpsChannelName"] == "海卡快速达-洛杉矶"
    assert fast["category"] == "快船"
    air = repo.get_row("AEE")
    assert air is not None
    assert air["dpsChannelName"] == "空派慢飞达"
    assert repo.lookup_code_by_dps_channel_name("空派慢飞达") == "AEE"


def test_rename_code_updates_shipments(repo: ChannelsRepository) -> None:
    from youzi_v2.db.shipments_repository import ShipmentsRepository

    repo.create({"code": "OLD-CH", "nameZh": "旧渠道", "category": "空运"})
    ship_repo = ShipmentsRepository(repo._database)
    ship_repo.insert_row({"shipment_no": "SN001", "channel_code": "OLD-CH"})
    updated = repo.update("OLD-CH", {"code": "NEW-CH", "nameZh": "新渠道"})
    assert updated["code"] == "NEW-CH"
    row = ship_repo.get_by_shipment_no("SN001")
    assert row is not None
    assert row["channelCode"] == "NEW-CH"


def test_create_validates_category(repo: ChannelsRepository) -> None:
    with pytest.raises(ValueError, match="大类"):
        repo.create(
            {
                "code": "X",
                "nameZh": "测试",
                "category": "无效",
            }
        )
    row = repo.create({"code": "Rail-X", "nameZh": "中欧铁路", "category": "铁路"})
    assert row["category"] == "铁路"


def test_dps_channel_name_create_and_lookup(repo: ChannelsRepository) -> None:
    row = repo.create(
        {
            "code": "LOCAL-SEA",
            "nameZh": "本地海运",
            "category": "普船",
            "dpsChannelName": "DPS Sea Truck",
        }
    )
    assert row["dpsChannelName"] == "DPS Sea Truck"
    assert repo.lookup_code_by_dps_channel_name("DPS Sea Truck") == "LOCAL-SEA"
    assert repo.lookup_code_by_dps_channel_name("missing") is None

    updated = repo.update(
        "LOCAL-SEA",
        {
            "code": "LOCAL-SEA",
            "nameZh": "本地海运",
            "category": "普船",
            "dpsChannelName": "DPS Sea Truck V2",
        },
    )
    assert updated["dpsChannelName"] == "DPS Sea Truck V2"
    assert repo.lookup_code_by_dps_channel_name("DPS Sea Truck") is None
    assert repo.lookup_code_by_dps_channel_name("DPS Sea Truck V2") == "LOCAL-SEA"


def test_seed_defaults_remaps_shipment_english_name(repo: ChannelsRepository) -> None:
    from youzi_v2.db.shipments_repository import ShipmentsRepository

    ship_repo = ShipmentsRepository(repo._database)
    ship_repo.insert_row(
        {
            "shipment_no": "SN-REMAP",
            "channel_code": "Sea Truck Standard Service - LAX",
        }
    )
    repo.seed_defaults()
    row = ship_repo.get_by_shipment_no("SN-REMAP")
    assert row is not None
    assert row["channelCode"] == "STS-LAX"
