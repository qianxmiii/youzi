"""船公司船期 Provider 注册表。"""

from __future__ import annotations

from typing import Any

from .providers.cosco_elines import CoscoElinesProvider
from .types import DEFAULT_PERIOD_DAYS, MaritimeScheduleProvider, ScheduleProviderInfo


def _normalize_company_key(raw: str) -> str:
    return "".join((raw or "").upper().split())


def _alias_keys(info: ScheduleProviderInfo) -> set[str]:
    keys = {_normalize_company_key(info.shipping_company), _normalize_company_key(info.id)}
    keys.update(_normalize_company_key(a) for a in info.aliases)
    keys.discard("")
    return keys


_PROVIDERS: list[MaritimeScheduleProvider] = [
    CoscoElinesProvider(),
]


def _provider_features(provider: MaritimeScheduleProvider) -> dict[str, bool]:
    return {
        "vesselSearch": callable(getattr(provider, "search_vessels", None)),
    }


def list_schedule_providers() -> list[dict[str, Any]]:
    return [
        {
            "id": p.info.id,
            "shippingCompany": p.info.shipping_company,
            "label": p.info.label,
            "aliases": list(p.info.aliases),
            "features": _provider_features(p),
        }
        for p in _PROVIDERS
    ]


def resolve_schedule_provider(shipping_company: str) -> MaritimeScheduleProvider:
    key = _normalize_company_key(shipping_company)
    if not key:
        supported = ", ".join(p.info.shipping_company for p in _PROVIDERS)
        raise ValueError(f"请指定船公司（已支持：{supported}）")
    for provider in _PROVIDERS:
        if key in _alias_keys(provider.info):
            return provider
    supported = ", ".join(f"{p.info.shipping_company}（{p.info.label}）" for p in _PROVIDERS)
    raise ValueError(f"暂不支持船公司「{shipping_company}」，已接入：{supported}")


def search_carrier_vessels(shipping_company: str, prefix: str) -> list[dict[str, Any]]:
    provider = resolve_schedule_provider(shipping_company)
    search = getattr(provider, "search_vessels", None)
    if not callable(search):
        raise ValueError(f"船公司「{shipping_company}」暂不支持船名检索")
    return search(prefix)


def fetch_vessel_schedule(
    shipping_company: str,
    vessel_code: str,
    *,
    period: int = DEFAULT_PERIOD_DAYS,
) -> dict[str, Any]:
    provider = resolve_schedule_provider(shipping_company)
    parsed = provider.fetch(vessel_code, period=period)
    parsed.setdefault("shippingCompany", provider.info.shipping_company)
    source = parsed.get("source")
    if isinstance(source, dict):
        source.setdefault("shippingCompany", provider.info.shipping_company)
    return parsed
