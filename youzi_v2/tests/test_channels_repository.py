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


def test_migrate_legacy_categories(repo: ChannelsRepository) -> None:
    now = "2026-01-01 00:00:00"
    conn = repo._conn  # noqa: SLF001 — 模拟存量旧数据
    conn.execute(
        """
        INSERT INTO channel_codes (
            code, name_zh, name_en, country, category, note,
            sort_order, is_active, created_time, updated_time
        ) VALUES (?, ?, ?, '', ?, '', 0, 1, ?, ?)
        """,
        ("Legacy Sea", "旧海运", "Legacy Sea", "海运", now, now),
    )
    conn.execute(
        """
        INSERT INTO channel_codes (
            code, name_zh, name_en, country, category, note,
            sort_order, is_active, created_time, updated_time
        ) VALUES (?, ?, ?, '', ?, '', 0, 1, ?, ?)
        """,
        ("Legacy Fast", "旧快船", "Legacy Fast", "海运", now, now),
    )
    conn.commit()
    n = repo.migrate_legacy_categories()
    assert n >= 2
    assert repo.get_row("Legacy Sea")["category"] == "普船"
    assert repo.get_row("Legacy Fast")["category"] == "快船"


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
