"""诊断 WY 承运商轨迹 API。用法: python youzi_v2/scripts/diag_wy_carrier.py [运单号]"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.services.carrier_vendors import (
    _wy_api_url,
    _wy_post_track,
    fetch_wy_batch_for_rows,
    load_vendors_config,
    parse_wy_track_group,
)

CONFIG = ROOT / "config" / "config.json"
DEFAULT_SN = "DPSECO260529171"


def main() -> None:
    sn = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SN).strip()
    vendors = load_vendors_config(CONFIG)
    vendor = next((v for v in vendors if (v.get("platform") or "").strip().lower() == "wy"), None)
    if vendor is None:
        print("config 中未找到 platform=wy 的 vendor")
        sys.exit(1)

    print("=== WY 配置 ===")
    print("vendor.id:", vendor.get("id"))
    print("apiUrl:", _wy_api_url(vendor))

    print("\n=== 轨迹查询 ===", sn)
    groups, err = _wy_post_track([sn], vendor, timeout=30)
    print("error:", err or "-")
    print("groups:", len(groups))
    if groups:
        logs, carrier_order_no, _ = parse_wy_track_group(groups[0])
        print("systemOrderNumber(承运商单号):", carrier_order_no or "-")
        print("轨迹节点数:", len(logs))

    print("\n=== fetch_wy_batch_for_rows ===")
    out = fetch_wy_batch_for_rows(
        [{"shipment_no": sn, "carrier_id": "", "carrier_code": str(vendor.get("id") or "")}],
        vendor,
        log=print,
    )
    logs, ferr, carrier_order_no, _ = out.get(sn, ([], "无返回", None, None))
    print("fetch error:", ferr or "-")
    print("fetch carrier order no:", carrier_order_no or "-")
    print("fetch logs:", len(logs))


if __name__ == "__main__":
    main()
