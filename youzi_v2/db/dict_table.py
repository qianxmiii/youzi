"""
通用字典表 sys_dict：按 dict_type 分组，code 为键。
时间列统一 YYYY-MM-DD HH:mm:ss。
"""

from __future__ import annotations

import sqlite3

from .datetime_util import now_str

TABLE_NAME = "sys_dict"

# (code, value 中文名, desc 英文名)
_COUNTRY_CODE_SEEDS: list[tuple[str, str, str]] = [
    ("US", "美国", "United States"),
    ("GB", "英国", "United Kingdom"),
    ("DE", "德国", "Germany"),
    ("FR", "法国", "France"),
    ("CA", "加拿大", "Canada"),
    ("AU", "澳大利亚", "Australia"),
    ("JP", "日本", "Japan"),
    ("KR", "韩国", "South Korea"),
    ("SG", "新加坡", "Singapore"),
    ("MY", "马来西亚", "Malaysia"),
    ("TH", "泰国", "Thailand"),
    ("VN", "越南", "Vietnam"),
    ("PH", "菲律宾", "Philippines"),
    ("ID", "印度尼西亚", "Indonesia"),
    ("IN", "印度", "India"),
    ("AE", "阿联酋", "United Arab Emirates"),
    ("SA", "沙特阿拉伯", "Saudi Arabia"),
    ("MX", "墨西哥", "Mexico"),
    ("BR", "巴西", "Brazil"),
    ("IT", "意大利", "Italy"),
    ("ES", "西班牙", "Spain"),
    ("NL", "荷兰", "Netherlands"),
    ("BE", "比利时", "Belgium"),
    ("PL", "波兰", "Poland"),
    ("CZ", "捷克", "Czech Republic"),
    ("AT", "奥地利", "Austria"),
    ("CH", "瑞士", "Switzerland"),
    ("SE", "瑞典", "Sweden"),
    ("NO", "挪威", "Norway"),
    ("DK", "丹麦", "Denmark"),
    ("FI", "芬兰", "Finland"),
    ("IE", "爱尔兰", "Ireland"),
    ("PT", "葡萄牙", "Portugal"),
    ("NZ", "新西兰", "New Zealand"),
    ("HK", "中国香港", "Hong Kong"),
    ("TW", "中国台湾", "Taiwan"),
    ("MO", "中国澳门", "Macao"),
    ("CN", "中国", "China"),
]

_ADDRESS_TYPE_SEEDS: list[tuple[str, str, str]] = [
    ("AMZ", "亚马逊", "Amazon FBA"),
    ("WFS", "沃尔玛", "Walmart WFS"),
    ("3PL", "商私地址", "Third-party / private address"),
]

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    dict_type TEXT NOT NULL,
    code TEXT NOT NULL,
    value TEXT NOT NULL DEFAULT '',
    desc TEXT NOT NULL DEFAULT '',
    created_time TEXT NOT NULL,
    updated_time TEXT NOT NULL,
    PRIMARY KEY (dict_type, code)
)
"""

_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_dict_type ON {TABLE_NAME}(dict_type)",
]


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_SQL)
    for stmt in _INDEXES:
        conn.execute(stmt)


def _seed_dict_type(
    conn: sqlite3.Connection,
    dict_type: str,
    rows: list[tuple[str, str, str]],
) -> None:
    """按 code 补缺：已有同类型同 code 则跳过，便于新增种子后自动补齐。"""
    now = now_str()
    for code, value, desc in rows:
        exists = conn.execute(
            f"SELECT 1 FROM {TABLE_NAME} WHERE dict_type = ? AND code = ?",
            (dict_type, code),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                dict_type, code, value, desc, created_time, updated_time
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dict_type, code, value, desc, now, now),
        )


def seed_if_empty(conn: sqlite3.Connection) -> None:
    """按 dict_type 分别灌入初始字典；已有该类型数据则跳过。"""
    _seed_dict_type(conn, "country_code", _COUNTRY_CODE_SEEDS)
    _seed_dict_type(conn, "address_type", _ADDRESS_TYPE_SEEDS)
