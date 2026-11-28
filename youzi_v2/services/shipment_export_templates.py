"""保存运单 Excel 自定义导出模板。"""

import json
from collections import Counter
from typing import Any
from uuid import uuid4

from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from ..db.app_settings_table import TABLE_NAME, get_setting, set_setting
from ..db.connection import Database
from .shipment_excel import is_blank_export_field, shipment_export_fields, shipment_export_formats

_KEY_PREFIX = "shipment-export-template:"


def _load_template(raw: str) -> dict:
    template = json.loads(raw)
    legacy_lock = bool(template.pop("fieldsLocked", False))
    for column in template["columns"]:
        column.setdefault("locked", legacy_lock)
    return template


def list_channel_options(database: Database) -> list[dict]:
    with database.lock:
        rows = database.conn.execute("""
            WITH codes AS (
                SELECT code FROM channel_codes WHERE is_active = 1
                UNION
                SELECT DISTINCT TRIM(channel_code) FROM shipments WHERE TRIM(channel_code) != ''
            )
            SELECT codes.code, COALESCE(NULLIF(TRIM(c.name_zh), ''), codes.code) AS name
            FROM codes LEFT JOIN channel_codes c ON c.code = codes.code
            ORDER BY name, codes.code
        """).fetchall()
    return [dict(row) for row in rows]


def unmapped_channels(items: list[dict], mapping: dict[str, str]) -> list[dict]:
    counts = Counter()
    names = {}
    for item in items:
        code = (item.get("channelCode") or "").strip()
        if code and code not in mapping:
            counts[code] += 1
            names[code] = (item.get("channelNameZh") or "").strip() or code
    return [{"code": code, "name": names[code], "count": count} for code, count in counts.most_common()]


def list_templates(database: Database) -> list[dict]:
    with database.lock:
        rows = database.conn.execute(
            f"SELECT value FROM {TABLE_NAME} WHERE key GLOB ?",
            (_KEY_PREFIX + "*",),
        ).fetchall()
    return sorted((_load_template(row["value"]) for row in rows), key=lambda item: item["name"].casefold())


def get_template(database: Database, template_id: str) -> dict:
    with database.lock:
        raw = get_setting(database.conn, _KEY_PREFIX + template_id)
    if raw is None:
        raise KeyError(template_id)
    return _load_template(raw)


def save_template(
    database: Database, name: str, columns: list[dict[str, Any]], template_id: str | None = None,
    *, channel_mappings: list[dict[str, str]] | None = None,
) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("请填写模板名称")
    if name == "标准模板":
        raise ValueError("请为自定义模板使用其他名称")
    catalog = shipment_export_fields()
    fields = [column["field"] for column in columns]
    if not fields:
        raise ValueError("请至少添加一个导出列")
    if any(field not in catalog and not is_blank_export_field(field) for field in fields) or len(fields) != len(set(fields)):
        raise ValueError("导出字段不存在或重复，请检查所选字段")
    normalized = []
    for index, source in enumerate(columns):
        field = source["field"]
        label = source["label"].strip() or catalog.get(field)
        if not label:
            raise ValueError("请填写空白列的表头")
        column = {"field": field, "label": label}
        linked_to = source.get("linkedTo")
        if linked_to:
            next_column = columns[index + 1] if index + 1 < len(columns) else None
            if (field not in catalog or linked_to not in catalog or not next_column
                    or next_column["field"] != linked_to or next_column.get("linkedTo")):
                raise ValueError("请关联相邻的两个运单字段，每个字段只能关联一次")
            column["linkedTo"] = linked_to
        output_format = source.get("format")
        if output_format is not None:
            if output_format not in shipment_export_formats(field):
                raise ValueError(f"「{label}」不支持所选格式")
            column["format"] = output_format
        normalized.append(column)
    if any(ILLEGAL_CHARACTERS_RE.search(column["label"]) for column in normalized):
        raise ValueError("表头含有 Excel 不支持的字符")
    template = {"id": template_id or uuid4().hex, "name": name, "columns": normalized}
    with database.lock, database.conn:
        existing_locks = {}
        if template_id is not None:
            existing = get_template(database, template_id)
            if channel_mappings is None:
                channel_mappings = existing.get("channelMappings", [])
            existing_locks = {column["field"]: column["locked"] for column in existing["columns"]}
        for column, source in zip(normalized, columns):
            locked = source.get("locked")
            column["locked"] = existing_locks.get(column["field"], False) if locked is None else locked
        mappings = {}
        for entry in channel_mappings or []:
            code, value = entry["channelCode"].strip(), entry["value"].strip()
            if not code or not value:
                raise ValueError("请填写完整的渠道映射")
            if code in mappings:
                raise ValueError("同一个系统渠道只能映射一次")
            if ILLEGAL_CHARACTERS_RE.search(value):
                raise ValueError("客户渠道含有 Excel 不支持的字符")
            mappings[code] = value
        template["channelMappings"] = [{"channelCode": code, "value": value} for code, value in mappings.items()]
        if any(item["id"] != template_id and item["name"].casefold() == name.casefold()
               for item in list_templates(database)):
            raise ValueError("模板名称已存在，请使用其他名称")
        set_setting(database.conn, _KEY_PREFIX + template["id"], json.dumps(template, ensure_ascii=False))
    return template
