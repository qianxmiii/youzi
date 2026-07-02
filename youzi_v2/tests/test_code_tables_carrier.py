"""承运商码表 carrier_id 映射测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from youzi_v2.db.code_tables_repository import CodeTablesRepository
from youzi_v2.db.connection import Database


@pytest.fixture
def repo(tmp_path: Path) -> CodeTablesRepository:
    return CodeTablesRepository(Database(tmp_path / "test.db"))


def test_carrier_codes_carrier_id_crud(repo: CodeTablesRepository) -> None:
    row = repo.insert_row(
        "carrier_codes",
        {
            "code": "TXFBA",
            "nameZh": "腾信",
            "carrier_id": "1724258253196189697",
        },
    )
    assert row["carrierId"] == "1724258253196189697"
    assert repo.lookup_carrier_code_by_id("1724258253196189697") == "TXFBA"
    updated = repo.update_row(
        "carrier_codes",
        "TXFBA",
        {"carrierId": "999"},
    )
    assert updated["carrierId"] == "999"
    assert repo.lookup_carrier_code_by_id("1724258253196189697") is None
    assert repo.lookup_carrier_code_by_id("999") == "TXFBA"
