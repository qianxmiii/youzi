"""诊断运单 SLA 扫描为何未生成预警（已运输天数 / 截止日 / 风险等级）。"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from youzi_v2.db.channel_sla_rules_repository import ChannelSlaRulesRepository
from youzi_v2.db.connection import Database
from youzi_v2.db.exception_duration import duration_seconds, format_duration
from youzi_v2.db.shipment_sla import (
    ACTIVE_STATUSES,
    compute_arrival_no_delivery_context,
    compute_due_context,
    compute_risk_level,
    compute_warehouse_no_departure_context,
    days_since_start,
    is_delivered,
    match_channel_rule,
    parse_date,
)


def _db_path() -> Path:
    env = (os.environ.get("YOUZI_DB_PATH") or "").strip()
    if env:
        return Path(env)
    return ROOT / "data" / "youzi_v2.db"


def _scan_skip_reason(row: dict, rule: dict | None, today: date, rules_by_channel: dict) -> str | None:
    if is_delivered(row):
        dt = (row.get("delivered_time") or "").strip()
        sc = (row.get("status_code") or "").strip()
        if dt:
            return f"系统判定已签收（delivered_time={dt}）"
        return f"系统判定已签收（status_code={sc}）"
    if not rule:
        ch = (row.get("channel_code") or "").strip() or "（空）"
        carrier = (row.get("carrier_code") or "").strip()
        rules = rules_by_channel.get(ch) or []
        if rules and carrier:
            return (
                f"渠道 {ch} 有规则，但承运商「{carrier}」未匹配到默认规则"
                f"（仅有承运商子规则时须配置 carrier_code 为空 的默认规则）"
            )
        return f"渠道 {ch} 无启用的运输时效规则（请在渠道管理 → 时效配置）"
    ctx = compute_due_context(row, rule)
    if not ctx:
        atd = (row.get("atd") or "").strip()
        if not atd:
            return "缺少 ATD，无法计算截止日（当前规则起算字段为 ATD，预计送仓不参与扫描）"
        est = int(rule.get("estimatedDays") or 0)
        if est <= 0:
            return f"渠道规则预估天数无效（estimatedDays={est}）"
        sf = (rule.get("startField") or "ATD").strip().upper()
        if sf != "ATD":
            return f"规则起算字段为 {sf}，当前仅支持 ATD"
        return "无法计算截止日（未知原因）"
    due_day = parse_date(ctx["dueDate"])
    if not due_day:
        return "截止日解析失败"
    warning_days = int(ctx["warningDays"])
    risk = compute_risk_level(
        today=today,
        due_day=due_day,
        warning_days=warning_days,
        severe_overdue_days=int(ctx["severeOverdueDays"]),
    )
    if not risk:
        warning_start = due_day - timedelta(days=max(0, warning_days))
        return (
            f"尚未进入预警窗口：today({today}) < 提醒起始日({warning_start})，"
            f"截止日 {due_day}，预估 {ctx.get('ruleId') and rule.get('estimatedDays')} 天"
        )
    return None


def main() -> None:
    sn = (sys.argv[1] if len(sys.argv) > 1 else "DPSECO260410137").strip()
    db_path = _db_path()
    if not db_path.is_file():
        print(f"数据库不存在: {db_path}")
        print("可设置环境变量 YOUZI_DB_PATH 指向实际 SQLite 文件")
        return

    db = Database(db_path)
    conn = db.conn
    row = conn.execute("SELECT * FROM shipments WHERE shipment_no = ?", (sn,)).fetchone()
    if row is None:
        print(f"运单不存在: {sn}")
        return
    d = dict(row)
    today = date.today()
    print(f"数据库: {db_path}")
    print(f"today: {today.isoformat()}")
    print("=== 运单关键字段 ===")
    for k in (
        "atd",
        "etd",
        "eta",
        "warehouse_entry_time",
        "expected_delivery_time",
        "delivered_time",
        "status_code",
        "exception_code",
        "exception_opened_time",
        "channel_code",
        "carrier_code",
    ):
        print(f"  {k}: {d.get(k) or '—'}")

    atd = d.get("atd") or ""
    atd_day = parse_date(atd)
    if atd_day:
        days = days_since_start(atd, today=today)
        print(f"\n已运输天数（未签收）= today - ATD = {days} 天")
    else:
        print("\n无 ATD")

    opened = (d.get("exception_opened_time") or "").strip()
    if opened:
        secs = duration_seconds(opened, None)
        label = format_duration(secs, opened_time=opened)
        print(f"异常天数 = {label}")

    rules_repo = ChannelSlaRulesRepository(db)
    rules_by_channel = rules_repo.list_enabled_grouped()
    channel = (d.get("channel_code") or "").strip()
    carrier = (d.get("carrier_code") or "").strip()
    rule = match_channel_rule(
        rules_by_channel,
        channel_code=channel,
        carrier_code=carrier,
    )

    print("\n=== SLA 扫描模拟 ===")
    skip = _scan_skip_reason(d, rule, today, rules_by_channel)
    if skip:
        print(f"  结果: 跳过，不生成 DELIVERY_TIME 预警")
        print(f"  原因: {skip}")
    else:
        ctx = compute_due_context(d, rule)
        due_day = parse_date(ctx["dueDate"]) if ctx else None
        risk = (
            compute_risk_level(
                today=today,
                due_day=due_day,
                warning_days=int(ctx["warningDays"]),
                severe_overdue_days=int(ctx["severeOverdueDays"]),
            )
            if ctx and due_day
            else None
        )
        print("  结果: 应生成/更新预警")
        print(f"  匹配规则: 渠道={channel} 承运商={carrier or '（默认）'}")
        print(f"  estimatedDays: {rule.get('estimatedDays') if rule else '—'}")
        if ctx:
            print(f"  dueDate: {ctx.get('dueDate')}")
            warn = parse_date(ctx.get("warningDate"))
            if warn:
                print(f"  warningDate: {warn}（today >= 此日才进入预警窗口）")
            print(f"  riskLevel: {risk}")

    wh = compute_warehouse_no_departure_context(d, today=today)
    ar = compute_arrival_no_delivery_context(d, today=today)
    print("\n=== 阶段卡点预警 ===")
    print(f"  入库未开船: {'可生成' if wh else '不适用'}")
    print(f"  到港未送仓: {'可生成' if ar else '不适用'}")

    alerts = conn.execute(
        "SELECT * FROM shipment_sla_alerts WHERE shipment_no = ? ORDER BY created_time DESC",
        (sn,),
    ).fetchall()
    if alerts:
        print("\n=== 已有 SLA 预警记录 ===")
        for a in alerts:
            ad = dict(a)
            st = ad.get("status") or ""
            in_todo = st in ACTIVE_STATUSES and not is_delivered(d)
            print(
                f"  id={ad.get('id')[:8]}… status={st} risk={ad.get('risk_level')} "
                f"due={ad.get('due_date')} {'→ 默认列表可见' if in_todo else '→ 默认列表不可见'}"
            )
    else:
        print("\n=== 已有 SLA 预警记录 ===")
        print("  （无）")


if __name__ == "__main__":
    main()
