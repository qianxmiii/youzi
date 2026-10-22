import {
  coarseShipmentStatusBadgeClass,
  normalizeShipmentStatusCode,
} from '@/constants/shipmentWorkspace'

/** 非关键节点：不同步写入、列表状态列不展示（回退粗状态） */
export const NON_MILESTONE_ROUTE_STATUS = new Set(['INFO'])

/** 运单列表状态徽章：明细状态色调（与 CSS `shipment-status-badge--*` 对应） */
export const ROUTE_STATUS_BADGE_TONE: Record<string, string> = {
  WAREHOUSE_IN: 'sky',
  EXPORT_CUSTOMS_RELEASE: 'teal',
  EXPORT_CUSTOMS_EXCEPTION: 'error',
  DEPARTED_POL: 'indigo',
  ARRIVED_POD: 'violet',
  IMPORT_CUSTOMS_EXCEPTION: 'rose',
  DEST_TRANSIT_WAREHOUSE: 'cyan',
  TRUCK_DISPATCH_APPOINTED: 'warning',
  LAST_MILE_HANDOVER: 'orange',
  TRACK_SIGNED: 'success',
}

/** 默认中文名（与码表种子一致；后台改名时可由调用方传入覆盖） */
export const ROUTE_STATUS_LABEL_ZH: Record<string, string> = {
  INFO: '信息传递',
  WAREHOUSE_IN: '入库',
  EXPORT_CUSTOMS_RELEASE: '出口海关放行',
  EXPORT_CUSTOMS_EXCEPTION: '出口海关异常',
  DEPARTED_POL: '离开起运港',
  ARRIVED_POD: '到达目的港',
  IMPORT_CUSTOMS_EXCEPTION: '进口清关异常',
  DEST_TRANSIT_WAREHOUSE: '到达目的国中转仓库',
  TRUCK_DISPATCH_APPOINTED: '卡派已约仓',
  LAST_MILE_HANDOVER: '快递派-已交仓',
  TRACK_SIGNED: '轨迹签收',
}

/** DPS commerceWaybillRouteInfo.status → 本地 route_status（与后端 ROUTE_STATUS_SEEDS 一致） */
export const ROUTE_STATUS_DPS_TO_LOCAL: Record<string, string> = {
  '100': 'INFO',
  '202': 'WAREHOUSE_IN',
  '205': 'EXPORT_CUSTOMS_RELEASE',
  '206': 'EXPORT_CUSTOMS_EXCEPTION',
  '301': 'DEPARTED_POL',
  '306': 'ARRIVED_POD',
  '402': 'IMPORT_CUSTOMS_EXCEPTION',
  '502': 'DEST_TRANSIT_WAREHOUSE',
  '509': 'TRUCK_DISPATCH_APPOINTED',
  '510': 'LAST_MILE_HANDOVER',
  '601': 'TRACK_SIGNED',
}

/** 将库内本地码或误存的 DPS 数字规范为本地 route_status 码 */
export function normalizeRouteStatusLocalCode(code: string | null | undefined): string {
  const raw = (code || '').trim()
  if (!raw) return ''
  const upper = raw.toUpperCase()
  if (upper in ROUTE_STATUS_LABEL_ZH) return upper
  const digits = raw.replace(/\.0+$/, '')
  if (/^\d+$/.test(digits)) {
    return ROUTE_STATUS_DPS_TO_LOCAL[digits] || ''
  }
  const asInt = Number.parseInt(String(Number.parseFloat(raw)), 10)
  if (Number.isFinite(asInt) && String(asInt) === digits) {
    return ROUTE_STATUS_DPS_TO_LOCAL[String(asInt)] || ''
  }
  return ''
}

export function routeStatusLabelZh(
  code: string | null | undefined,
  override?: Record<string, string> | null,
): string {
  const local = normalizeRouteStatusLocalCode(code)
  if (!local) {
    const fallback = (code || '').trim()
    return fallback
  }
  return override?.[local] || ROUTE_STATUS_LABEL_ZH[local] || local
}

export function isDisplayableRouteStatus(code: string | null | undefined): boolean {
  const local = normalizeRouteStatusLocalCode(code)
  if (!local || NON_MILESTONE_ROUTE_STATUS.has(local)) return false
  return local in ROUTE_STATUS_LABEL_ZH
}

export function routeStatusBadgeClass(code: string | null | undefined): string {
  const key = normalizeRouteStatusLocalCode(code)
  const tone = ROUTE_STATUS_BADGE_TONE[key] || 'default'
  return `shipment-status-badge--${tone}`
}

/** 运单列表「状态」列：粗状态已签收时优先显示已签收（601 轨迹签收仅作明细，不顶替粗状态）。 */
export function resolveShipmentListStatusDisplay(input: {
  statusCode?: string | number | null
  routeStatus?: string | null
  routeStatusLabelByCode?: Record<string, string> | null
  coarseStatusLabel: Record<string, string>
}): { label: string; toneClass: string; tipExtra: string } {
  const coarseRaw = normalizeShipmentStatusCode(input.statusCode) || 'UNKNOWN'
  const coarse = coarseRaw.toUpperCase()
  const routeLocal = normalizeRouteStatusLocalCode(input.routeStatus)

  if (coarse === 'DELIVERED' || coarseRaw === '3') {
    let tipExtra = ''
    if (isDisplayableRouteStatus(routeLocal)) {
      tipExtra = `明细：${routeStatusLabelZh(routeLocal, input.routeStatusLabelByCode)}；`
    }
    return {
      label: input.coarseStatusLabel['DELIVERED'] || '已签收',
      toneClass: 'shipment-status-badge--success',
      tipExtra,
    }
  }

  if (isDisplayableRouteStatus(routeLocal)) {
    const label = routeStatusLabelZh(routeLocal, input.routeStatusLabelByCode)
    const coarseLabel =
      input.coarseStatusLabel[coarseRaw] ||
      input.coarseStatusLabel[coarse] ||
      coarseRaw
    const tipExtra =
      coarseLabel && coarseLabel !== label ? `粗状态：${coarseLabel}；` : ''
    return {
      label,
      toneClass: routeStatusBadgeClass(routeLocal),
      tipExtra,
    }
  }

  return {
    label:
      input.coarseStatusLabel[coarseRaw] ||
      input.coarseStatusLabel[coarse] ||
      coarseRaw,
    toneClass: coarseShipmentStatusBadgeClass(coarseRaw),
    tipExtra: '',
  }
}
