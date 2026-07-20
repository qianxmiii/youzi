"""工作台首页聚合概览 schemas。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkbenchFocusMetrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    available: bool = True
    error: str | None = None
    pending_exceptions: int = Field(0, alias="pendingExceptions")
    pending_collections: int = Field(0, alias="pendingCollections")
    pending_tracking_reviews: int = Field(0, alias="pendingTrackingReviews")
    arriving_soon: int = Field(0, alias="arrivingSoon")


class WorkbenchTodoItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    kinds: list[str] = Field(default_factory=list)
    priority: int = 5
    severity: str = "normal"
    shipment_id: str | None = Field(None, alias="shipmentId")
    shipment_no: str | None = Field(None, alias="shipmentNo")
    customer: str = ""
    title: str = ""
    summary: str = ""
    href: str = ""
    overdue_days: int = Field(0, alias="overdueDays")
    trigger_time: str | None = Field(None, alias="triggerTime")
    updated_time: str | None = Field(None, alias="updatedTime")


class WorkbenchTodosModule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    available: bool = True
    error: str | None = None
    items: list[WorkbenchTodoItem] = Field(default_factory=list)


class WorkbenchArrivalItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    day_group: str = Field("later", alias="dayGroup")
    vessel_voyage: str = Field("", alias="vesselVoyage")
    destination_port_code: str = Field("", alias="destinationPortCode")
    eta: str | None = None
    shipment_count: int = Field(0, alias="shipmentCount")
    is_subscribed_port: bool = Field(False, alias="isSubscribedPort")
    href: str = ""


class WorkbenchArrivalsModule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    available: bool = True
    error: str | None = None
    items: list[WorkbenchArrivalItem] = Field(default_factory=list)


class WorkbenchTransportOverview(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    available: bool = True
    error: str | None = None
    in_transit: int = Field(0, alias="inTransit")
    inspection: int = 0
    arrived_unsigned: int = Field(0, alias="arrivedUnsigned")
    delivered_this_week: int = Field(0, alias="deliveredThisWeek")


class WorkbenchOverviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    generated_at: str = Field(..., alias="generatedAt")
    focus: WorkbenchFocusMetrics
    todos: WorkbenchTodosModule
    arrivals: WorkbenchArrivalsModule
    overview: WorkbenchTransportOverview
