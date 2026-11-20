"""运输关注的两档自然日阈值。"""
import json

from ..db.app_settings_table import get_setting, set_setting

KEY = "sla.attention.thresholds"
DEFAULTS = {
    "WAREHOUSE_NO_DEPARTURE": (7, 10),
    "ARRIVAL_NO_DELIVERY": (7, 12),
    "DEST_WAREHOUSE_NO_DISPATCH": (5, 7),
    "INTERNAL_TRACKING_STALE": (7, 10),
}


def load_thresholds(database):
    with database.lock:
        raw = get_setting(database.conn, KEY)
    stored = json.loads(raw) if raw else {}
    return {key: tuple(stored.get(key, default)) for key, default in DEFAULTS.items()}


def save_thresholds(database, values):
    if set(values) != set(DEFAULTS):
        raise ValueError("请提供完整的四项关注规则")
    for pair in values.values():
        if (not isinstance(pair, list) or len(pair) != 2
                or any(type(v) is not int or not 0 <= v <= 365 for v in pair)
                or pair[0] >= pair[1]):
            raise ValueError("阈值须为 0—365 的整数，主要关注天数须大于次要关注")
    with database.lock:
        set_setting(database.conn, KEY, json.dumps(values))
        database.conn.commit()
    return load_thresholds(database)
