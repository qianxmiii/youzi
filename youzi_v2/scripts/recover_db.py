"""从损坏的 youzi_v2.db 尽量恢复数据到新库。"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "youzi_v2.db"


def recover(src: Path, dst: Path) -> dict[str, int | str]:
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    dst_conn.execute("PRAGMA journal_mode=WAL")
    stats: dict[str, int | str] = {}

    tables = [
        r[0]
        for r in src_conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
    ]
    stats["tables_total"] = len(tables)

    copied = 0
    rows_total = 0
    failed: list[str] = []

    for name in tables:
        try:
            ddl_row = src_conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
                (name,),
            ).fetchone()
            if not ddl_row or not ddl_row[0]:
                failed.append(f"{name}: 无 DDL")
                continue
            dst_conn.execute(ddl_row[0])
            cols = [r[1] for r in src_conn.execute(f'PRAGMA table_info("{name}")')]
            placeholders = ", ".join("?" * len(cols))
            col_sql = ", ".join(f'"{c}"' for c in cols)
            insert_sql = f'INSERT INTO "{name}" ({col_sql}) VALUES ({placeholders})'
            batch: list[tuple] = []
            for row in src_conn.execute(f'SELECT * FROM "{name}"'):
                batch.append(tuple(row))
                if len(batch) >= 500:
                    dst_conn.executemany(insert_sql, batch)
                    rows_total += len(batch)
                    batch.clear()
            if batch:
                dst_conn.executemany(insert_sql, batch)
                rows_total += len(batch)
            dst_conn.commit()
            copied += 1
            print(f"  OK  {name}: {dst_conn.execute(f'SELECT COUNT(*) FROM \"{name}\"').fetchone()[0]} 行")
        except Exception as exc:
            failed.append(f"{name}: {exc}")
            print(f"  ERR {name}: {exc}")
            dst_conn.rollback()
            try:
                dst_conn.execute(f'DROP TABLE IF EXISTS "{name}"')
                dst_conn.commit()
            except Exception:
                pass

    src_conn.close()
    dst_conn.execute("VACUUM")
    dst_conn.commit()
    dst_conn.close()

    stats["tables_copied"] = copied
    stats["rows_total"] = rows_total
    stats["failed"] = "; ".join(failed) if failed else ""
    return stats


def main() -> int:
    if not DB.exists():
        print(f"源库不存在: {DB}")
        return 1

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = DB.with_name(f"youzi_v2.recovered-{ts}.db")
    print(f"源库: {DB}")
    print(f"目标: {dst}")
    stats = recover(DB, dst)
    print("\n恢复结果:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(
        "\n下一步:\n"
        "  1. 停止后端\n"
        f"  2. 将 {DB.name} 重命名为 youzi_v2.db.broken-{ts}\n"
        f"  3. 将 {dst.name} 重命名为 {DB.name}\n"
        "  4. 删除 youzi_v2.db-wal / youzi_v2.db-shm（若存在）\n"
        "  5. 重启后端"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
