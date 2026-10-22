"""亚马逊推送港口规则：amz_update_port_rules。"""

from __future__ import annotations

import sqlite3
from typing import Any

from .datetime_util import now_str

TABLE_NAME = "amz_update_port_rules"

# code, name_zh, transport_mode, country_code, leg, port_code, rule_kind, match_text, is_default, sort_order
AMZ_PORT_RULE_SEEDS: list[tuple[str, str, str, str, str, str, str, str, int, int]] = [
    ("AIR_ORIGIN_SZX", "空运起运", "AIR", "CN", "ORIGIN", "SZX", "DEFAULT", "", 1, 10),
    ("AIR_DEST_US_LAX", "洛杉矶", "AIR", "US", "DESTINATION", "LAX", "OPTION", "", 1, 10),
    ("AIR_DEST_US_ORD", "芝加哥", "AIR", "US", "DESTINATION", "ORD", "OPTION", "", 0, 20),
    ("AIR_DEST_US_JFK", "纽约", "AIR", "US", "DESTINATION", "JFK", "OPTION", "", 0, 30),
    ("AIR_DEST_CA_YVR", "温哥华", "AIR", "CA", "DESTINATION", "YVR", "OPTION", "", 1, 10),
    ("AIR_DEST_CA_YYZ", "多伦多", "AIR", "CA", "DESTINATION", "YYZ", "OPTION", "", 0, 20),
    ("AIR_DEST_GB_LHR", "伦敦", "AIR", "GB", "DESTINATION", "LHR", "DEFAULT", "", 1, 10),
    ("AIR_DEST_DE_FRA", "法兰克福", "AIR", "DE", "DESTINATION", "FRA", "DEFAULT", "", 1, 10),
    ("AIR_DEST_ES_FRA", "法兰克福", "AIR", "ES", "DESTINATION", "FRA", "DEFAULT", "", 1, 10),
    ("AIR_DEST_FR_FRA", "法兰克福", "AIR", "FR", "DESTINATION", "FRA", "DEFAULT", "", 1, 10),
    ("AIR_DEST_IT_FRA", "法兰克福", "AIR", "IT", "DESTINATION", "FRA", "DEFAULT", "", 1, 10),
    ("AIR_DEST_NL_FRA", "法兰克福", "AIR", "NL", "DESTINATION", "FRA", "DEFAULT", "", 1, 10),
    ("SEA_ORIGIN_SZ", "深圳仓", "SEA", "CN", "ORIGIN", "CNSNZ", "ORIGIN_EXACT", "深圳仓", 0, 10),
    ("SEA_ORIGIN_YW", "义乌仓", "SEA", "CN", "ORIGIN", "CNNBO", "ORIGIN_EXACT", "义乌仓", 0, 20),
    ("SEA_DEST_US_LAX", "洛杉矶", "SEA", "US", "DESTINATION", "USLAX", "DEFAULT", "", 1, 10),
    ("SEA_DEST_US_SAV", "萨瓦纳", "SEA", "US", "DESTINATION", "USSAV", "DEST_KEYWORD", "萨瓦纳", 0, 20),
    ("SEA_DEST_US_NYC", "纽约", "SEA", "US", "DESTINATION", "USNYC", "DEST_KEYWORD", "纽约", 0, 30),
    ("SEA_DEST_US_OAK", "奥克兰", "SEA", "US", "DESTINATION", "USOAK", "DEST_KEYWORD", "奥克兰", 0, 40),
    ("SEA_DEST_US_SEA", "西雅图", "SEA", "US", "DESTINATION", "USSEA", "DEST_KEYWORD", "西雅图", 0, 50),
    ("SEA_DEST_US_HOU", "休斯顿", "SEA", "US", "DESTINATION", "USHOU", "DEST_KEYWORD", "休斯顿", 0, 60),
    ("SEA_DEST_CA", "温哥华", "SEA", "CA", "DESTINATION", "CAVAN", "DEFAULT", "", 1, 10),
    ("SEA_DEST_GB", "费利克斯托", "SEA", "GB", "DESTINATION", "GBFXT", "DEFAULT", "", 1, 10),
    ("SEA_DEST_DE", "鹿特丹", "SEA", "DE", "DESTINATION", "NLRTM", "DEFAULT", "", 1, 10),
    ("SEA_DEST_ES", "鹿特丹", "SEA", "ES", "DESTINATION", "NLRTM", "DEFAULT", "", 1, 10),
    ("SEA_DEST_FR", "鹿特丹", "SEA", "FR", "DESTINATION", "NLRTM", "DEFAULT", "", 1, 10),
    ("SEA_DEST_IT", "鹿特丹", "SEA", "IT", "DESTINATION", "NLRTM", "DEFAULT", "", 1, 10),
    ("SEA_DEST_NL", "鹿特丹", "SEA", "NL", "DESTINATION", "NLRTM", "DEFAULT", "", 1, 10),
]

RULE_KINDS = frozenset({"DEFAULT", "OPTION", "ORIGIN_EXACT", "DEST_KEYWORD"})
TRANSPORT_MODES = frozenset({"AIR", "SEA"})
LEGS = frozenset({"ORIGIN", "DESTINATION"})


def sync_amz_update_port_rules(conn: sqlite3.Connection) -> None:
    """补齐种子行，不覆盖已有编码（便于后台改港口码）。"""
    now = now_str()
    for (
        code,
        name_zh,
        mode,
        country,
        leg,
        port_code,
        kind,
        match_text,
        is_default,
        sort_order,
    ) in AMZ_PORT_RULE_SEEDS:
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME} (
                code, name_zh, name_en, transport_mode, country_code, leg, port_code,
                rule_kind, match_text, is_default, sort_order, is_active,
                created_time, updated_time
            ) VALUES (?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                code,
                name_zh,
                mode,
                country,
                leg,
                port_code,
                kind,
                match_text,
                is_default,
                sort_order,
                now,
                now,
            ),
        )


def list_active_amz_port_rules(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        f"""
        SELECT code, name_zh, transport_mode, country_code, leg, port_code,
               rule_kind, match_text, is_default, sort_order
        FROM {TABLE_NAME}
        WHERE is_active = 1
        ORDER BY sort_order, code
        """
    ).fetchall()
    return [
        {
            "code": row["code"],
            "nameZh": row["name_zh"] or "",
            "transportMode": (row["transport_mode"] or "").strip().upper(),
            "countryCode": (row["country_code"] or "").strip().upper(),
            "leg": (row["leg"] or "").strip().upper(),
            "portCode": (row["port_code"] or "").strip().upper(),
            "ruleKind": (row["rule_kind"] or "").strip().upper(),
            "matchText": (row["match_text"] or "").strip(),
            "isDefault": bool(row["is_default"]),
            "sortOrder": int(row["sort_order"] or 0),
        }
        for row in rows
    ]
