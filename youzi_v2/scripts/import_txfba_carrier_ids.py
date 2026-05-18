"""批量写入腾信服务商单号（carrier_id）。用法: python -m youzi_v2.scripts.import_txfba_carrier_ids"""

from __future__ import annotations

from pathlib import Path

from youzi_v2.db.connection import get_database
from youzi_v2.db.datetime_util import now_str
from youzi_v2.db.shipments_table import TABLE_NAME

# 原单号 -> 服务商单号 (billNo)
MAPPINGS: list[tuple[str, str]] = [
    ("DPSECO260505105", "ICBU00001060983"),
    ("DPSECO260407062", "ICBU00001019022"),
    ("DPSECO260407067", "ICBU00001024232"),
    ("DPSECO260407070", "ICBU00001024233"),
    ("DPSECO260303019", "ICBU00000971657"),
    ("DPSECO260410002", "ICBU00001031786"),
    ("DPSECO260407061", "ICBU00001019024"),
    ("DPSECO260423015", "ICBU00001042932"),
    ("DPSECO260416086", "ICBU00001035096"),
    ("DPSECO260425044", "ICBU00001053995"),
    ("DPSECO260409089", "ICBU00001024843"),
    ("DPSECO260423018", "ICBU00001045347"),
    ("DPSECO260423012", "ICBU00001042936"),
    ("DPSECO260411074", "ICBU00001031372"),
    ("DPSECO260411073", "ICBU00001031366"),
    ("DPSECO260411076", "ICBU00001031368"),
    ("DPSECO260411075", "ICBU00001031370"),
    ("DPSECO260417122", "ICBU00001036120"),
    ("DPSECO260323012", "ICBU00001002728"),
]


def main() -> None:
    db_path = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"
    db = get_database(db_path)
    ts = now_str()
    updated = 0
    missing: list[str] = []

    with db.lock:
        conn = db.conn
        for sn, cid in MAPPINGS:
            cur = conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET carrier_id = ?, updated_time = ?
                WHERE shipment_no = ?
                """,
                (cid, ts, sn),
            )
            if cur.rowcount:
                updated += 1
            else:
                missing.append(sn)
        conn.commit()

    print(f"已更新 {updated} 条 carrier_id")
    if missing:
        print(f"库中未找到运单号 ({len(missing)}): {', '.join(missing)}")


if __name__ == "__main__":
    main()
