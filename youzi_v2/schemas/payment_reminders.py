from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ..services.payment_reminder_rules import SETTLEMENT_METHODS


class PaymentReminderFollowupIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    note: str = ""


class PaymentReminderFollowupBatchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("shipmentIds", "shipment_ids"),
    )
    note: str = ""


class PaymentReminderFollowupResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    shipment_id: str = Field(alias="shipmentId")
    shipment_no: str = Field(alias="shipmentNo")
    followup_time: str = Field(alias="followupTime")
    note: str = ""


class PaymentReminderFollowupBatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    created: int = 0
    failed: int = 0
    errors: list[dict[str, str]] = Field(default_factory=list)


def _validate_settlement_method(v: str | None) -> str | None:
    if v is None:
        return None
    text = v.strip().upper()
    if not text:
        return None
    if text not in SETTLEMENT_METHODS:
        raise ValueError(
            "settlementMethod 须为 BEFORE_SHIPMENT / BEFORE_ARRIVAL / "
            "AFTER_ARRIVAL / MONTHLY / AFTER_DELIVERY"
        )
    return text


def _validate_settlement_day(v: int | None, settlement_method: str | None) -> int | None:
    if v is None:
        return None
    if v < 1 or v > 31:
        raise ValueError("settlementDay 须在 1-31 之间")
    return v
