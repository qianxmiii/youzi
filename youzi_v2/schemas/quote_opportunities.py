from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ..services.quote_followup_rules import CHANGE_REASONS, FOLLOWUP_TYPES


class QuoteOpportunityCreateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str = Field(default="", validation_alias=AliasChoices("customerId", "customer_id"))
    customer_name: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("customerName", "customer_name"),
    )
    is_new_customer: bool = Field(
        default=False,
        validation_alias=AliasChoices("isNewCustomer", "is_new_customer"),
    )
    customer_inquiry_no: str = Field(
        default="",
        validation_alias=AliasChoices("customerInquiryNo", "customer_inquiry_no"),
    )
    quote_date: str | None = Field(
        default=None, validation_alias=AliasChoices("quoteDate", "quote_date")
    )
    deadline_date: str | None = Field(
        default=None, validation_alias=AliasChoices("deadlineDate", "deadline_date")
    )
    followup_interval_days: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("followupIntervalDays", "followup_interval_days"),
    )
    next_followup_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("nextFollowupDate", "next_followup_date"),
    )
    owner: str = ""
    product_name: str = Field(
        default="", validation_alias=AliasChoices("productName", "product_name")
    )
    address_text: str = Field(
        default="", validation_alias=AliasChoices("addressText", "address_text")
    )
    ctns: int | None = None
    weight_kg: float | None = Field(
        default=None, validation_alias=AliasChoices("weightKg", "weight_kg")
    )
    volume_cbm: float | None = Field(
        default=None, validation_alias=AliasChoices("volumeCbm", "volume_cbm")
    )
    quoted_amount: float | None = Field(
        default=None, validation_alias=AliasChoices("quotedAmount", "quoted_amount")
    )
    quoted_currency: str = Field(
        default="", validation_alias=AliasChoices("quotedCurrency", "quoted_currency")
    )
    profit_amount: float | None = Field(
        default=None, validation_alias=AliasChoices("profitAmount", "profit_amount")
    )
    profit_currency: str = Field(
        default="", validation_alias=AliasChoices("profitCurrency", "profit_currency")
    )
    profit_rate: float | None = Field(
        default=None, validation_alias=AliasChoices("profitRate", "profit_rate")
    )
    note: str = ""


class QuoteOpportunityPatchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str | None = Field(
        default=None, validation_alias=AliasChoices("customerId", "customer_id")
    )
    customer_name: str | None = Field(
        default=None, validation_alias=AliasChoices("customerName", "customer_name")
    )
    is_new_customer: bool | None = Field(
        default=None, validation_alias=AliasChoices("isNewCustomer", "is_new_customer")
    )
    customer_inquiry_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerInquiryNo", "customer_inquiry_no"),
    )
    quote_date: str | None = Field(
        default=None, validation_alias=AliasChoices("quoteDate", "quote_date")
    )
    deadline_date: str | None = Field(
        default=None, validation_alias=AliasChoices("deadlineDate", "deadline_date")
    )
    followup_interval_days: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("followupIntervalDays", "followup_interval_days"),
    )
    next_followup_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("nextFollowupDate", "next_followup_date"),
    )
    status: str | None = None
    owner: str | None = None
    product_name: str | None = Field(
        default=None, validation_alias=AliasChoices("productName", "product_name")
    )
    address_text: str | None = Field(
        default=None, validation_alias=AliasChoices("addressText", "address_text")
    )
    ctns: int | None = None
    weight_kg: float | None = Field(
        default=None, validation_alias=AliasChoices("weightKg", "weight_kg")
    )
    volume_cbm: float | None = Field(
        default=None, validation_alias=AliasChoices("volumeCbm", "volume_cbm")
    )
    note: str | None = None
    lost_reason: str | None = Field(
        default=None, validation_alias=AliasChoices("lostReason", "lost_reason")
    )


class QuoteVersionIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    change_reason: str = Field(
        default="OTHER",
        validation_alias=AliasChoices("changeReason", "change_reason"),
    )
    product_name: str | None = Field(
        default=None, validation_alias=AliasChoices("productName", "product_name")
    )
    address_text: str | None = Field(
        default=None, validation_alias=AliasChoices("addressText", "address_text")
    )
    ctns: int | None = None
    weight_kg: float | None = Field(
        default=None, validation_alias=AliasChoices("weightKg", "weight_kg")
    )
    volume_cbm: float | None = Field(
        default=None, validation_alias=AliasChoices("volumeCbm", "volume_cbm")
    )
    quoted_amount: float | None = Field(
        default=None, validation_alias=AliasChoices("quotedAmount", "quoted_amount")
    )
    quoted_currency: str | None = Field(
        default=None, validation_alias=AliasChoices("quotedCurrency", "quoted_currency")
    )
    profit_amount: float | None = Field(
        default=None, validation_alias=AliasChoices("profitAmount", "profit_amount")
    )
    profit_currency: str | None = Field(
        default=None, validation_alias=AliasChoices("profitCurrency", "profit_currency")
    )
    profit_rate: float | None = Field(
        default=None, validation_alias=AliasChoices("profitRate", "profit_rate")
    )
    note: str = ""

    @field_validator("change_reason")
    @classmethod
    def _v_reason(cls, v: str) -> str:
        key = (v or "OTHER").strip().upper()
        if key not in CHANGE_REASONS:
            raise ValueError("changeReason 无效")
        return key


class QuoteFollowupIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    followup_type: str = Field(
        default="",
        validation_alias=AliasChoices("followupType", "followup_type"),
    )
    note: str = ""
    next_followup_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("nextFollowupDate", "next_followup_date"),
    )
    adjust_quote: bool = Field(
        default=False,
        validation_alias=AliasChoices("adjustQuote", "adjust_quote"),
    )
    version: QuoteVersionIn | None = None

    @field_validator("followup_type")
    @classmethod
    def _v_type(cls, v: str) -> str:
        key = (v or "").strip().lower()
        if key and key not in FOLLOWUP_TYPES:
            raise ValueError("followupType 须为 phone / wechat / email / other")
        return key


class QuoteMarkLostIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lost_reason: str = Field(
        default="",
        validation_alias=AliasChoices("lostReason", "lost_reason"),
    )
    note: str | None = None


class QuoteExtendDeadlineIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    deadline_date: str = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("deadlineDate", "deadline_date"),
    )
    next_followup_date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("nextFollowupDate", "next_followup_date"),
    )
