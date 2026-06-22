/** 运单分组类型（与后端 shipment_group_types.py 一致） */

export const SHIPMENT_GROUP_TYPE_OPTIONS = [
  { value: 'MANUAL', label: '手动分组', description: '临时跟进、运营人工整理的任意组合' },
  { value: 'CUSTOMER_BATCH', label: '客户批次', description: '同一客户的一批货，统一跟进签收、罚款和收款' },
  { value: 'ORDER_BATCH', label: '订单批次', description: '同一客户订单或平台订单下的多票运单' },
  { value: 'VESSEL_BATCH', label: '船次批次', description: '同一船名航次的一批海运货' },
  { value: 'PORT_BATCH', label: '到港批次', description: '同一目的港或同一 ETA 窗口内的货' },
  { value: 'PAYMENT_BATCH', label: '收款批次', description: '以催款、账期、尾款为核心管理的一组运单' },
] as const

export type ShipmentGroupType = (typeof SHIPMENT_GROUP_TYPE_OPTIONS)[number]['value']

const LABEL_MAP = Object.fromEntries(
  SHIPMENT_GROUP_TYPE_OPTIONS.map((o) => [o.value, o.label]),
) as Record<ShipmentGroupType, string>

export function shipmentGroupTypeLabel(value?: string | null): string {
  if (!value?.trim()) return '—'
  const key = value.trim().toUpperCase()
  return LABEL_MAP[key as ShipmentGroupType] ?? key
}

export function groupPrimaryType(group: {
  primaryType?: string | null
  groupType?: string | null
}): ShipmentGroupType {
  const key = (group.primaryType || group.groupType || 'MANUAL').trim().toUpperCase()
  return key as ShipmentGroupType
}

export function shipmentGroupTypeSelectOptions() {
  return SHIPMENT_GROUP_TYPE_OPTIONS.map((o) => ({
    label: o.label,
    value: o.value,
  }))
}
