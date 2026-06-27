export interface ShipmentGroupMember {
  id: string
  groupId: string
  shipmentId: string
  shipmentNo: string
  createdTime: string
}

export interface ShipmentGroupRule {
  id?: string
  groupId?: string
  ruleType: string
  enabled: boolean
  thresholdDays: number | null
  warningDays: number | null
  triggerStatus: string
  configJson: string
  createdTime?: string
  updatedTime?: string
}

export interface ShipmentGroupRuleInput {
  ruleType: string
  enabled: boolean
  thresholdDays?: number | null
  warningDays?: number | null
  triggerStatus?: string
  configJson?: string
}

export interface ShipmentGroupNotification {
  id: string
  groupId: string
  groupNo?: string
  groupName?: string
  customer?: string | null
  ruleType: string
  severity: string
  title: string
  message: string
  shipmentNo: string
  eventKey: string
  triggeredAt: string
  readAt: string | null
  resolvedAt: string | null
}

export interface ShipmentGroupDetail extends ShipmentGroup {
  members?: ShipmentGroupMember[]
  rules?: ShipmentGroupRule[]
  arrivedCount?: number
  deliveredCount?: number
  undeliveredCount?: number
  unreadNotificationCount?: number
}

export interface ShipmentGroupNotificationListResponse {
  items: ShipmentGroupNotification[]
  total: number
  limit: number
  offset: number
}

export interface ShipmentGroupUnreadNotificationsResponse {
  items: ShipmentGroupNotification[]
  unreadCount: number
}

export interface ShipmentGroupEvaluateResult {
  evaluated: number
  created: number
  errors: { groupId?: string; message: string }[]
}

export interface ShipmentGroupUpdatePayload {
  groupName?: string
  customer?: string | null
  customerNo?: string | null
  vesselVoyage?: string | null
  destinationPortCode?: string | null
  paymentStatus?: string
  paymentDueRule?: string
  note?: string
  rules?: ShipmentGroupRuleInput[]
}

export interface ShipmentGroupSummary {
  groupId: string
  groupNo: string
  groupName: string
  enabledRules?: string[]
}

export interface ShipmentGroupFilterOption {
  id: string
  groupNo: string
  groupName: string
}

export interface ShipmentGroup {
  id: string
  groupNo: string
  groupName: string
  customer: string | null
  customerNo: string | null
  vesselVoyage: string | null
  destinationPortCode: string | null
  paymentStatus: string
  paymentDueRule: string
  note: string
  archivedAt?: string | null
  createdTime: string
  updatedTime: string
  memberCount?: number
  enabledRules?: string[]
  unreadNotificationCount?: number
}

export interface ShipmentGroupCreatePayload {
  groupNo?: string
  groupName?: string
  customer?: string | null
  customerNo?: string | null
  vesselVoyage?: string | null
  destinationPortCode?: string | null
  paymentStatus?: string
  paymentDueRule?: string
  note?: string
  rules?: ShipmentGroupRuleInput[]
}

export interface ShipmentGroupListResponse {
  items: ShipmentGroup[]
  total: number
  limit: number
  offset: number
}

export interface ShipmentGroupMemberMutationError {
  shipmentId?: string
  shipmentNo?: string
  message: string
}

export interface ShipmentGroupMembersAddResult {
  total: number
  added: number
  skipped: number
  failed: number
  errors: ShipmentGroupMemberMutationError[]
}

export interface ShipmentGroupMembersRemoveResult {
  total: number
  removed: number
  notFound: number
  errors: ShipmentGroupMemberMutationError[]
}

export type ShipmentGroupBatchMode = 'create' | 'add' | 'remove' | 'suggest'

export interface ShipmentGroupSuggestion {
  suggestionKey: string
  ruleType: string
  ruleLabel: string
  proposedGroupName: string
  groupNo?: string | null
  groupName?: string | null
  customer?: string | null
  customerNo?: string | null
  vesselVoyage?: string | null
  destinationPortCode?: string | null
  shipmentIds: string[]
  shipmentNos: string[]
  memberCount: number
  rules?: ShipmentGroupRuleInput[]
}

export interface ShipmentGroupSuggestionsPreviewResult {
  suggestions: ShipmentGroupSuggestion[]
  shipmentCount: number
  missingShipmentIds: string[]
}

export interface ShipmentGroupSuggestionsApplyResult {
  groupsCreated: number
  membersAdded: number
  skipped: number
  errors: { suggestionKey?: string; message: string }[]
}

export interface ShipmentGroupRuleMeta {
  value: string
  label: string
  description: string
}
