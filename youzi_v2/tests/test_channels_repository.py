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
    res = repo.seed_defaults()
    assert res["total"] == 26
    assert res["inserted"] == 26
    listed = repo.list_rows(limit=100)
    assert listed["total"] == 26
    row = repo.get_row("Air Express Economy Service")
    assert row is not None
    assert row["nameZh"] == "美国空运"
    assert row["country"] == "美国"
    assert row["category"] == "空运"


def test_create_validates_category(repo: ChannelsRepository) -> None:
    with pytest.raises(ValueError, match="大类"):
        repo.create(
            {
                "code": "X",
                "nameZh": "测试",
                "category": "无效",
            }
        )
