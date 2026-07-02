"""码表 API 请求体。"""

from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CodeTableRecordIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    code: str
    name_zh: str = Field(default="", validation_alias=AliasChoices("nameZh", "name_zh"))
    name_en: str = Field(default="", validation_alias=AliasChoices("nameEn", "name_en"))
    sort_order: int = Field(
        default=0, validation_alias=AliasChoices("sortOrder", "sort_order")
    )
    is_active: bool = Field(
        default=True, validation_alias=AliasChoices("isActive", "is_active")
    )
    port_type: str = Field(
        default="both", validation_alias=AliasChoices("portType", "port_type")
    )
    country: str = Field(default="")
    category: str = Field(default="")
    note: str = Field(default="")
    carrier_id: str = Field(
        default="", validation_alias=AliasChoices("carrierId", "carrier_id")
    )

    def to_payload(self) -> dict:
        return self.model_dump()


class CodeTableUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name_zh: str = Field(default="", validation_alias=AliasChoices("nameZh", "name_zh"))
    name_en: str = Field(default="", validation_alias=AliasChoices("nameEn", "name_en"))
    sort_order: int = Field(
        default=0, validation_alias=AliasChoices("sortOrder", "sort_order")
    )
    is_active: bool = Field(
        default=True, validation_alias=AliasChoices("isActive", "is_active")
    )
    port_type: str = Field(
        default="both", validation_alias=AliasChoices("portType", "port_type")
    )
    country: str = Field(default="")
    category: str = Field(default="")
    note: str = Field(default="")
    carrier_id: str = Field(
        default="", validation_alias=AliasChoices("carrierId", "carrier_id")
    )

    def to_payload(self) -> dict:
        return self.model_dump()
