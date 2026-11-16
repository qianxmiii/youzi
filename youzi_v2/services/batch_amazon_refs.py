"""批量补录：逐票冲突检查、保存、推送。"""
import re
from .dps_update_amz import preview_amz_push, push_amz_update, record_amz_push_result


def parse_lines(text):
    result = []
    seen = set()
    for number, line in enumerate(text.replace("\\", "\n").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"[\s=＝]+", line)
        error = "" if len(parts) == 3 else "格式错误，应为运单号 货件号 预约号"
        no = parts[0]
        if no in seen:
            error = "重复运单号，请合并后重试"
        seen.add(no)
        result.append({"line": number, "shipmentNo": no, "shipmentId": parts[1] if len(parts)>1 else "", "referenceId": parts[2] if len(parts)>2 else "", "error": error})
    # 重复票的所有行均跳过，避免先更新后发现冲突。
    counts = {}
    for row in result:
        counts[row["shipmentNo"]] = counts.get(row["shipmentNo"], 0) + 1
    for row in result:
        if counts[row["shipmentNo"]] > 1:
            row["error"] = "重复运单号，请合并后重试"
    return result


def process_row(repo, config_path, item, *, force=False, task_id=""):
    if item.get("error"):
        return {**item, "status": "skipped", "message": item["error"]}
    row = repo.get_by_shipment_no(item["shipmentNo"])
    if not row:
        return {**item, "status": "skipped", "message": "运单不存在"}
    old = (row.get("customerShipmentId") or "").strip()
    new = item["shipmentId"].strip()
    conflict = old not in ("", "1", new)
    if conflict and not force:
        return {**item, "status": "conflict", "existingShipmentId": old, "message": "货件号不一致，未保存、未推送"}
    if new in ("", "1") or item["referenceId"].strip() in ("", "1"):
        return {**item, "status": "skipped", "message": "货件号或预约号无效"}
    database = repo._database
    preview = preview_amz_push(database, row)
    origin = (row.get("amzPushOriginPort") or preview.get("originPort") or "").strip()
    dest = (row.get("amzPushDestPort") or preview.get("destinationPort") or "").strip()
    event_id = None
    if task_id:
        from ..db.task_history import record_event
        event_id = record_event(database, task_id, item["shipmentNo"],
            {"shipmentId":old,"referenceId":row.get("amazonRefId") or "","originPort":row.get("amzPushOriginPort") or "","destinationPort":row.get("amzPushDestPort") or ""},
            {"shipmentId":new,"referenceId":item["referenceId"].strip(),"originPort":origin,"destinationPort":dest,"force":force})
    saved = repo.update_row(row["id"], {"customer_shipment_id": new, "amazon_ref_id": item["referenceId"].strip(), "amz_push_origin_port": origin, "amz_push_dest_port": dest})
    push = push_amz_update(database, repo, config_path, saved)
    record_amz_push_result(database, saved, push)
    if event_id is not None:
        from ..db.task_history import finish_event
        finish_event(database, event_id, push)
    return {**item, "status": "success" if push["ok"] else "saved", "existingShipmentId": old if conflict else "", "message": ("已强制覆盖货件号并保存。" if conflict else "已保存。") + push["message"]}
