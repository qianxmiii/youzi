"""按 DPS 提单号归集运单，将航次及清关进度展示在提单层。"""

from collections import defaultdict
from datetime import datetime

from ..db.datetime_util import DATETIME_FMT, normalize_tracking_time, now_str
from ..db.internal_tracking_logs_table import LATEST_INTERNAL_LOG_DESC, LATEST_INTERNAL_LOG_JOIN, LATEST_INTERNAL_LOG_TIME
from ..db.shipment_route_status import map_dps_route_status
from ..db.shipment_sla import sql_sla_delivered
from .port_code_resolve import PortCodeResolver

_BILL_FILTER = "TRIM(COALESCE(s.bill_of_lading_no, '')) <> ''"
_BILL_KEY = "UPPER(TRIM(s.bill_of_lading_no))"
_CUSTOMS_STATES = {
    "EXPORT_CUSTOMS_EXCEPTION": ("export", "inspection"),
    "EXPORT_CUSTOMS_RELEASE": ("export", "released"),
    "IMPORT_CUSTOMS_EXCEPTION": ("import", "inspection"),
    "IMPORT_CUSTOMS_RELEASE": ("import", "released"),
}


def record_customs_nodes(database, shipment_no, nodes):
    values = []
    for node in nodes:
        mapping = _CUSTOMS_STATES.get(map_dps_route_status(node.get("status")))
        if mapping is None:
            continue
        time = normalize_tracking_time(str(node.get("nodeTime") or ""))
        try:
            time = datetime.strptime(time, DATETIME_FMT).strftime(DATETIME_FMT)
        except ValueError:
            continue
        phase, status = mapping
        values.append((shipment_no, phase, status, time, str(node.get("nodeDesc") or "").strip()))
    if not values:
        return
    with database.lock, database.conn:
        database.conn.executemany("""
            INSERT INTO shipment_customs_nodes (shipment_no, phase, status, node_time, description)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(shipment_no, phase) DO UPDATE SET
                status=excluded.status, node_time=excluded.node_time, description=excluded.description
            WHERE excluded.node_time > shipment_customs_nodes.node_time
               OR (excluded.node_time = shipment_customs_nodes.node_time AND excluded.status = 'inspection')
        """, values)


def _customs_evidence(rows, phase, known):
    evidence = []
    for row in rows:
        shipment_no = row["shipment_no"]
        item = known.get((shipment_no, phase))
        if item:
            evidence.append(dict(shipmentNo=shipment_no, status=item["status"], time=item["node_time"], description=item["description"]))
        route_code = (row["route_status"] or "").strip().upper()
        exception_code = (row["exception_code"] or "").strip().upper()
        current = [(exception_code, normalize_tracking_time(row["exception_opened_time"]) or None)]
        if route_code != exception_code:
            current.append((route_code, None))
        for code, time in current:
            parsed = _CUSTOMS_STATES.get(code)
            if not parsed or parsed[0] != phase:
                continue
            # 保留原始节点的时间和描述，同时允许当前异常重新打开已放行的阶段。
            if item and (item["status"] != "released" or parsed[1] != "inspection"):
                continue
            evidence.append(dict(shipmentNo=shipment_no, status=parsed[1], time=time, description=""))
    latest = max(evidence, key=lambda item: (item["time"] or "", item["status"] == "inspection"), default=None)
    if latest and latest["status"] == "released":
        # 无节点时间的查验，无法确认发生在这次放行之前。
        return next((item for item in evidence if item["status"] == "inspection" and not item["time"]), latest)
    return latest


def _members(rows, known):
    groups = defaultdict(list)
    codes = {(row["container_no"] or "").strip().upper() for row in rows} - {""}
    inferred = next(iter(codes)) if len(codes) == 1 else ""
    for row in rows:
        key = (row["container_no"] or "").strip().upper() or inferred
        groups[key].append(row)

    containers = []
    for code, members in sorted(groups.items(), key=lambda pair: (not pair[0], pair[0])):
        customs = {phase: _customs_evidence(members, phase, known) for phase in ("export", "import")}
        evidence_nos = {item["shipmentNo"] for item in customs.values() if item and item["status"] == "inspection"}
        members.sort(key=lambda row: (row["shipment_no"] not in evidence_nos, row["shipment_no"]))
        containers.append(dict(
            containerNo=code or None, unassigned=not code and len(codes) > 1,
            shipmentCount=len(members), customs=customs,
            shipments=[dict(
                id=row["id"], shipmentNo=row["shipment_no"], customer=row["customer"],
                channelCode=row["channel_code"], channelNameZh=row["channel_name_zh"],
                addressCode=row["address_code"], routeStatus=row["route_status"],
                vesselVoyage=row["vessel_voyage"], latestTrackingTime=row["tracking_time"],
                latestTrackingDesc=row["tracking_desc"],
            ) for row in members],
        ))
    return containers


