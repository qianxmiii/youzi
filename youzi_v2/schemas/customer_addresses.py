"""客户地址簿请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CustomerAddressIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_name: str = Field(alias="customerName")
    label: str = ""
    consignee_name: str = Field(default="", alias="consigneeName")
    company: str = ""
    phone: str = ""
    email: str = ""
    country: str
    address: str
    postcode: str = ""
    address_kind: str = Field(alias="addressKind")
    is_remote: bool = Field(default=False, alias="isRemote")
    note: str = ""


class CustomerAddressBatchDeleteIn(BaseModel):
    ids: list[str] = Field(default_factory=list)
