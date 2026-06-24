from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from ..shipment_group_rules import RULE_TYPES, normalize_rule_type

PAYMENT_STATUSES = frozenset({"UNPAID", "PARTIAL", "PAID"})
PAYMENT_DUE_RULES = frozenset({"LAST_ARRIVAL"})


class ShipmentGroupRuleIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_type: str = Field(..., validation_alias=AliasChoices("ruleType", "rule_type"))
    enabled: bool = True
    threshold_days: int | None = Field(
        default=None,
        validation_alias=AliasChoices("thresholdDays", "threshold_days"),
    )
    warning_days: int | None = Field(
        default=None,
        validation_alias=AliasChoices("warningDays", "warning_days"),
    )
    trigger_status: str = Field(
        default="",
        validation_alias=AliasChoices("triggerStatus", "trigger_status"),
    )
    config_json: str = Field(
        default="{}",
        validation_alias=AliasChoices("configJson", "config_json"),
    )

    @field_validator("rule_type")
    @classmethod
    def _rule_type(cls, v: str) -> str:
        return normalize_rule_type(v)


class ShipmentGroupRulesReplaceIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rules: list[ShipmentGroupRuleIn] = Field(default_factory=list)


class ShipmentGroupRulePatchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool | None = None
    threshold_days: int | None = Field(
        default=None,
        validation_alias=AliasChoices("thresholdDays", "threshold_days"),
    )
    warning_days: int | None = Field(
        default=None,
        validation_alias=AliasChoices("warningDays", "warning_days"),
    )
    trigger_status: str | None = Field(
        default=None,
        validation_alias=AliasChoices("triggerStatus", "trigger_status"),
    )
    config_json: str | None = Field(
        default=None,
        validation_alias=AliasChoices("configJson", "config_json"),
    )


class ShipmentGroupMembersAddIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("shipmentIds", "ids"),
    )


class ShipmentGroupMembersRemoveIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("shipmentIds", "ids"),
    )


class ShipmentGroupMemberPatchItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_id: str = Field(
        ...,
        validation_alias=AliasChoices("shipmentId", "id"),
    )


class ShipmentGroupMembersBatchPatchIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ShipmentGroupMemberPatchItem] = Field(..., min_length=1, max_length=200)


class ShipmentGroupMemberMutationError(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_id: str = Field(default="", validation_alias=AliasChoices("shipmentId", "id"))
    shipment_no: str = Field(default="", validation_alias=AliasChoices("shipmentNo", "shipment_no"))
    message: str = ""


class ShipmentGroupMembersAddResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    added: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[ShipmentGroupMemberMutationError] = Field(default_factory=list)


class ShipmentGroupMembersRemoveResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    removed: int = 0
    not_found: int = Field(default=0, alias="notFound")
    errors: list[ShipmentGroupMemberMutationError] = Field(default_factory=list)


class ShipmentGroupMembersBatchPatchResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total: int = 0
    updated: int = 0
    not_found: int = Field(default=0, alias="notFound")
    skipped: int = 0
    errors: list[ShipmentGroupMemberMutationError] = Field(default_factory=list)


class ShipmentGroupIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    group_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("groupNo", "group_no"),
        description="分组编号；留空则自动生成 GYYMMDDnnn",
    )
    group_name: str = Field(
        default="",
        validation_alias=AliasChoices("groupName", "group_name"),
    )
    customer: str | None = None
    customer_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerNo", "customer_no"),
    )
    vessel_voyage: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
    )
    destination_port_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("destinationPortCode", "destination_port_code"),
    )
    payment_status: str = Field(
        default="UNPAID",
        validation_alias=AliasChoices("paymentStatus", "payment_status"),
    )
    payment_due_rule: str = Field(
        default="LAST_ARRIVAL",
        validation_alias=AliasChoices("paymentDueRule", "payment_due_rule"),
    )
    note: str = ""
    rules: list[ShipmentGroupRuleIn] = Field(default_factory=list)

    @field_validator("payment_status")
    @classmethod
    def _payment_status(cls, v: str) -> str:
        key = (v or "UNPAID").strip().upper()
        if key not in PAYMENT_STATUSES:
            raise ValueError(f"paymentStatus 须为 {', '.join(sorted(PAYMENT_STATUSES))}")
        return key

    @field_validator("payment_due_rule")
    @classmethod
    def _payment_due_rule(cls, v: str) -> str:
        key = (v or "LAST_ARRIVAL").strip().upper()
        if key not in PAYMENT_DUE_RULES:
            raise ValueError(f"paymentDueRule 须为 {', '.join(sorted(PAYMENT_DUE_RULES))}")
        return key

    @field_validator("rules")
    @classmethod
    def _rules_unique(cls, v: list[ShipmentGroupRuleIn]) -> list[ShipmentGroupRuleIn]:
        seen: set[str] = set()
        for rule in v:
            if rule.rule_type in seen:
                raise ValueError(f"规则重复：{rule.rule_type}")
            seen.add(rule.rule_type)
        return v


class ShipmentGroupEvaluateResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    evaluated: int = 0
    created: int = 0
    errors: list[dict[str, str]] = Field(default_factory=list)


class ShipmentGroupNotificationReadResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    count: int = 0


class ShipmentGroupSuggestionsPreviewIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    shipment_ids: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("shipmentIds", "ids"),
    )


class ShipmentGroupSuggestionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    suggestion_key: str = Field(
        default="",
        validation_alias=AliasChoices("suggestionKey", "suggestion_key"),
    )
    rule_type: str = Field(
        default="",
        validation_alias=AliasChoices("ruleType", "rule_type"),
    )
    rule_label: str = Field(
        default="",
        validation_alias=AliasChoices("ruleLabel", "rule_label"),
    )
    proposed_group_name: str = Field(
        default="",
        validation_alias=AliasChoices("proposedGroupName", "proposed_group_name"),
    )
    group_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("groupNo", "group_no"),
    )
    group_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("groupName", "group_name"),
    )
    customer: str | None = None
    customer_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerNo", "customer_no"),
    )
    vessel_voyage: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
    )
    destination_port_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("destinationPortCode", "destination_port_code"),
    )
    shipment_ids: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("shipmentIds", "shipment_ids"),
    )
    shipment_nos: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("shipmentNos", "shipment_nos"),
    )
    member_count: int = Field(default=0, alias="memberCount")
    rules: list[ShipmentGroupRuleIn] = Field(default_factory=list)


class ShipmentGroupSuggestionsPreviewResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    suggestions: list[ShipmentGroupSuggestionItem] = Field(default_factory=list)
    shipment_count: int = Field(default=0, alias="shipmentCount")
    missing_shipment_ids: list[str] = Field(
        default_factory=list,
        alias="missingShipmentIds",
    )


class ShipmentGroupSuggestionsApplyIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[ShipmentGroupSuggestionItem] = Field(..., min_length=1, max_length=50)


class ShipmentGroupSuggestionsApplyResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    groups_created: int = Field(default=0, alias="groupsCreated")
    members_added: int = Field(default=0, alias="membersAdded")
    skipped: int = 0
    errors: list[dict[str, str]] = Field(default_factory=list)


class ShipmentGroupUpdateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    group_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("groupName", "group_name"),
    )
    customer: str | None = None
    customer_no: str | None = Field(
        default=None,
        validation_alias=AliasChoices("customerNo", "customer_no"),
    )
    vessel_voyage: str | None = Field(
        default=None,
        validation_alias=AliasChoices("vesselVoyage", "vessel_voyage"),
    )
    destination_port_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("destinationPortCode", "destination_port_code"),
    )
    payment_status: str | None = Field(
        default=None,
        validation_alias=AliasChoices("paymentStatus", "payment_status"),
    )
    payment_due_rule: str | None = Field(
        default=None,
        validation_alias=AliasChoices("paymentDueRule", "payment_due_rule"),
    )
    note: str | None = None
    rules: list[ShipmentGroupRuleIn] | None = None

    @field_validator("payment_status")
    @classmethod
    def _payment_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        key = v.strip().upper()
        if key not in PAYMENT_STATUSES:
            raise ValueError(f"paymentStatus 须为 {', '.join(sorted(PAYMENT_STATUSES))}")
        return key

    @field_validator("payment_due_rule")
    @classmethod
    def _payment_due_rule(cls, v: str | None) -> str | None:
        if v is None:
            return None
        key = v.strip().upper()
        if key not in PAYMENT_DUE_RULES:
            raise ValueError(f"paymentDueRule 须为 {', '.join(sorted(PAYMENT_DUE_RULES))}")
        return key

    @field_validator("rules")
    @classmethod
    def _rules_unique(
        cls, v: list[ShipmentGroupRuleIn] | None
    ) -> list[ShipmentGroupRuleIn] | None:
        if v is None:
            return None
        seen: set[str] = set()
        for rule in v:
            if rule.rule_type in seen:
                raise ValueError(f"规则重复：{rule.rule_type}")
            seen.add(rule.rule_type)
        return v
