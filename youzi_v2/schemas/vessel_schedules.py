from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class VoyagePortCallIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = None
    port_name: str = Field(min_length=1, validation_alias=AliasChoices("portName", "port_name"))
    sequence: int = Field(default=1, ge=1)
    eta: str | None = None
    ata: str | None = None
    etd: str | None = None
    atd: str | None = None


class VesselVoyageIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vessel_voyage: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
    )
    vessel_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselName", "vessel_name"),
    )
    voyage_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("voyageNo", "voyage_no"),
    )
    vessel_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselCode", "vessel_code"),
    )
    shipping_company: str | None = Field(
        default=None,
        validation_alias=AliasChoices("shippingCompany", "shipping_company"),
    )
    notes: str = ""
    port_calls: list[VoyagePortCallIn] = Field(
        default_factory=list,
        validation_alias=AliasChoices("portCalls", "port_calls"),
    )

    @field_validator("notes", mode="before")
    @classmethod
    def _coerce_notes(cls, value: object) -> str:
        return "" if value is None else str(value)


class VesselVoyageUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vessel_voyage: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
    )
    vessel_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselName", "vessel_name"),
    )
    voyage_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("voyageNo", "voyage_no"),
    )
    vessel_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselCode", "vessel_code"),
    )
    shipping_company: str | None = Field(
        default=None,
        validation_alias=AliasChoices("shippingCompany", "shipping_company"),
    )
    notes: str | None = None
    port_calls: list[VoyagePortCallIn] | None = Field(
        default=None,
        validation_alias=AliasChoices("portCalls", "port_calls"),
    )


class VoyageImportResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    created: int
    updated: int
    failed: int
    errors: list[dict[str, str | int]] = Field(default_factory=list)


class VesselScheduleFetchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipping_company: str = Field(
        min_length=1,
        validation_alias=AliasChoices("shippingCompany", "shipping_company"),
    )
    vessel_code: str = Field(
        min_length=1,
        validation_alias=AliasChoices("vesselCode", "vessel_code"),
    )
    period: int = Field(default=28, ge=7, le=90)
    notes: str | None = None
