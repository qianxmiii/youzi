import { api } from '@/api/client'
import type {
  ShipmentGroup,
  ShipmentGroupCreatePayload,
  ShipmentGroupDetail,
  ShipmentGroupEvaluateResult,
  ShipmentGroupListResponse,
  ShipmentGroupMembersAddResult,
  ShipmentGroupMembersRemoveResult,
  ShipmentGroupNotificationListResponse,
  ShipmentGroupRule,
  ShipmentGroupRuleInput,
  ShipmentGroupRuleMeta,
  ShipmentGroupSuggestionsApplyResult,
  ShipmentGroupSuggestionsPreviewResult,
  ShipmentGroupSuggestion,
  ShipmentGroupUnreadNotificationsResponse,
  ShipmentGroupUpdatePayload,
} from '@/types/shipmentGroup'

export interface ListShipmentGroupsParams {
  search?: string
  ruleType?: string
  hasRule?: boolean
  hasUnread?: boolean
  paymentStatus?: string
  customer?: string
  archived?: boolean
  limit?: number
  offset?: number
}

export async function getShipmentGroupRulesMeta(): Promise<{ ruleTypes: ShipmentGroupRuleMeta[] }> {
  return api('/api/v1/shipment-groups/meta')
}

export async function previewShipmentGroupSuggestions(
  shipmentIds: string[],
): Promise<ShipmentGroupSuggestionsPreviewResult> {
  return api('/api/v1/shipment-groups/suggestions/preview', {
    method: 'POST',
    body: { shipmentIds },
  })
}

export async function applyShipmentGroupSuggestions(
  items: ShipmentGroupSuggestion[],
): Promise<ShipmentGroupSuggestionsApplyResult> {
  return api('/api/v1/shipment-groups/suggestions/apply', {
    method: 'POST',
    body: { items },
  })
}

export async function getShipmentGroupUnreadNotifications(
  limit = 20,
): Promise<ShipmentGroupUnreadNotificationsResponse> {
  return api('/api/v1/shipment-group-notifications', {
    query: { limit: String(limit) },
  })
}

export async function resolveShipmentGroupNotification(notificationId: string): Promise<void> {
  await api(`/api/v1/shipment-group-notifications/${notificationId}/resolve`, {
    method: 'POST',
  })
}

export async function getShipmentGroup(groupId: string): Promise<ShipmentGroupDetail> {
  return api<ShipmentGroupDetail>(`/api/v1/shipment-groups/${groupId}`)
}

export async function updateShipmentGroup(
  groupId: string,
  payload: ShipmentGroupUpdatePayload,
): Promise<ShipmentGroup> {
  return api<ShipmentGroup>(`/api/v1/shipment-groups/${groupId}`, {
    method: 'PUT',
    body: payload,
  })
}

export async function deleteShipmentGroup(groupId: string): Promise<void> {
  await api(`/api/v1/shipment-groups/${groupId}`, { method: 'DELETE' })
}

export async function archiveShipmentGroup(groupId: string): Promise<ShipmentGroup> {
  return api<ShipmentGroup>(`/api/v1/shipment-groups/${groupId}/archive`, { method: 'POST' })
}

export async function unarchiveShipmentGroup(groupId: string): Promise<ShipmentGroup> {
  return api<ShipmentGroup>(`/api/v1/shipment-groups/${groupId}/unarchive`, { method: 'POST' })
}

export async function listShipmentGroupRules(groupId: string): Promise<{ items: ShipmentGroupRule[] }> {
  return api(`/api/v1/shipment-groups/${groupId}/rules`)
}

export async function replaceShipmentGroupRules(
  groupId: string,
  rules: ShipmentGroupRuleInput[],
): Promise<{ items: ShipmentGroupRule[] }> {
  return api(`/api/v1/shipment-groups/${groupId}/rules`, {
    method: 'PUT',
    body: { rules },
  })
}

export async function patchShipmentGroupRule(
  groupId: string,
  ruleType: string,
  patch: Partial<ShipmentGroupRuleInput>,
): Promise<ShipmentGroupRule> {
  return api(`/api/v1/shipment-groups/${groupId}/rules/${ruleType}`, {
    method: 'PATCH',
    body: patch,
  })
}

export async function listShipmentGroupNotifications(
  groupId: string,
  params?: { unreadOnly?: boolean; limit?: number; offset?: number },
): Promise<ShipmentGroupNotificationListResponse> {
  const query: Record<string, string> = {}
  if (params?.unreadOnly) query.unreadOnly = 'true'
  if (params?.limit != null) query.limit = String(params.limit)
  if (params?.offset != null) query.offset = String(params.offset)
  return api(`/api/v1/shipment-groups/${groupId}/notifications`, { query })
}

export async function evaluateShipmentGroupAlerts(
  groupId: string,
): Promise<ShipmentGroupEvaluateResult> {
  return api(`/api/v1/shipment-groups/${groupId}/evaluate-alerts`, { method: 'POST' })
}

export async function markShipmentGroupNotificationRead(notificationId: string): Promise<void> {
  await api(`/api/v1/shipment-group-notifications/${notificationId}/read`, { method: 'POST' })
}

export async function markAllShipmentGroupNotificationsRead(groupId?: string): Promise<number> {
  const query: Record<string, string> = {}
  if (groupId) query.groupId = groupId
  const res = await api<{ count: number }>('/api/v1/shipment-group-notifications/read-all', {
    method: 'POST',
    query,
  })
  return res.count
}

export async function listShipmentGroups(
  params?: ListShipmentGroupsParams,
): Promise<ShipmentGroupListResponse> {
  const query: Record<string, string> = {}
  if (params?.search?.trim()) query.search = params.search.trim()
  if (params?.ruleType?.trim()) query.ruleType = params.ruleType.trim()
  if (params?.hasRule === true) query.hasRule = 'true'
  if (params?.hasRule === false) query.hasRule = 'false'
  if (params?.hasUnread === true) query.hasUnread = 'true'
  if (params?.archived === true) query.archived = 'true'
  else if (params?.archived === false) query.archived = 'false'
  if (params?.paymentStatus?.trim()) query.paymentStatus = params.paymentStatus.trim()
  if (params?.customer?.trim()) query.customer = params.customer.trim()
  if (params?.limit != null) query.limit = String(params.limit)
  if (params?.offset != null) query.offset = String(params.offset)
  return api<ShipmentGroupListResponse>('/api/v1/shipment-groups', { query })
}

export async function createShipmentGroup(
  payload: ShipmentGroupCreatePayload,
): Promise<ShipmentGroup> {
  return api<ShipmentGroup>('/api/v1/shipment-groups', { method: 'POST', body: payload })
}

export async function addShipmentGroupMembers(
  groupId: string,
  shipmentIds: string[],
): Promise<ShipmentGroupMembersAddResult> {
  return api<ShipmentGroupMembersAddResult>(`/api/v1/shipment-groups/${groupId}/members`, {
    method: 'POST',
    body: { shipmentIds },
  })
}

export async function removeShipmentGroupMembers(
  groupId: string,
  shipmentIds: string[],
): Promise<ShipmentGroupMembersRemoveResult> {
  return api<ShipmentGroupMembersRemoveResult>(`/api/v1/shipment-groups/${groupId}/members`, {
    method: 'DELETE',
    body: { shipmentIds },
  })
}