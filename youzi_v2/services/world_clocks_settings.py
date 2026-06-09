"""顶栏世界时间：app_settings 全局配置。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from ..db.app_settings_table import get_setting, set_setting
from ..db.connection import Database

KEY_ENABLED = "header.world_clocks.enabled"
KEY_USE_24H = "header.world_clocks.use_24h"
KEY_ZONES = "header.world_clocks.zones"

MAX_ZONES = 6

DEFAULT_ZONES: list[dict[str, str]] = [
    {"tz": "Asia/Shanghai", "label": "北京"},
    {"tz": "America/Los_Angeles", "label": "洛杉矶"},
    {"tz": "America/New_York", "label": "纽约"},
    {"tz": "Europe/London", "label": "伦敦"},
]


@dataclass(frozen=True)
class WorldClockZoneRow:
    tz: str
    label: str


@dataclass(frozen=True)
class WorldClocksConfig:
    enabled: bool
    use24h: bool
    zones: list[WorldClockZoneRow]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "use24h": self.use24h,
            "zones": [{"tz": z.tz, "label": z.label} for z in self.zones],
        }


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _is_valid_tz(tz: str) -> bool:
    """校验 IANA 时区；勿依赖 available_timezones()（Windows 无 tzdata 时其为空）。"""
    name = (tz or "").strip()
    if not name:
        return False
    try:
        ZoneInfo(name)
        return True
    except Exception:
        return False


def _normalize_zones(raw: Any) -> list[WorldClockZoneRow]:
    if not isinstance(raw, list):
        return []
    out: list[WorldClockZoneRow] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        tz = str(item.get("tz") or "").strip()
        label = str(item.get("label") or "").strip()
        if not tz or not label or not _is_valid_tz(tz) or tz in seen:
            continue
        seen.add(tz)
        out.append(WorldClockZoneRow(tz=tz, label=label[:32]))
        if len(out) >= MAX_ZONES:
            break
    return out


def _load_zones_json(conn) -> list[WorldClockZoneRow]:
    raw = get_setting(conn, KEY_ZONES)
    if not raw or not str(raw).strip():
        return _normalize_zones(DEFAULT_ZONES)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _normalize_zones(DEFAULT_ZONES)
    zones = _normalize_zones(parsed)
    return zones or _normalize_zones(DEFAULT_ZONES)


def ensure_world_clocks_defaults(conn) -> None:
    if get_setting(conn, KEY_ENABLED) is None:
        set_setting(conn, KEY_ENABLED, "1")
    if get_setting(conn, KEY_USE_24H) is None:
        set_setting(conn, KEY_USE_24H, "1")
    if get_setting(conn, KEY_ZONES) is None:
        set_setting(conn, KEY_ZONES, json.dumps(DEFAULT_ZONES, ensure_ascii=False))


def get_world_clocks_settings(database: Database) -> WorldClocksConfig:
    with database.lock:
        ensure_world_clocks_defaults(database.conn)
        enabled = _parse_bool(get_setting(database.conn, KEY_ENABLED), True)
        use24h = _parse_bool(get_setting(database.conn, KEY_USE_24H), True)
        zones = _load_zones_json(database.conn)
    return WorldClocksConfig(enabled=enabled, use24h=use24h, zones=zones)


def save_world_clocks_settings(
    database: Database,
    *,
    enabled: bool,
    use24h: bool,
    zones: list[dict[str, str]],
) -> WorldClocksConfig:
    normalized = _normalize_zones(zones)
    if enabled and not normalized:
        raise ValueError("启用世界时间时至少保留一个有效时区")
    with database.lock:
        ensure_world_clocks_defaults(database.conn)
        set_setting(database.conn, KEY_ENABLED, "1" if enabled else "0")
        set_setting(database.conn, KEY_USE_24H, "1" if use24h else "0")
        set_setting(
            database.conn,
            KEY_ZONES,
            json.dumps(
                [{"tz": z.tz, "label": z.label} for z in normalized],
                ensure_ascii=False,
            ),
        )
        database.conn.commit()
    return get_world_clocks_settings(database)
