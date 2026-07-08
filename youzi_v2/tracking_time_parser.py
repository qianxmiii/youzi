"""内部轨迹文本解析：ETD/ETA/ATD/ATA/预计送仓/入仓/签收节点。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from .db.datetime_util import normalize_tracking_time
from .internal_tracking import is_internal_no_tracking_desc

_EXPLICIT_DATE_RE = re.compile(
    r"\b(ETD|ETA|ATD)\s*:?\s*(\d{1,2})[\/.-](\d{1,2})\b",
    re.IGNORECASE,
)
_ARRIVED_DEST_RE = re.compile(r"arriving\s+at\s+the\s+destination", re.IGNORECASE)
_GOODS_SHIPPED_RE = re.compile(r"the\s+goods\s+have\s+been\s+shipped", re.IGNORECASE)
_EXPECTED_DELIVERY_RE = re.compile(
    r"expected\s+to\s+be\s+delivered\s+on\s+(\d{1,2})[\/.-](\d{1,2})",
    re.IGNORECASE,
)
_SIGNED_FOR_RE = re.compile(r"signed\s+for", re.IGNORECASE)
_DELIVERED_NODE_RE = re.compile(r"\bDelivered\b")
_SIGNED_TRACK_EXCLUDE_RE = re.compile(
    r"delivered\s+goods,\s*waiting\s+for\s+unpacking",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InternalTrackRow:
    id: str
    tracking_time: str
    tracking_desc: str
    created_time: str


@dataclass(frozen=True)
class ParsedTimeCandidate:
    field_name: str
    candidate_value: str
    source_track_id: str
    source_track_time: str
    source_track_desc: str
    confidence: str = "high"


def normalize_track_text(desc: str) -> str:
    text = (desc or "").replace("：", ":")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_track_text_lower(desc: str) -> str:
    return normalize_track_text(desc).lower()


def parse_tracking_event_time(raw: str) -> datetime | None:
    normalized = normalize_tracking_time(raw)
    if not normalized:
        return None
    try:
        return datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _infer_year(month: int, day: int, reference: datetime | None, fallback: datetime | None) -> int:
    ref = reference or fallback
    if ref is None:
        ref = datetime.now()
    ref_date = ref.date()
    year = ref_date.year
    try:
        candidate = date(year, month, day)
    except ValueError:
        return year
    delta = (candidate - ref_date).days
    if delta < -180:
        year += 1
    elif delta > 180:
        year -= 1
    return year


def parse_month_day_to_datetime(
    month: int,
    day: int,
    *,
    reference: datetime | None,
    fallback: datetime | None,
) -> str:
    year = _infer_year(month, day, reference, fallback)
    return f"{year:04d}-{month:02d}-{day:02d} 00:00:00"


def is_signed_track(desc: str) -> bool:
    normalized_lower = normalize_track_text_lower(desc)
    if _SIGNED_TRACK_EXCLUDE_RE.search(normalized_lower):
        return False
    if _SIGNED_FOR_RE.search(normalized_lower):
        return True
    return _DELIVERED_NODE_RE.search(desc or "") is not None


def is_arrived_destination_track(desc: str) -> bool:
    return _ARRIVED_DEST_RE.search(normalize_track_text_lower(desc)) is not None


def is_goods_shipped_track(desc: str) -> bool:
    """内部轨迹「The goods have been shipped」节点（后可跟中文说明）。"""
    return _GOODS_SHIPPED_RE.search(normalize_track_text_lower(desc)) is not None


def _track_sort_key(track: InternalTrackRow) -> tuple[str, str, str]:
    event = normalize_tracking_time(track.tracking_time) or ""
    created = normalize_tracking_time(track.created_time) or ""
    return (event, created, track.id)


def _sort_tracks_newest_first(tracks: list[InternalTrackRow]) -> list[InternalTrackRow]:
    return sorted(tracks, key=_track_sort_key, reverse=True)


def _parse_explicit_field(
    tracks: list[InternalTrackRow],
    field: str,
    *,
    fallback_time: datetime | None,
) -> ParsedTimeCandidate | None:
    token = field.upper()
    for track in _sort_tracks_newest_first(tracks):
        normalized = normalize_track_text(track.tracking_desc)
        match = re.search(
            rf"\b{token}\s*:?\s*(\d{{4}})[/.-](\d{{1,2}})[/.-](\d{{1,2}})\b",
            normalized,
            re.IGNORECASE,
        )
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            try:
                date(year, month, day)
            except ValueError:
                pass
            else:
                return ParsedTimeCandidate(
                    field_name=field.lower(),
                    candidate_value=f"{year:04d}-{month:02d}-{day:02d} 00:00:00",
                    source_track_id=track.id,
                    source_track_time=normalize_tracking_time(track.tracking_time),
                    source_track_desc=track.tracking_desc or "",
                )
        match = re.search(
            rf"\b{token}\s*:?\s*(\d{{1,2}})[/.-](\d{{1,2}})\b",
            normalized,
            re.IGNORECASE,
        )
        if not match:
            continue
        month = int(match.group(1))
        day = int(match.group(2))
        ref = parse_tracking_event_time(track.tracking_time)
        value = parse_month_day_to_datetime(
            month,
            day,
            reference=ref,
            fallback=fallback_time,
        )
        return ParsedTimeCandidate(
            field_name=field.lower(),
            candidate_value=value,
            source_track_id=track.id,
            source_track_time=normalize_tracking_time(track.tracking_time),
            source_track_desc=track.tracking_desc or "",
        )
    return None


def _parse_expected_delivery(
    tracks: list[InternalTrackRow],
    *,
    fallback_time: datetime | None,
) -> ParsedTimeCandidate | None:
    for track in _sort_tracks_newest_first(tracks):
        normalized = normalize_track_text_lower(track.tracking_desc)
        match = _EXPECTED_DELIVERY_RE.search(normalized)
        if not match:
            continue
        month = int(match.group(1))
        day = int(match.group(2))
        ref = parse_tracking_event_time(track.tracking_time)
        value = parse_month_day_to_datetime(
            month,
            day,
            reference=ref,
            fallback=fallback_time,
        )
        return ParsedTimeCandidate(
            field_name="expected_delivery_time",
            candidate_value=value,
            source_track_id=track.id,
            source_track_time=normalize_tracking_time(track.tracking_time),
            source_track_desc=track.tracking_desc or "",
        )
    return None


def _sort_tracks_oldest_first(tracks: list[InternalTrackRow]) -> list[InternalTrackRow]:
    return sorted(tracks, key=_track_sort_key)


def _parse_event_time_field(
    tracks: list[InternalTrackRow],
    *,
    field_name: str,
    predicate: Callable[[str], bool],
    newest_first: bool = True,
) -> ParsedTimeCandidate | None:
    ordered = _sort_tracks_newest_first(tracks) if newest_first else _sort_tracks_oldest_first(tracks)
    for track in ordered:
        if not predicate(track.tracking_desc):
            continue
        event_time = normalize_tracking_time(track.tracking_time)
        if not event_time:
            return ParsedTimeCandidate(
                field_name=field_name,
                candidate_value="",
                source_track_id=track.id,
                source_track_time="",
                source_track_desc=track.tracking_desc or "",
                confidence="low",
            )
        return ParsedTimeCandidate(
            field_name=field_name,
            candidate_value=event_time,
            source_track_id=track.id,
            source_track_time=event_time,
            source_track_desc=track.tracking_desc or "",
        )
    return None


def _parse_atd(
    tracks: list[InternalTrackRow],
    *,
    fallback_time: datetime | None,
) -> ParsedTimeCandidate | None:
    explicit = _parse_explicit_field(tracks, "atd", fallback_time=fallback_time)
    if explicit is not None:
        return explicit
    return _parse_event_time_field(
        tracks,
        field_name="atd",
        predicate=is_goods_shipped_track,
        newest_first=False,
    )


def build_time_candidates(
    tracks: list[InternalTrackRow],
    *,
    shipment_created_time: str | None = None,
) -> dict[str, ParsedTimeCandidate | None]:
    fallback = parse_tracking_event_time(shipment_created_time or "")
    ordered = list(tracks)
    return {
        "etd": _parse_explicit_field(ordered, "etd", fallback_time=fallback),
        "eta": _parse_explicit_field(ordered, "eta", fallback_time=fallback),
        "atd": _parse_atd(ordered, fallback_time=fallback),
        "ata": _parse_event_time_field(
            ordered,
            field_name="ata",
            predicate=is_arrived_destination_track,
        ),
        "expected_delivery_time": _parse_expected_delivery(
            ordered,
            fallback_time=fallback,
        ),
        "warehouse_entry_time": _parse_event_time_field(
            ordered,
            field_name="warehouse_entry_time",
            predicate=is_internal_no_tracking_desc,
            newest_first=False,
        ),
        "signed_time": _parse_event_time_field(
            ordered,
            field_name="signed_time",
            predicate=is_signed_track,
        ),
    }


def tracks_from_rows(rows: list[dict[str, Any]]) -> list[InternalTrackRow]:
    out: list[InternalTrackRow] = []
    for row in rows:
        out.append(
            InternalTrackRow(
                id=str(row.get("id") or ""),
                tracking_time=str(row.get("tracking_time") or row.get("trackingTime") or ""),
                tracking_desc=str(row.get("tracking_desc") or row.get("trackingDesc") or ""),
                created_time=str(row.get("created_time") or row.get("createdTime") or ""),
            )
        )
    return out
