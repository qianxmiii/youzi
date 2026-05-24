"""承运商轨迹条目（含可选 vendor_event_id，用于 P2 稳定去重）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence


@dataclass(frozen=True, slots=True)
class CarrierTrackingLogEntry:
    tracking_time: str
    tracking_desc: str
    vendor_event_id: str | None = None

    @classmethod
    def from_row(
        cls,
        tracking_time: str,
        tracking_desc: str,
        vendor_event_id: str | None = None,
    ) -> CarrierTrackingLogEntry:
        t = (tracking_time or "").strip()
        d = (tracking_desc or "").strip()
        eid = (vendor_event_id or "").strip() or None
        return cls(t, d, eid)

    @classmethod
    def coerce(cls, item: Any) -> CarrierTrackingLogEntry | None:
        if isinstance(item, CarrierTrackingLogEntry):
            return item if item.tracking_time else None
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            eid = None
            if len(item) >= 3 and item[2] is not None:
                eid = str(item[2]).strip() or None
            return cls.from_row(str(item[0]), str(item[1] or ""), eid)
        return None

    def match_key(self) -> str:
        if self.vendor_event_id:
            return f"id:{self.vendor_event_id}"
        return f"legacy:{self.tracking_time}\0{self.tracking_desc}"


def coerce_carrier_logs(
    logs: Sequence[Any],
) -> list[CarrierTrackingLogEntry]:
    out: list[CarrierTrackingLogEntry] = []
    for item in logs:
        entry = CarrierTrackingLogEntry.coerce(item)
        if entry and entry.tracking_time:
            out.append(entry)
    return out


def sort_logs_desc(entries: list[CarrierTrackingLogEntry]) -> list[CarrierTrackingLogEntry]:
    seen: set[str] = set()
    unique: list[CarrierTrackingLogEntry] = []
    for entry in entries:
        key = entry.match_key()
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return sorted(unique, key=lambda e: e.tracking_time, reverse=True)


def latest_from_logs(
    logs: Sequence[Any],
) -> tuple[str, str]:
    entries = coerce_carrier_logs(logs)
    if not entries:
        return "", ""
    sorted_entries = sort_logs_desc(entries)
    return sorted_entries[0].tracking_time, sorted_entries[0].tracking_desc


def carrier_logs_unchanged(
    existing: Iterable[CarrierTrackingLogEntry],
    api: Iterable[CarrierTrackingLogEntry],
) -> bool:
    ex_map = {e.match_key(): e for e in existing}
    api_map = {e.match_key(): e for e in api}
    if set(ex_map) != set(api_map):
        return False
    for key, api_entry in api_map.items():
        old = ex_map[key]
        if (
            old.tracking_time != api_entry.tracking_time
            or old.tracking_desc != api_entry.tracking_desc
        ):
            return False
    return True
