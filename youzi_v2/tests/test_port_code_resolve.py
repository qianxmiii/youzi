import sqlite3

from youzi_v2.db.code_tables import ensure_schema
from youzi_v2.db.datetime_util import now_str
from youzi_v2.services.port_code_resolve import PortCodeResolver


def test_resolve_by_name_en_and_enrich():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    now = now_str()
    conn.execute(
        """
        INSERT INTO port_codes (
            code, name_zh, name_en, port_type,
            sort_order, is_active, created_time, updated_time
        ) VALUES (?, ?, ?, 'both', 0, 1, ?, ?)
        """,
        ("NYC", "纽约", "NEWYORK", now, now),
    )
    resolver = PortCodeResolver(conn)
    hit = resolver.resolve("NEWYORK")
    assert hit is not None
    assert hit["code"] == "NYC"
    assert hit["nameZh"] == "纽约"

    row = resolver.enrich_port_call({"portName": "NEWYORK", "sequence": 1})
    assert row["portCode"] == "NYC"
    assert row["portCnname"] == "纽约"
    assert row["portNameEn"] == "NEWYORK"
    assert row["portName"] == "NEWYORK"

    assert resolver.resolve("Unknown Port") is None
