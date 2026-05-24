"""拉取单票运单内部/承运商原始报文并写入 youzi_v2/temp/。用法:
  python youzi_v2/scripts/dump_tracking_response.py DPSECO260417120
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.services.carrier_vendors import (
    detect_platform,
    fetch_tracking_one,
    load_vendors_config,
    _fetch_topda_batch,
)
from youzi_v2.services.logistics_tracking import load_logistics_config, query_logistics_batch
from youzi_v2.services.sync_log import make_sync_logger

CONFIG = ROOT / "config" / "config.json"
OUT_DIR = Path(__file__).resolve().parents[1] / "temp"


def main() -> None:
    sn = (sys.argv[1] if len(sys.argv) > 1 else "DPSECO260417120").strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _, out_log = make_sync_logger()

    out: dict[str, object] = {"shipmentNo": sn}

    cfg = load_logistics_config(CONFIG)
    data, err = query_logistics_batch(
        [{"tracking_number": sn, "customer": "", "channel": "", "carrier": ""}],
        cfg["base_url"],
    )
    out["internal"] = {"error": err, "items": data}
    out_log(f"[dump] {sn} 内部返回 {len(data)} 条" + (f" 错误={err}" if err else ""))
    for item in data:
        out_log(f"[dump] {sn} 内部报文 {json.dumps(item, ensure_ascii=False)}")

    vendors = load_vendors_config(CONFIG)
    out["carriers"] = {}
    for vendor in vendors:
        name = (vendor.get("name") or "").strip()
        if not name:
            continue
        platform = detect_platform(vendor)
        try:
            if platform == "topda":
                batch_out = _fetch_topda_batch([sn], vendor, timeout=30, log=out_log)
                logs, err, cid, tn = batch_out.get(sn, ([], None, None, None))
                out["carriers"][name] = {
                    "platform": platform,
                    "error": err,
                    "carrierId": cid,
                    "trackingNumber": tn,
                    "logCount": len(logs),
                }
            else:
                logs, err, cid, tn = fetch_tracking_one(sn, vendor)
                out["carriers"][name] = {
                    "platform": platform,
                    "error": err,
                    "carrierId": cid,
                    "trackingNumber": tn,
                    "logCount": len(logs),
                }
                out_log(f"[dump] {sn} {name}/{platform} 轨迹 {len(logs)} 条")
        except Exception as exc:
            out["carriers"][name] = {"error": str(exc)}
            out_log(f"[dump] {sn} {name} 失败: {exc}")

    path = OUT_DIR / f"tracking_{sn}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_log(f"[dump] 已写入 {path}")


if __name__ == "__main__":
    main()
