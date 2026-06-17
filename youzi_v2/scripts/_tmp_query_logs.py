import json
from pathlib import Path

sn = "DPSECO260611093"
logs_dir = Path(__file__).resolve().parents[1] / "logs"

for path in sorted(logs_dir.glob("tracking-sync-*.log")):
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if sn not in line:
                continue
            if "返回报文" in line or "承运商轨迹" in line or "轨迹同步" in line:
                print(f"[{path.name}] {line.rstrip()}")
