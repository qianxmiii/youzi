"""中远海运 COSCO eLines 公开船期。"""

from __future__ import annotations

import time
from typing import Any

import requests

from ....db.datetime_util import normalize_tracking_time
from ...vessel_voyage_fields import compose_vessel_voyage, resolve_voyage_identity
from ..types import DEFAULT_PERIOD_DAYS, ScheduleProviderInfo

_SCHEDULE_URL = (
    "https://elines.coscoshipping.com/ebschedule/public/purpoShipment/vesselCode"
)
_VESSEL_SEARCH_URL = (
    "https://elines.coscoshipping.com/ebbase/public/general/findVesselByPrefix"
)
_MIN_VESSEL_PREFIX_LEN = 3
_DEFAULT_TIMEOUT = 30
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; YouziV2/1.0)",
    "Accept": "application/json",
}

_INFO = ScheduleProviderInfo(
    id="cosco_elines",
    shipping_company="COSCO",
    label="COSCO",
    aliases=(
        "COSCO",
        "COSCO SHIPPING",
        "COSCO SHIPPING LINES",
        "COSCOSCO",
        "COSCON",
        "中远",
        "中远海运",
        "中远海运集运",
    ),
)


def _norm_time(value: Any) -> str | None:
    text = normalize_tracking_time(str(value).strip() if value is not None else "")
    return text or None


def parse_elines_purpo_rows(
    rows: list[dict[str, Any]],
    *,
    shipping_company: str,
    source_label: str,
) -> dict[str, Any]:
    vessel_name: str | None = None
    voyage_no: str | None = None
    vessel_code: str | None = None
    loop_abbrv: str | None = None
    port_calls: list[dict[str, Any]] = []

    for row in rows:
        if not vessel_name:
            vessel_name = (row.get("vesselName") or "").strip() or None
        if not voyage_no:
            voyage_no = (row.get("voy") or "").strip() or None
        if not vessel_code:
            vessel_code = (row.get("vesselCode") or "").strip() or None
        if not loop_abbrv:
            loop_abbrv = (row.get("loopAbbrv") or "").strip() or None

        port_name = (row.get("protName") or "").strip()
        if not port_name:
            continue
        port_calls.append(
            {
                "portName": port_name,
                "sequence": len(port_calls) + 1,
                "eta": _norm_time(row.get("arrDtlocCos")),
                "ata": _norm_time(row.get("arrDtlocAct")),
                "etd": _norm_time(row.get("depDtlocCos")),
                "atd": _norm_time(row.get("depDtlocAct")),
            }
        )

    if not port_calls:
        raise ValueError(f"{shipping_company} 未返回有效挂靠港口")

    notes_parts = [f"来源 {source_label}（{shipping_company}）"]
    if loop_abbrv:
        notes_parts.append(f"航线 {loop_abbrv}")

    meta: dict[str, Any] = {
        "vesselName": vessel_name,
        "voyageNo": voyage_no,
        "vesselCode": vessel_code,
        "shippingCompany": shipping_company,
        "notes": " · ".join(notes_parts),
    }
    vv, name, voy = resolve_voyage_identity(
        vessel_name=vessel_name,
        voyage_no=voyage_no,
        vessel_voyage=compose_vessel_voyage(vessel_name, voyage_no) or None,
    )
    meta["vesselVoyage"] = vv
    meta["vesselName"] = name
    meta["voyageNo"] = voy
    meta["portCalls"] = port_calls
    return meta


def _extract_rows(payload: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    if str(payload.get("code")) != "200":
        msg = (payload.get("message") or "").strip() or f"{label} 接口返回异常"
        raise ValueError(msg)
    content = payload.get("data") or {}
    if isinstance(content, dict) and "content" in content:
        content = content["content"]
    if not isinstance(content, dict):
        raise ValueError(f"{label} 响应格式异常")
    rows = content.get("data")
    if not isinstance(rows, list):
        raise ValueError(f"{label} 未返回船期数据")
    return rows


def _parse_vessel_search_rows(payload: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    if str(payload.get("code")) != "200":
        msg = (payload.get("message") or "").strip() or f"{label} 船舶检索异常"
        raise ValueError(msg)
    data = payload.get("data") or {}
    if isinstance(data, dict) and "content" in data:
        rows = data["content"]
    else:
        rows = data
    if not isinstance(rows, list):
        return []
    items: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = (row.get("code") or "").strip().upper()
        name = (row.get("description") or row.get("chineseDescription") or "").strip()
        if not code or not name:
            continue
        items.append(
            {
                "vesselCode": code,
                "vesselName": name,
                "label": f"{name}（{code}）",
            }
        )
    return items


class CoscoElinesProvider:
    info = _INFO

    def search_vessels(
        self,
        prefix: str,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> list[dict[str, Any]]:
        text = (prefix or "").strip()
        if len(text) < _MIN_VESSEL_PREFIX_LEN:
            return []
        label = self.info.label
        params = {"prefix": text, "timestamp": int(time.time() * 1000)}
        try:
            resp = requests.get(
                _VESSEL_SEARCH_URL,
                params=params,
                headers=_HEADERS,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ValueError(f"{label} 船舶检索失败: {exc}") from exc
        if resp.status_code != 200:
            raise ValueError(f"{label} 船舶检索 HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ValueError(f"{label} 船舶检索响应非 JSON") from exc
        return _parse_vessel_search_rows(payload, label=label)

    def _vessel_code_known(
        self,
        code: str,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> bool:
        """用船名前缀检索校验 vesselCode 是否在 COSCO 船名录中。"""
        if len(code) < _MIN_VESSEL_PREFIX_LEN:
            return False
        try:
            items = self.search_vessels(code, timeout=timeout)
        except ValueError:
            return False
        return any((item.get("vesselCode") or "").strip().upper() == code for item in items)

    def fetch(
        self,
        vessel_code: str,
        *,
        period: int = DEFAULT_PERIOD_DAYS,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        code = (vessel_code or "").strip().upper()
        if not code:
            raise ValueError("vesselCode 不能为空")
        period_days = max(7, min(int(period or DEFAULT_PERIOD_DAYS), 90))
        params = {
            "vesselCode": code,
            "period": period_days,
            "timestamp": int(time.time() * 1000),
        }
        label = self.info.label
        try:
            resp = requests.get(
                _SCHEDULE_URL,
                params=params,
                headers=_HEADERS,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise ValueError(f"{label} 请求失败: {exc}") from exc
        if resp.status_code != 200:
            raise ValueError(f"{label} HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ValueError(f"{label} 响应非 JSON") from exc
        rows = _extract_rows(payload, label=label)
        if not rows:
            if not self._vessel_code_known(code, timeout=timeout):
                raise ValueError(
                    f"{label} 未找到船舶代码「{code}」，请通过船名检索选择正确的 vesselCode"
                )
            raise ValueError(
                f"{label} 船舶「{code}」在未来 {period_days} 天内暂无挂靠船期"
            )
        parsed = parse_elines_purpo_rows(
            rows,
            shipping_company=self.info.shipping_company,
            source_label=label,
        )
        parsed["source"] = {
            "provider": self.info.id,
            "shippingCompany": self.info.shipping_company,
            "vesselCode": code,
            "period": period_days,
            "rowCount": len(rows),
        }
        return parsed