def _read(database, bill_no=None, *, voyage_id=None, port_call_id=None):
    binding_filters = []
    binding_params = []
    if bill_no:
        binding_filters.append("b.bill_no = ?")
        binding_params.append(bill_no)
    if voyage_id:
        binding_filters.append("b.voyage_id = ?")
        binding_params.append(voyage_id)
    if port_call_id:
        binding_filters.append("? IN (b.origin_call_id, b.destination_call_id)")
        binding_params.append(port_call_id)
    binding_where = " WHERE " + " AND ".join(binding_filters) if binding_filters else ""
    where = _BILL_FILTER
    params = []
    if bill_no:
        where += f" AND {_BILL_KEY} = ?"
        params.append(bill_no)
    if voyage_id or port_call_id:
        where += f" AND {_BILL_KEY} IN (SELECT b.bill_no FROM bill_of_lading_bindings b{binding_where})"
        params.extend(binding_params)
    with database.lock:
        rows = database.conn.execute(f"""
            SELECT s.id, s.shipment_no, {_BILL_KEY} AS bill_no, s.container_no,
                   s.country_code, s.customer, s.address_code, s.route_status, s.exception_code,
                   s.channel_code, NULLIF(TRIM(cc.name_zh), '') AS channel_name_zh,
                   s.origin_port_code, s.destination_port_code,
                   s.exception_opened_time, s.vessel_voyage, {sql_sla_delivered("s.route_status")} AS is_delivered,
                   {LATEST_INTERNAL_LOG_TIME} AS tracking_time, {LATEST_INTERNAL_LOG_DESC} AS tracking_desc
            FROM shipments s
            LEFT JOIN channel_codes cc ON cc.code = s.channel_code
            {LATEST_INTERNAL_LOG_JOIN}
            WHERE {where}
            ORDER BY s.shipment_no
        """, params).fetchall()
        nodes = database.conn.execute(f"""
            SELECT n.* FROM shipment_customs_nodes n
            JOIN shipments s ON s.shipment_no = n.shipment_no
            WHERE {where}
        """, params).fetchall()
        bindings = database.conn.execute("""
            SELECT b.*, v.vessel_voyage,
                   origin.port_name AS origin_port, origin.sequence AS origin_sequence, origin.etd, origin.atd,
                   destination.port_name AS destination_port, destination.sequence AS destination_sequence,
                   destination.eta, destination.ata
            FROM bill_of_lading_bindings b
            LEFT JOIN vessel_voyages v ON v.id=b.voyage_id
            LEFT JOIN voyage_port_calls origin ON origin.id=b.origin_call_id AND origin.voyage_id=b.voyage_id
            LEFT JOIN voyage_port_calls destination ON destination.id=b.destination_call_id AND destination.voyage_id=b.voyage_id
        """ + binding_where, binding_params).fetchall()
    return rows, {(r["shipment_no"], r["phase"]): r for r in nodes}, {r["bill_no"]: r for r in bindings}


def _binding(row):
    if row is None:
        return None
    return dict(
        voyageId=row["voyage_id"], vesselVoyage=row["vessel_voyage"],
        originCallId=row["origin_call_id"], destinationCallId=row["destination_call_id"],
        originPort=row["origin_port"], destinationPort=row["destination_port"],
        etd=row["etd"], atd=row["atd"], eta=row["eta"], ata=row["ata"],
        needsReview=not (
            row["vessel_voyage"] and row["origin_port"] and row["destination_port"]
            and row["origin_sequence"] < row["destination_sequence"]
        ),
    )


def _summary(bill_no, rows, known, binding):
    containers = _members(rows, known)
    countries = sorted({row["country_code"].strip().upper() for row in rows if (row["country_code"] or "").strip()})
    has_inspection = any(
        event and event["status"] == "inspection"
        for container in containers for event in container["customs"].values()
    )
    state = (
        "unbound" if binding is None else "review" if binding["needsReview"]
        else "arrived" if binding["ata"] else "departed" if binding["atd"] else "planned"
    )
    return dict(billNo=bill_no, shipmentCount=len(rows), deliveredCount=sum(row["is_delivered"] for row in rows),
                countries=countries, binding=binding,
                state=state, hasInspection=has_inspection, containers=containers)


