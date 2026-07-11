from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from ..services.payment_reminder_rules import SETTLEMENT_METHODS, SETTLEMENT_MONTHLY


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

    customer_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerName", "customer_name"),
    )
    update_shipments: bool | None = Field(
        default=None,
        validation_alias=AliasChoices("updateShipments", "update_shipments"),
    )
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

    @field_validator("customer_name", mode="before")
    @classmethod
    def _customer_name(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            raise ValueError("客户名不能为空")
        return s

    @field_validator("customer_lang", mode="before")
    @classmethod
    def _customer_lang(cls, v: object) -> str | None:
        if v is None:
            return None
        return _normalize_customer_lang(str(v))

    settlement_method: str | None = Field(
        default=None,
        validation_alias=AliasChoices("settlementMethod", "settlement_method"),
    )
    settlement_day: int | None = Field(
        default=None,
        validation_alias=AliasChoices("settlementDay", "settlement_day"),
    )

    @field_validator("settlement_method", mode="before")
    @classmethod
    def _settlement_method(cls, v: object) -> str | None:
        if v is None:
            return None
        text = str(v).strip().upper()
        if not text:
            return None
        if text not in SETTLEMENT_METHODS:
            raise ValueError("settlementMethod 无效")
        return text

    @field_validator("settlement_day", mode="before")
    @classmethod
    def _settlement_day(cls, v: object) -> int | None:
        if v is None or v == "":
            return None
        n = int(v)
        if n < 1 or n > 31:
            raise ValueError("settlementDay 须在 1-31 之间")
        return n

    @model_validator(mode="after")
    def _monthly_requires_day(self) -> "CustomerUpdateIn":
        if self.settlement_method == SETTLEMENT_MONTHLY and self.settlement_day is None:
            raise ValueError("月结客户须填写 settlementDay")
        return self


class CustomerSyncResult(BaseModel):
    model_config = {"populate_by_name": True}

    added: int = Field(description="本次新增客户数")
    total: int = Field(description="客户表总数")
    from_shipments: int = Field(alias="fromShipments", description="运单中去重客户数")

