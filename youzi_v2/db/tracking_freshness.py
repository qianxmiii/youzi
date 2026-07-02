"""轨迹新鲜度：内部/承运商分别按自然日划分（今日 / 三日内含今日 / 更早 / 无）。"""

from __future__ import annotations

from ..internal_tracking import INTERNAL_WAREHOUSE_PLACEHOLDER

FRESHNESS_BUCKETS = frozenset({"today", "within3d", "older", "none"})

# 承运商无轨迹统计/筛选：整柜不走 API 轨迹，不计入「无轨迹」
FCL_CARRIER_NAME_ZH = "整柜"

# 承新于内：承运时间须晚于内部至少该分钟数（双方均有有效内部轨迹时）
CARRIER_AHEAD_MIN_MINUTES = 1


def validate_freshness(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    v = str(value).strip().lower()
    if v not in FRESHNESS_BUCKETS:
        raise ValueError(f"freshness 须为 today / within3d / older / none，收到: {value}")
    return v


def _internal_effective_sql(alias: str = "s") -> str:
    p = f"{alias}." if alias else ""
    return f"""(
      {p}latest_tracking_time IS NOT NULL AND TRIM({p}latest_tracking_time) != ''
      AND {p}latest_tracking_desc IS NOT NULL AND TRIM({p}latest_tracking_desc) != ''
      AND TRIM({p}latest_tracking_desc) != ?
    )"""


def _carrier_effective_sql(alias: str = "s") -> str:
    p = f"{alias}." if alias else ""
    return f"""(
      {p}latest_carrier_time IS NOT NULL AND TRIM({p}latest_carrier_time) != ''
    )"""


def _fcl_carrier_match_sql(alias: str = "s") -> str:
    """运单承运商为整柜（FCL，无 API 轨迹）。"""
    p = f"{alias}." if alias else ""
    return f"""(
      TRIM(COALESCE({p}carrier_code, '')) = ? COLLATE NOCASE
      OR EXISTS (
        SELECT 1 FROM carrier_codes crc
        WHERE TRIM(COALESCE({p}carrier_code, '')) != ''
          AND (crc.code = {p}carrier_code OR crc.carrier_id = {p}carrier_code)
          AND TRIM(crc.name_zh) = ? COLLATE NOCASE
      )
    )"""


def carrier_no_tracking_eligible_sql(alias: str = "s") -> tuple[str, list]:
    """承运商「无轨迹」筛选/统计的排除条件（排除整柜）。"""
    return f"NOT {_fcl_carrier_match_sql(alias)}", [FCL_CARRIER_NAME_ZH, FCL_CARRIER_NAME_ZH]


def internal_freshness_sql(bucket: str, alias: str = "s") -> tuple[str, list]:
    """返回 (SQL 片段, 参数)。"""
    eff = _internal_effective_sql(alias)
    p = f"{alias}." if alias else ""
    ph = INTERNAL_WAREHOUSE_PLACEHOLDER
    if bucket == "none":
        return f"NOT {eff}", [ph]
    if bucket == "today":
        return (
            f"{eff} AND date({p}latest_tracking_time) = date('now', 'localtime')",
            [ph],
        )
    if bucket == "within3d":
        return (
            f"{eff} AND date({p}latest_tracking_time) >= date('now', 'localtime', '-2 days')",
            [ph],
        )
    if bucket == "older":
        return (
            f"{eff} AND date({p}latest_tracking_time) < date('now', 'localtime', '-2 days')",
            [ph],
        )
    raise ValueError(bucket)


def carrier_freshness_sql(bucket: str, alias: str = "s") -> tuple[str, list]:
    eff = _carrier_effective_sql(alias)
    p = f"{alias}." if alias else ""
    if bucket == "none":
        exclude_frag, exclude_params = carrier_no_tracking_eligible_sql(alias)
        return f"NOT {eff} AND {exclude_frag}", exclude_params
    if bucket == "today":
        return f"{eff} AND date({p}latest_carrier_time) = date('now', 'localtime')", []
    if bucket == "within3d":
        return (
            f"{eff} AND date({p}latest_carrier_time) >= date('now', 'localtime', '-2 days')",
            [],
        )
    if bucket == "older":
        return (
            f"{eff} AND date({p}latest_carrier_time) < date('now', 'localtime', '-2 days')",
            [],
        )
    raise ValueError(bucket)


def carrier_ahead_of_internal_sql(alias: str = "s") -> tuple[str, list]:
    """承运商最新节点时间晚于内部至少 CARRIER_AHEAD_MIN_MINUTES 分钟，或内部无有效轨迹但承运有。"""
    ce = _carrier_effective_sql(alias)
    ie = _internal_effective_sql(alias)
    p = f"{alias}." if alias else ""
    ph = INTERNAL_WAREHOUSE_PLACEHOLDER
    offset = f"+{CARRIER_AHEAD_MIN_MINUTES} minutes"
    frag = f"""(
      {ce}
      AND (
        NOT {ie}
        OR datetime({p}latest_carrier_time) > datetime({p}latest_tracking_time, '{offset}')
      )
    )"""
    return frag, [ph]


def freshness_stats_sql() -> tuple[str, list]:
    """全库四档运单计数（内部、承运商各四列）+ 承新于内运单数。"""
    ie = _internal_effective_sql("s")
    ce = _carrier_effective_sql("s")
    ahead = carrier_ahead_of_internal_sql("s")[0]
    no_carrier_exclude, _ = carrier_no_tracking_eligible_sql("s")
    ph = INTERNAL_WAREHOUSE_PLACEHOLDER
    sql = f"""
    SELECT
      SUM(CASE WHEN {ie}
          AND date(s.latest_tracking_time) = date('now', 'localtime') THEN 1 ELSE 0 END) AS internal_today,
      SUM(CASE WHEN {ie}
          AND date(s.latest_tracking_time) >= date('now', 'localtime', '-2 days') THEN 1 ELSE 0 END) AS internal_within3d,
      SUM(CASE WHEN {ie}
          AND date(s.latest_tracking_time) < date('now', 'localtime', '-2 days') THEN 1 ELSE 0 END) AS internal_older,
      SUM(CASE WHEN NOT {ie} THEN 1 ELSE 0 END) AS internal_none,
      SUM(CASE WHEN {ce}
          AND date(s.latest_carrier_time) = date('now', 'localtime') THEN 1 ELSE 0 END) AS carrier_today,
      SUM(CASE WHEN {ce}
          AND date(s.latest_carrier_time) >= date('now', 'localtime', '-2 days') THEN 1 ELSE 0 END) AS carrier_within3d,
      SUM(CASE WHEN {ce}
          AND date(s.latest_carrier_time) < date('now', 'localtime', '-2 days') THEN 1 ELSE 0 END) AS carrier_older,
      SUM(CASE WHEN NOT {ce} AND {no_carrier_exclude} THEN 1 ELSE 0 END) AS carrier_none,
      SUM(CASE WHEN {ahead} THEN 1 ELSE 0 END) AS carrier_ahead_of_internal
    FROM shipments s
    """
    fcl = FCL_CARRIER_NAME_ZH
    params = [ph, ph, ph, ph, fcl, fcl, ph]
    assert len(params) == sql.count("?")
    return sql, params
