"""顶栏世界时间配置。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorldClockZone(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tz: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=32)


class WorldClocksSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = True
    use24h: bool = Field(default=True, alias="use24h")
    zones: list[WorldClockZone] = Field(default_factory=list, max_length=6)


class WorldClocksSettingsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool
    use24h: bool = Field(alias="use24h")
    zones: list[WorldClockZone] = Field(max_length=6)
