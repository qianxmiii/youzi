from pydantic import AliasChoices, BaseModel, ConfigDict, Field


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

    vessel_voyage: str = Field(
        min_length=1,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
    )
    notes: str = ""
    port_calls: list[VoyagePortCallIn] = Field(
        default_factory=list,
        validation_alias=AliasChoices("portCalls", "port_calls"),
    )


class VesselVoyageUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    vessel_voyage: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
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
