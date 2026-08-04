"""按运单号批量重拉 DPS，回填 customer_no / ref_shipment_no。

映射规则（见 shipment_dps_mapper）：
  customer_no     ← internalOrderNum
  ref_shipment_no ← assOrderNumber

查不到 / 失败的运单不改动（无启发式）。

用法（仓库根目录）:
  python youzi_v2/scripts/migrate_ref_shipment_no.py
  python youzi_v2/scripts/migrate_ref_shipment_no.py --limit 100
  python youzi_v2/scripts/migrate_ref_shipment_no.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.db.connection import get_database
from youzi_v2.db.shipments_repository import ShipmentsRepository
from youzi_v2.db.shipments_table import ensure_schema as ensure_shipments_schema
from youzi_v2.services.shipment_dps_sync import run_shipment_dps_sync_by_order

DB = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"
CONFIG = ROOT / "config" / "config.json"
_CHUNK = 200


def _list_all_shipment_nos(repo: ShipmentsRepository, limit: int | None) -> list[str]:
    with repo._database.lock:
        sql = "SELECT shipment_no FROM shipments ORDER BY datetime(updated_time) DESC"
        if limit is not None and limit > 0:
            rows = repo._conn.execute(f"{sql} LIMIT ?", (limit,)).fetchall()
        else:
            rows = repo._conn.execute(sql).fetchall()
    return [str(r["shipment_no"]).strip() for r in rows if r["shipment_no"]]


def main() -> None:
    parser = argparse.ArgumentParser(description="DPS 回填关联单号 / 客户订单号")
    parser.add_argument("--limit", type=int, default=0, help="最多处理运单数（0=全部）")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅列出将处理的运单数，不调用 DPS",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        help="每批之间休眠秒数，降低 DPS 限流风险",
    )
    args = parser.parse_args()

    if not CONFIG.is_file():
        print(f"缺少配置: {CONFIG}")
        sys.exit(1)

    db = get_database(DB)
    ensure_shipments_schema(db.conn)
    db.conn.commit()
    repo = ShipmentsRepository(db)

    limit = args.limit if args.limit > 0 else None
    nos = _list_all_shipment_nos(repo, limit)
    print(f"待处理运单: {len(nos)}（chunk={_CHUNK}）")
    if args.dry_run:
        print("dry-run，退出")
        return

    totals = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "failed": 0,
        "notFound": 0,
        "errors": 0,
    }

    for i in range(0, len(nos), _CHUNK):
        chunk = nos[i : i + _CHUNK]
        print(f"\n=== 批次 {i // _CHUNK + 1}: {len(chunk)} 单 ===")
        result = run_shipment_dps_sync_by_order(repo, CONFIG, chunk, log=print)
        if result.get("skipped"):
            print("跳过:", result.get("reason") or result.get("error"))
            if result.get("error") or result.get("reason"):
                totals["errors"] += 1
            continue
        for key in ("created", "updated", "unchanged", "failed", "notFound"):
            totals[key] += int(result.get(key) or 0)
        if args.sleep > 0 and i + _CHUNK < len(nos):
            time.sleep(args.sleep)

    print("\n=== 合计 ===")
    for k, v in totals.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
