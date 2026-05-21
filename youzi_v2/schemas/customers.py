from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class CustomerIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_name: str = Field(
        min_length=1,
        validation_alias=AliasChoices("customerName", "customer_name"),
    )
    note: str = ""
    is_vip: bool = Field(default=False, validation_alias=AliasChoices("isVip", "is_vip"))


class CustomerUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_vip: bool | None = Field(default=None, validation_alias=AliasChoices("isVip", "is_vip"))
    note: str | None = None


class CustomerSyncResult(BaseModel):
    model_config = {"populate_by_name": True}

    added: int = Field(description="本次新增客户数")
    total: int = Field(description="客户表总数")
    from_shipments: int = Field(alias="fromShipments", description="运单中去重客户数")
