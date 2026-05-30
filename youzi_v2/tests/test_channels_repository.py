"""渠道管理仓储测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from youzi_v2.db.channels_repository import ChannelsRepository
from youzi_v2.db.connection import Database


@pytest.fixture
def repo(tmp_path: Path) -> ChannelsRepository:
    return ChannelsRepository(Database(tmp_path / "test.db"))


def test_seed_defaults_inserts_26(repo: ChannelsRepository) -> None:
    listed_before = repo.list_rows(limit=100)
    assert listed_before["total"] == 27
    res = repo.seed_defaults()
    assert res["total"] == 27
    assert res["inserted"] == 0
    assert res["updated"] == 27
    listed = repo.list_rows(limit=100)
    assert listed["total"] == 27
    row = repo.get_row("Sea Truck Standard Service - LAX")
    assert row is not None
    assert row["nameZh"] == "美国普船"
    assert row["country"] == "美国"
    assert row["category"] == "普船"
    fast = repo.get_row("Sea Truck Rapid Service - LAX")
    assert fast is not None
    assert fast["category"] == "快船"


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
