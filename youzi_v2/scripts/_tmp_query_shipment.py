import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

sn = "DPSECO260611093"
rows = cur.execute(
    "SELECT shipment_no, carrier_code, carrier_id, tracking_number, "
    "latest_carrier_time, latest_carrier_desc, status_code "
    "FROM shipments WHERE shipment_no = ? OR shipment_no LIKE ?",
    (sn, f"%{sn[-9:]}%"),
).fetchall()
print("shipments:", len(rows))
for r in rows:
    print(dict(r))

if rows:
    actual = rows[0]["shipment_no"]
    logs = cur.execute(
        "SELECT * FROM carrier_tracking_logs WHERE shipment_no = ? "
        "ORDER BY tracking_time DESC LIMIT 20",
        (actual,),
    ).fetchall()
    print("\ncarrier_tracking_logs:", len(logs))
    for r in logs:
        print(dict(r))

# search sync logs
logs_dir = Path(__file__).resolve().parents[1] / "logs"
for path in sorted(logs_dir.glob("tracking-sync-*.log")):
    hits = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if sn in line or "260611093" in line:
                hits.append((i, line.rstrip()))
    if hits:
        print(f"\n=== {path.name} ({len(hits)} hits) ===")
        for ln, text in hits:
            print(f"L{ln}: {text}")
