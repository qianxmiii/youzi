"""诊断 youzi_v2.db 损坏情况并尝试导出可读数据。"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "youzi_v2.db"


def main() -> int:
    if not DB.exists():
        print(f"数据库不存在: {DB}")
        return 1

    print(f"文件: {DB} ({DB.stat().st_size:,} bytes)")
    for suffix in ("-wal", "-shm"):
        p = Path(str(DB) + suffix)
        if p.exists():
            print(f"  {p.name}: {p.stat().st_size:,} bytes")

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"integrity_check: {integrity if len(integrity) < 80 else integrity[:80] + '...'}")
    except Exception as exc:
        print(f"integrity_check 失败: {exc}")

    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
        print("wal_checkpoint: ok")
    except Exception as exc:
        print(f"wal_checkpoint: {exc}")

    try:
        tables = [
            r[0]
            for r in conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
    except Exception as exc:
        print(f"读取表清单失败: {exc}")
        conn.close()
        return 1

    print(f"\n共 {len(tables)} 张表:")
    ok = 0
    fail = 0
    for name in tables:
        try:
            n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            print(f"  OK  {name}: {n}")
            ok += 1
        except Exception as exc:
            print(f"  ERR {name}: {exc}")
            fail += 1
    conn.close()

    print(f"\n可读表 {ok}，失败 {fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
