/** 运单工作台：港前（核对/下载） vs 在途（轨迹） */

export type ShipmentWorkspace = 'preport' | 'transit'

export const SHIPMENT_WORKSPACE_PREPORT: ShipmentWorkspace = 'preport'
export const SHIPMENT_WORKSPACE_TRANSIT: ShipmentWorkspace = 'transit'

/** DPS Status */
export const DPS_STATUS_ORDERED = '0'
export const DPS_STATUS_PICKED_UP = '01'
export const DPS_STATUS_WAREHOUSE_IN = '1'
export const DPS_STATUS_IN_TRANSIT = '2'
export const DPS_STATUS_DELIVERED = '3'
export const DPS_STATUS_CANCELLED = '4'

export const PRE_PORT_STATUS_CODES = new Set([
  DPS_STATUS_ORDERED,
  DPS_STATUS_PICKED_UP,
  DPS_STATUS_WAREHOUSE_IN,
  DPS_STATUS_CANCELLED,
])

export const TRANSIT_STATUS_CODES = new Set([
  DPS_STATUS_IN_TRANSIT,
  DPS_STATUS_DELIVERED,
  'IN_TRANSIT',
  'DELIVERED',
])

/** 港前列表不展示（列设置中亦隐藏） */
export const PREPORT_EXCLUDED_COLUMN_KEYS = [
  'carrierCode',
  'latestCarrier',
  'latestTracking',
  'paymentStatus',
] as const

export const PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY = 'originWarehouseCode'
export const PREPORT_CHARGED_WEIGHT_COLUMN_KEY = 'chargedWeight'

const PREPORT_INJECTED_COLUMN_KEYS = new Set<string>([
  PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY,
  PREPORT_CHARGED_WEIGHT_COLUMN_KEY,
])

function insertColumnBefore(keys: readonly string[], columnKey: string, anchorKey: string): string[] {
  const list = [...keys]
  const anchorIdx = list.indexOf(anchorKey)
  if (anchorIdx >= 0) {
    return [...list.slice(0, anchorIdx), columnKey, ...list.slice(anchorIdx)]
  }
  return [columnKey, ...list]
}

function insertColumnAfter(keys: readonly string[], columnKey: string, anchorKey: string): string[] {
  const list = [...keys]
  const anchorIdx = list.indexOf(anchorKey)
  if (anchorIdx >= 0) {
    return [...list.slice(0, anchorIdx + 1), columnKey, ...list.slice(anchorIdx + 1)]
  }
  return [...list, columnKey]
}

/**
 * 港前列：强制展示「收货仓」（派送仓库前）、「计费重」（邮编后）。
 */
export function applyPreportListColumnKeys(keys: readonly string[]): string[] {
  const excluded = new Set<string>(PREPORT_EXCLUDED_COLUMN_KEYS)
  let list = keys.filter((k) => !excluded.has(k))
  list = list.filter((k) => !PREPORT_INJECTED_COLUMN_KEYS.has(k))

  list = insertColumnBefore(list, PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY, 'addressCode')
  if (!list.includes(PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY)) {
    list = insertColumnAfter(list, PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY, 'channelCode')
  }
  if (!list.includes(PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY)) {
    list = [PREPORT_ORIGIN_WAREHOUSE_COLUMN_KEY, ...list]
  }

  list = insertColumnAfter(list, PREPORT_CHARGED_WEIGHT_COLUMN_KEY, 'zipcode')
  if (!list.includes(PREPORT_CHARGED_WEIGHT_COLUMN_KEY)) {
    list = insertColumnAfter(list, PREPORT_CHARGED_WEIGHT_COLUMN_KEY, 'addressCode')
  }
  if (!list.includes(PREPORT_CHARGED_WEIGHT_COLUMN_KEY)) {
    list = [PREPORT_CHARGED_WEIGHT_COLUMN_KEY, ...list]
  }

  return list
}

export const SHIPMENT_STATUS_LABEL_ZH: Record<string, string> = {
  '0': '已下单',
  '01': '提货中',
  '1': '已入仓',
  '2': '转运中',
  '3': '已签收',
  '4': '已取消',
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

/** 在途页默认只看 DPS「转运中」(2)；港前不默认状态 */
export function defaultStatusFilterForWorkspace(ws: ShipmentWorkspace): string | null {
  return ws === SHIPMENT_WORKSPACE_TRANSIT ? DPS_STATUS_IN_TRANSIT : null
}

export function shipmentStatusLabel(code: string | null | undefined): string {
  const key = (code || '').trim()
  if (!key) return '—'
  return SHIPMENT_STATUS_LABEL_ZH[key] || key
}

/** 港前 DPS Status 徽章色调（01 提货中 vs 1 已入仓 等） */
export function dpsPreportStatusBadgeClass(code: string | null | undefined): string {
  const key = (code || '').trim()
  switch (key) {
    case DPS_STATUS_ORDERED:
      return 'shipment-status-badge--sky'
    case DPS_STATUS_PICKED_UP:
      return 'shipment-status-badge--orange'
    case DPS_STATUS_WAREHOUSE_IN:
      return 'shipment-status-badge--teal'
    case DPS_STATUS_CANCELLED:
      return 'shipment-status-badge--slate'
    default:
      return 'shipment-status-badge--default'
  }
}
