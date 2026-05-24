from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


def _normalize_customer_lang(v: str | None) -> str:
    if not v:
        return "zh"
    s = v.strip().lower()
    if s in ("en", "en_us", "english"):
        return "en"
    return "zh"


class CustomerIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_name: str = Field(
        min_length=1,
        validation_alias=AliasChoices("customerName", "customer_name"),
    )
    customer_lang: str = Field(
        default="zh",
        validation_alias=AliasChoices(
            "customerLang",
            "customer_lang",
            "trackQueryLang",
            "track_query_lang",
        ),
    )
    note: str = ""
    is_vip: bool = Field(default=False, validation_alias=AliasChoices("isVip", "is_vip"))

    @field_validator("customer_lang", mode="before")
    @classmethod
    def _customer_lang(cls, v: object) -> str:
        return _normalize_customer_lang(str(v) if v is not None else "")


class CustomerUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_vip: bool | None = Field(default=None, validation_alias=AliasChoices("isVip", "is_vip"))
    note: str | None = None
    customer_lang: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "customerLang",
            "customer_lang",
            "trackQueryLang",
            "track_query_lang",
        ),
    )

    @field_validator("customer_lang", mode="before")
    @classmethod
    def _customer_lang(cls, v: object) -> str | None:
        if v is None:
            return None
        return _normalize_customer_lang(str(v))


class CustomerSyncResult(BaseModel):
    model_config = {"populate_by_name": True}

    added: int = Field(description="本次新增客户数")
    total: int = Field(description="客户表总数")
    from_shipments: int = Field(alias="fromShipments", description="运单中去重客户数")
