from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ChannelIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(min_length=1)
    name_zh: str = Field(
        default="",
        validation_alias=AliasChoices("nameZh", "name_zh"),
    )
    name_en: str = Field(
        default="",
        validation_alias=AliasChoices("nameEn", "name_en"),
    )
    country: str = ""
    category: str = ""
    note: str = ""
    dps_channel_name: str = Field(
        default="",
        validation_alias=AliasChoices(
            "dpsChannelName",
            "dps_channel_name",
            "DPS_channelName",
        ),
    )
    sort_order: int = Field(default=0, validation_alias=AliasChoices("sortOrder", "sort_order"))
    is_active: bool = Field(default=True, validation_alias=AliasChoices("isActive", "is_active"))


class ChannelUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str | None = Field(default=None, min_length=1)
    name_zh: str | None = Field(default=None, validation_alias=AliasChoices("nameZh", "name_zh"))
    name_en: str | None = Field(default=None, validation_alias=AliasChoices("nameEn", "name_en"))
    country: str | None = None
    category: str | None = None
    note: str | None = None
    dps_channel_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "dpsChannelName",
            "dps_channel_name",
            "DPS_channelName",
        ),
    )
    sort_order: int | None = Field(default=None, validation_alias=AliasChoices("sortOrder", "sort_order"))
    is_active: bool | None = Field(default=None, validation_alias=AliasChoices("isActive", "is_active"))


class ChannelSeedResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    inserted: int
    updated: int
    total: int
    deleted: int = 0
