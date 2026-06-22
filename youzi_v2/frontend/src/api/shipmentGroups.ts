import { api } from '@/api/client'
import type {
  ShipmentGroup,
  ShipmentGroupCreatePayload,
  ShipmentGroupDetail,
  ShipmentGroupEvaluateResult,
  ShipmentGroupListResponse,
  ShipmentGroupMembersAddResult,
  ShipmentGroupMembersBatchPatchResult,
  ShipmentGroupMembersRemoveResult,
  ShipmentGroupNotificationListResponse,
  ShipmentGroupSuggestionsApplyResult,
  ShipmentGroupSuggestionsPreviewResult,
  ShipmentGroupSuggestion,
  ShipmentGroupUpdatePayload,
} from '@/types/shipmentGroup'

export interface ListShipmentGroupsParams {
  search?: string
  groupType?: string
  paymentStatus?: string
  customer?: string
  limit?: number
  offset?: number
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
  if (params?.groupType?.trim()) query.groupType = params.groupType.trim()
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
  options?: { role?: string; batchNo?: string },
): Promise<ShipmentGroupMembersAddResult> {
  return api<ShipmentGroupMembersAddResult>(`/api/v1/shipment-groups/${groupId}/members`, {
    method: 'POST',
    body: {
      shipmentIds,
      role: options?.role ?? 'NORMAL',
      batchNo: options?.batchNo ?? '',
    },
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

export async function patchShipmentGroupMembersBatch(
  groupId: string,
  items: { shipmentId: string; role?: string; batchNo?: string }[],
): Promise<ShipmentGroupMembersBatchPatchResult> {
  return api<ShipmentGroupMembersBatchPatchResult>(
    `/api/v1/shipment-groups/${groupId}/members/batch`,
    { method: 'PATCH', body: { items } },
  )
}
