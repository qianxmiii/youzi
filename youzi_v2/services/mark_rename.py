"""唛头下载文件名：按所选字段顺序与分隔符拼接。"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Literal

# 顺序即对话框默认展示顺序
MARK_RENAME_FIELDS: tuple[tuple[str, str], ...] = (
    ("shipmentNo", "运单号"),
    ("addressCode", "派送仓库（空则邮编）"),
    ("ctns", "件数"),
    ("customer", "客户"),
    ("customerNo", "客户单号"),
    ("refShipmentNo", "关联单号"),
    ("customerShipmentId", "货件号"),
    ("channelNameZh", "渠道"),
    ("zipcode", "邮编"),
    ("originWarehouseCode", "收货仓"),
    ("countryCode", "国家"),
)

MARK_RENAME_FIELD_KEYS = {key for key, _label in MARK_RENAME_FIELDS}
DEFAULT_MARK_RENAME_FIELDS = ("shipmentNo", "addressCode", "ctns")
DEFAULT_MARK_RENAME_SEPARATOR = "-"
DEFAULT_MARK_RENAME_COUNTRY_LANG: Literal["en", "zh"] = "en"
_SEPARATOR_MAX = 8
_STEM_MAX = 180
_INVALID_FS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_WHITESPACE = re.compile(r"\s+")

CountryLang = Literal["en", "zh"]
CountryLabelMap = dict[str, dict[str, str]]


def normalize_mark_rename_separator(raw: str | None) -> str:
    if raw is None:
        return DEFAULT_MARK_RENAME_SEPARATOR
    sep = str(raw)
    if sep == "":
        raise ValueError("请选择分隔符")
    if len(sep) > _SEPARATOR_MAX:
        raise ValueError("分隔符过长")
    if _INVALID_FS.search(sep):
        raise ValueError('分隔符不能包含 \\ / : * ? " < > |')
    return sep


def normalize_mark_rename_fields(raw: list[str] | None) -> list[str]:
    if not raw:
        raise ValueError("请至少选择一个重命名字段")
    fields: list[str] = []
    seen: set[str] = set()
    for item in raw:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        if key not in MARK_RENAME_FIELD_KEYS:
            raise ValueError(f"不支持的重命名字段：{key}")
        seen.add(key)
        fields.append(key)
    if not fields:
        raise ValueError("请至少选择一个重命名字段")
    if len(fields) > len(MARK_RENAME_FIELDS):
        raise ValueError("重命名字段过多")
    return fields


def normalize_mark_rename_country_lang(raw: str | None) -> CountryLang:
    key = (raw or DEFAULT_MARK_RENAME_COUNTRY_LANG).strip().lower()
    if key in ("zh", "cn", "zh-cn", "zh_cn", "chinese"):
        return "zh"
    return "en"


def load_country_label_map(conn: sqlite3.Connection) -> CountryLabelMap:
    """sys_dict.country_code：value=中文，desc=英文。"""
    rows = conn.execute(
        """
        SELECT code, value, desc FROM sys_dict
        WHERE dict_type = 'country_code'
          AND code IS NOT NULL AND TRIM(code) != ''
        """
    ).fetchall()
    out: CountryLabelMap = {}
    for row in rows:
        code = str(row["code"] or "").strip().upper()
        if not code:
            continue
        out[code] = {
            "zh": str(row["value"] or "").strip(),
            "en": str(row["desc"] or "").strip(),
        }
    return out


def _field_text(
    row: dict[str, Any],
    key: str,
    *,
    country_lang: CountryLang = DEFAULT_MARK_RENAME_COUNTRY_LANG,
    country_labels: CountryLabelMap | None = None,
) -> str:
    if key == "ctns":
        value = row.get("ctns")
        if value is None or value == "":
            return ""
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(value).strip()
    if key == "channelNameZh":
        return str(row.get("channelNameZh") or row.get("channelCode") or "").strip()
    if key == "addressCode":
        # 默认规则：派送仓库为空则用邮编
        text = str(row.get("addressCode") or "").strip()
        if text:
            return text
        return str(row.get("zipcode") or "").strip()
    if key == "countryCode":
        code = str(row.get("countryCode") or "").strip()
        if not code:
            return ""
        # 英文：国家码缩写（AU / US）；中文：字典中文名
        if country_lang != "zh":
            return code.upper()
        labels = (country_labels or {}).get(code.upper()) or (country_labels or {}).get(code)
        if labels:
            return labels.get("zh") or code.upper()
        return code.upper()
    return str(row.get(key) or "").strip()


def normalize_mark_rename_folder(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = str(raw).strip()
    if not key:
        return None
    if key not in MARK_RENAME_FIELD_KEYS:
        raise ValueError(f"不支持的文件夹字段：{key}")
    return key


def build_mark_rename_folder(
    row: dict[str, Any],
    key: str,
    *,
    country_lang: CountryLang = DEFAULT_MARK_RENAME_COUNTRY_LANG,
    country_labels: CountryLabelMap | None = None,
) -> str:
    """相同字段值进同一文件夹；空值归入「未填写」。"""
    return (
        sanitize_mark_rename_part(
            _field_text(
                row,
                key,
                country_lang=country_lang,
                country_labels=country_labels,
            )
        )
        or "未填写"
    )


def sanitize_mark_rename_part(value: str) -> str:
    text = _INVALID_FS.sub("", str(value or "").strip())
    return _WHITESPACE.sub("", text)


def build_mark_rename_stem(
    row: dict[str, Any],
    fields: list[str],
    separator: str,
    *,
    country_lang: CountryLang = DEFAULT_MARK_RENAME_COUNTRY_LANG,
    country_labels: CountryLabelMap | None = None,
) -> str:
    parts = [
        part
        for key in fields
        if (
            part := sanitize_mark_rename_part(
                _field_text(
                    row,
                    key,
                    country_lang=country_lang,
                    country_labels=country_labels,
                )
            )
        )
    ]
    stem = separator.join(parts)
    if not stem:
        stem = sanitize_mark_rename_part(str(row.get("shipmentNo") or "")) or "唛头"
    if len(stem) > _STEM_MAX:
        stem = stem[:_STEM_MAX].rstrip(" .-_")
    return stem or "唛头"


def unique_mark_filename(stem: str, extension: str, used: set[str]) -> str:
    ext = extension if str(extension).startswith(".") else f".{extension}" if extension else ".pdf"
    name = f"{stem}{ext}"
    if name not in used:
        used.add(name)
        return name
    n = 2
    while True:
        candidate = f"{stem}_{n}{ext}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        n += 1
