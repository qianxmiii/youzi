"""DPS 运单全量同步计划任务配置（app_settings）。"""



from __future__ import annotations



from dataclasses import dataclass

from typing import Any



from ..db.app_settings_table import get_setting, set_setting

from ..db.connection import Database

from ..db.datetime_util import now_str

from .scheduled_sync_settings import _parse_bool

from .shipment_query_config import default_transit_time_range, resolve_transit_time_range



KEY_DPS_SYNC_ENABLED = "shipments.dps_sync.enabled"

KEY_DPS_SYNC_TRANSIT_TIME_START = "shipments.dps_sync.transit_time_start"

KEY_DPS_SYNC_TRANSIT_TIME_END = "shipments.dps_sync.transit_time_end"

KEY_DPS_SYNC_TRANSIT_TIME_START_LEGACY = "shipments.dps_sync.order_time_start"

KEY_DPS_SYNC_TRANSIT_TIME_END_LEGACY = "shipments.dps_sync.order_time_end"

KEY_DPS_SYNC_LAST_FINISHED = "shipments.dps_sync.last_finished_at"



DPS_SYNC_INTERVAL_HOURS = 24.0





def _read_transit_time_setting(conn, key: str, legacy_key: str) -> str | None:

    value = get_setting(conn, key)

    if not (value or "").strip():

        value = get_setting(conn, legacy_key)

    return (value or "").strip() or None





@dataclass(frozen=True)

class ShipmentDpsSyncSettings:

    enabled: bool

    transit_time_start: str | None

    transit_time_end: str | None

    last_finished: str | None



    def effective_transit_time_range(self) -> tuple[str, str]:

        return resolve_transit_time_range(self.transit_time_start, self.transit_time_end)



    def to_api_dict(self) -> dict[str, Any]:

        default_start, default_end = default_transit_time_range()

        effective_start, effective_end = self.effective_transit_time_range()

        return {

            "dpsShipmentSyncEnabled": self.enabled,

            "dpsShipmentSyncTransitTimeStart": self.transit_time_start,

            "dpsShipmentSyncTransitTimeEnd": self.transit_time_end,

            "dpsShipmentSyncTransitTimeStartDefault": default_start,

            "dpsShipmentSyncTransitTimeEndDefault": default_end,

            "dpsShipmentSyncTransitTimeStartEffective": effective_start,

            "dpsShipmentSyncTransitTimeEndEffective": effective_end,

            "dpsShipmentSyncLastFinished": self.last_finished,

        }





def ensure_dps_sync_defaults(conn) -> None:

    if get_setting(conn, KEY_DPS_SYNC_ENABLED) is None:

        set_setting(conn, KEY_DPS_SYNC_ENABLED, "0")





def get_shipment_dps_sync_settings(database: Database) -> ShipmentDpsSyncSettings:

    with database.lock:

        ensure_dps_sync_defaults(database.conn)

        enabled = _parse_bool(get_setting(database.conn, KEY_DPS_SYNC_ENABLED), False)

        transit_time_start = _read_transit_time_setting(

            database.conn,

            KEY_DPS_SYNC_TRANSIT_TIME_START,

            KEY_DPS_SYNC_TRANSIT_TIME_START_LEGACY,

        )

        transit_time_end = _read_transit_time_setting(

            database.conn,

            KEY_DPS_SYNC_TRANSIT_TIME_END,

            KEY_DPS_SYNC_TRANSIT_TIME_END_LEGACY,

        )

        last_finished = get_setting(database.conn, KEY_DPS_SYNC_LAST_FINISHED)

    return ShipmentDpsSyncSettings(

        enabled=enabled,

        transit_time_start=transit_time_start,

        transit_time_end=transit_time_end,

        last_finished=last_finished,

    )





def save_shipment_dps_sync_enabled(

    database: Database, *, enabled: bool

) -> ShipmentDpsSyncSettings:

    with database.lock:

        ensure_dps_sync_defaults(database.conn)

        set_setting(database.conn, KEY_DPS_SYNC_ENABLED, "1" if enabled else "0")

        database.conn.commit()

    return get_shipment_dps_sync_settings(database)





def save_shipment_dps_sync_transit_time_range(

    database: Database,

    *,

    transit_time_start: str | None,

    transit_time_end: str | None,

) -> ShipmentDpsSyncSettings:

    with database.lock:

        ensure_dps_sync_defaults(database.conn)

        start = (transit_time_start or "").strip()

        end = (transit_time_end or "").strip()

        set_setting(

            database.conn,

            KEY_DPS_SYNC_TRANSIT_TIME_START,

            start if start else None,

        )

        set_setting(

            database.conn,

            KEY_DPS_SYNC_TRANSIT_TIME_END,

            end if end else None,

        )

        database.conn.commit()

    return get_shipment_dps_sync_settings(database)





# 兼容旧名

save_shipment_dps_sync_order_time_range = save_shipment_dps_sync_transit_time_range





def record_shipment_dps_sync_finished(database: Database) -> None:

    with database.lock:

        set_setting(database.conn, KEY_DPS_SYNC_LAST_FINISHED, now_str())

        database.conn.commit()

