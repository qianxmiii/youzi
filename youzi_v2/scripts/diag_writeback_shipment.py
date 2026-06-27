"""诊断单票轨迹时间回写。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from youzi_v2.db.connection import Database
from youzi_v2.services.tracking_time_writeback import recalculate_for_shipment
from youzi_v2.tracking_time_parser import build_time_candidates, is_signed_track, tracks_from_rows

SN = (sys.argv[1] if len(sys.argv) > 1 else "DPSECO260508120").strip()


def main() -> None:
    db = Database(ROOT / "data" / "youzi_v2.db")
    conn = db.conn
    row = conn.execute(
        """
        SELECT id, shipment_no, etd, eta, atd, ata,
               expected_delivery_time, delivered_time, status_code,
               latest_tracking_time, latest_tracking_desc, created_time, updated_time
        FROM shipments WHERE shipment_no = ?
        """,
        (SN,),
    ).fetchone()
    if not row:
        similar = conn.execute(
            "SELECT shipment_no FROM shipments WHERE shipment_no LIKE ? LIMIT 10",
            (f"%{SN[-8:]}%",),
        ).fetchall()
        print(f"运单 {SN} 不存在")
        if similar:
            print("相似运单:", [r[0] for r in similar])
        return

    sid = row["id"]
    print("=== 运单 ===")
    for k in row.keys():
        print(f"  {k}: {row[k]}")

    logs = conn.execute(
        """
        SELECT id, tracking_time, tracking_desc, created_time
        FROM internal_tracking_logs
        WHERE shipment_no = ?
        ORDER BY datetime(tracking_time) ASC, datetime(created_time) ASC
        """,
        (SN,),
    ).fetchall()
    print(f"\n=== 内部轨迹 ({len(logs)} 条) ===")
    for r in logs:
        desc = (r["tracking_desc"] or "").replace("\n", " ")
        signed = " [签收]" if is_signed_track(desc) else ""
        print(f"  {r['tracking_time']} | {desc[:100]}{signed}")

    tracks = tracks_from_rows([dict(r) for r in logs])
    candidates = build_time_candidates(
        tracks, shipment_created_time=str(row["created_time"] or "")
    )
    print("\n=== 解析候选 ===")
    for name, c in candidates.items():
        if c is None:
            print(f"  {name}: (无)")
        else:
            print(f"  {name}: {c.candidate_value} <- {c.source_track_desc[:80]}")

    pending = conn.execute(
        """
        SELECT * FROM shipment_tracking_time_candidates c
        WHERE c.shipment_id = ?
        """,
        (sid,),
    ).fetchall()
    print(f"\n=== 候选表 ({len(pending)} 条) ===")
    for r in pending:
        print(
            f"  {r['field_name']}: {r['candidate_value']} "
            f"status={r['review_status']} applied={r['applied']} reason={r['review_reason']}"
        )

    print("\n=== 试跑 recalculate ===")
    result = recalculate_for_shipment(db, shipment_id=sid)
    print(result)

    row2 = conn.execute(
        """
        SELECT etd, eta, atd, ata, expected_delivery_time, delivered_time, status_code
        FROM shipments WHERE id = ?
        """,
        (sid,),
    ).fetchone()
    print("\n=== 重算后运单时间 ===")
    for k in row2.keys():
        print(f"  {k}: {row2[k]}")


if __name__ == "__main__":
    main()
