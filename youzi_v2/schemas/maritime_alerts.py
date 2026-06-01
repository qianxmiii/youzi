from pydantic import BaseModel, ConfigDict, Field


class MaritimeAlertCounts(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    arriving_soon: int = Field(0, validation_alias="arrivingSoon")
    departing_soon: int = Field(0, validation_alias="departingSoon")
    arrived: int = Field(0, validation_alias="arrived")
    in_transit: int = Field(0, validation_alias="inTransit")
    planned: int = Field(0, validation_alias="planned")
    unknown: int = Field(0, validation_alias="unknown")
    port_arriving_soon: int = Field(0, validation_alias="portArrivingSoon")
    port_departing_soon: int = Field(0, validation_alias="portDepartingSoon")


class MaritimeAlertShipment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_no: str = Field(validation_alias="shipmentNo")
    customer: str | None = None
    vessel_voyage: str | None = Field(None, validation_alias="vesselVoyage")
    maritime_status: str = Field(validation_alias="maritimeStatus")
    maritime_status_label: str = Field(validation_alias="maritimeStatusLabel")
    eta: str | None = None
    etd: str | None = None
    destination_port_code: str | None = Field(None, validation_alias="destinationPortCode")


class MaritimeAlertPortCall(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    voyage_id: str = Field(validation_alias="voyageId")
    vessel_voyage: str = Field(validation_alias="vesselVoyage")
    port_name: str = Field(validation_alias="portName")
    sequence: int
    status: str
    status_label: str = Field(validation_alias="statusLabel")
    eta: str | None = None
    etd: str | None = None


class PortArrivalNotification(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    subscription_id: str = Field(validation_alias="subscriptionId")
    port_call_id: str = Field(validation_alias="portCallId")
    voyage_id: str = Field(validation_alias="voyageId")
    port_name: str = Field(validation_alias="portName")
    vessel_voyage: str = Field(validation_alias="vesselVoyage")
    ata: str
    created_at: str = Field(validation_alias="createdAt")
    read_at: str | None = Field(None, validation_alias="readAt")


class MaritimeAlertsOverview(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    generated_at: str = Field(validation_alias="generatedAt")
    counts: MaritimeAlertCounts
    urgent_shipments: list[MaritimeAlertShipment] = Field(
        default_factory=list, validation_alias="urgentShipments"
    )
    urgent_port_calls: list[MaritimeAlertPortCall] = Field(
        default_factory=list, validation_alias="urgentPortCalls"
    )
    eta_arriving_soon_port_calls: list[MaritimeAlertPortCall] = Field(
        default_factory=list, validation_alias="etaArrivingSoonPortCalls"
    )
    eta_arriving_soon_shipments: list[MaritimeAlertShipment] = Field(
        default_factory=list, validation_alias="etaArrivingSoonShipments"
    )
    voyages_with_alerts: list[dict] = Field(
        default_factory=list, validation_alias="voyagesWithAlerts"
    )
    unconfigured_vessel_voyages: list[dict] = Field(
        default_factory=list, validation_alias="unconfiguredVesselVoyages"
    )
    total_scanned: int = Field(0, validation_alias="totalScanned")
    port_arrival_notifications: list[PortArrivalNotification] = Field(
        default_factory=list, validation_alias="portArrivalNotifications"
    )
