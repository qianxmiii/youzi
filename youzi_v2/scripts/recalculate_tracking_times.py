"""对有内部轨迹的运单批量重算时间字段（ETD/ETA/ATA/预计送仓/签收等）。

用法（仓库根目录）:
  python youzi_v2/scripts/recalculate_tracking_times.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from youzi_v2.db.connection import get_database
from youzi_v2.services.tracking_time_writeback import recalculate_all_with_internal_tracks

DB = Path(__file__).resolve().parents[1] / "data" / "youzi_v2.db"


def main() -> None:
    db = get_database(DB)
    result = recalculate_all_with_internal_tracks(db, log=print)
    print(result)


if __name__ == "__main__":
    main()
