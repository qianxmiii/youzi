/** 非关键节点：不同步写入、列表状态列不展示（回退粗状态） */
export const NON_MILESTONE_ROUTE_STATUS = new Set(['INFO'])

/** 运单列表状态徽章：细状态色调（与 CSS `shipment-status-badge--*` 对应） */
export const ROUTE_STATUS_BADGE_TONE: Record<string, string> = {
  WAREHOUSE_IN: 'sky',
  EXPORT_CUSTOMS_RELEASE: 'teal',
  EXPORT_CUSTOMS_EXCEPTION: 'error',
  DEPARTED_POL: 'indigo',
  ARRIVED_POD: 'violet',
  IMPORT_CUSTOMS_EXCEPTION: 'rose',
  DEST_TRANSIT_WAREHOUSE: 'cyan',
  LAST_MILE_HANDOVER: 'orange',
  TRACK_SIGNED: 'success',
}

export function isDisplayableRouteStatus(code: string | null | undefined): boolean {
  const key = (code || '').trim().toUpperCase()
  return Boolean(key) && !NON_MILESTONE_ROUTE_STATUS.has(key)
}

export function routeStatusBadgeClass(code: string | null | undefined): string {
  const key = (code || '').trim().toUpperCase()
  const tone = ROUTE_STATUS_BADGE_TONE[key] || 'default'
  return `shipment-status-badge--${tone}`
}
