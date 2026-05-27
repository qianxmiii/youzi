from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

DEFAULT_PERIOD_DAYS = 28


@dataclass(frozen=True)
class ScheduleProviderInfo:
    id: str
    shipping_company: str
    label: str
    aliases: tuple[str, ...]


class MaritimeScheduleProvider(Protocol):
    info: ScheduleProviderInfo

    def fetch(
        self,
        vessel_code: str,
        *,
        period: int = DEFAULT_PERIOD_DAYS,
    ) -> dict[str, Any]: ...