def _port_choices(members, binding, resolver):
    def resolve(raw):
        name = (raw or "").strip()
        match = resolver.resolve(name)
        if match:
            code = match["code"].strip().upper()
            label = match["nameZh"] or match["nameEn"]
            return code, f"{label}（{code}）" if label else code
        return name.upper(), name

    bound = binding or {}
    return {
        (resolve(bound.get("originPort") or row["origin_port_code"]),
         resolve(bound.get("destinationPort") or row["destination_port_code"]))
        for row in members
    }


def _format_port_options(options):
    return [dict(value=value, label=label) for value, label in sorted(options.items(), key=lambda item: item[1].casefold())]


def list_bills(database, country, search, state, limit, offset, *, voyage_id=None, port_call_id=None,
               origin_port="", destination_port="", delivery_scope="all"):
    rows, known, bindings = _read(database, voyage_id=voyage_id, port_call_id=port_call_id)
    with database.lock:
        resolver = PortCodeResolver(database.conn)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["bill_no"]].append(row)
    items = []
    origins = {}
    destinations = {}
    query = search.strip().lower()
    for bill_no, members in grouped.items():
        if country and not any((row["country_code"] or "").strip().upper() == country for row in members):
            continue
        binding = _binding(bindings.get(bill_no))
        pairs = _port_choices(members, binding, resolver)
        bill_origins = dict(origin for origin, _ in sorted(pairs) if origin[0])
        bill_destinations = dict(destination for _, destination in sorted(pairs) if destination[0])
        origins.update(bill_origins)
        destinations.update(bill_destinations)
        if (origin_port or destination_port) and not any(
            (not origin_port or origin[0] == origin_port) and (not destination_port or destination[0] == destination_port)
            for origin, destination in pairs
        ):
            continue
        item = _summary(bill_no, members, known, binding)
        item["originPorts"] = sorted(bill_origins.values())
        item["destinationPorts"] = sorted(bill_destinations.values())
        if state == "inspection" and not item["hasInspection"]:
            continue
        all_delivered = item["deliveredCount"] == item["shipmentCount"]
        if (state == "delivered" or delivery_scope == "delivered") and not all_delivered:
            continue
        if delivery_scope == "open" and all_delivered:
            continue
        if state not in ("", "inspection", "delivered") and state != item["state"]:
            continue
        containers = item["containers"]
        if query and not any(query in value.lower() for value in (
            bill_no, (item["binding"] or {}).get("vesselVoyage") or "",
            *(container["containerNo"] or "" for container in containers),
        )):
            continue
        for container in containers:
            container.pop("shipments")
        items.append(item)
    items.sort(key=lambda item: (not item["hasInspection"], item["state"] not in ("unbound", "review"), item["billNo"]))
    return dict(items=items[offset:offset + limit], total=len(items),
                portOptions=dict(origins=_format_port_options(origins), destinations=_format_port_options(destinations)))


def get_bill(database, bill_no):
    rows, known, bindings = _read(database, bill_no)
    return _summary(bill_no, rows, known, _binding(bindings.get(bill_no))) if rows else None


def save_binding(database, bill_no, voyage_id, origin_call_id, destination_call_id):
    with database.lock, database.conn:
        if database.conn.execute(f"SELECT 1 FROM shipments s WHERE {_BILL_FILTER} AND {_BILL_KEY}=? LIMIT 1", (bill_no,)).fetchone() is None:
            return False
        if voyage_id is None:
            database.conn.execute("DELETE FROM bill_of_lading_bindings WHERE bill_no=?", (bill_no,))
            return True
        ports = {row["id"]: row["sequence"] for row in database.conn.execute("""
            SELECT id, sequence FROM voyage_port_calls WHERE voyage_id=? AND id IN (?, ?)
        """, (voyage_id, origin_call_id, destination_call_id))}
        if len(ports) != 2 or ports[origin_call_id] >= ports[destination_call_id]:
            raise ValueError("请选择同一航次中顺序正确的起运港和目的港")
        database.conn.execute("""
            INSERT INTO bill_of_lading_bindings VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(bill_no) DO UPDATE SET voyage_id=excluded.voyage_id,
                origin_call_id=excluded.origin_call_id, destination_call_id=excluded.destination_call_id,
                updated_at=excluded.updated_at
        """, (bill_no, voyage_id, origin_call_id, destination_call_id, now_str()))
        return True
