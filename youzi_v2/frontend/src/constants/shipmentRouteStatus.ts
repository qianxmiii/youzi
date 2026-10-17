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

export function routeStatusLabelZh(
  code: string | null | undefined,
  override?: Record<string, string> | null,
): string {
  const key = (code || '').trim().toUpperCase()
  if (!key) return ''
  return override?.[key] || ROUTE_STATUS_LABEL_ZH[key] || key
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

/** 运单列表「状态」列：粗状态已签收时优先显示已签收（601 轨迹签收仅作明细，不顶替粗状态）。 */
export function resolveShipmentListStatusDisplay(input: {
  statusCode?: string | null
  routeStatus?: string | null
  routeStatusLabelByCode?: Record<string, string> | null
  coarseStatusLabel: Record<string, string>
}): { label: string; toneClass: string; tipExtra: string } {
  const coarse = (input.statusCode || 'UNKNOWN').trim().toUpperCase()
  const route = (input.routeStatus || '').trim().toUpperCase()

  if (coarse === 'DELIVERED') {
    let tipExtra = ''
    if (isDisplayableRouteStatus(route)) {
      tipExtra = `明细：${routeStatusLabelZh(route, input.routeStatusLabelByCode)}；`
    }
    return {
      label: input.coarseStatusLabel['DELIVERED'] || '已签收',
      toneClass: 'shipment-status-badge--success',
      tipExtra,
    }
  }

  if (isDisplayableRouteStatus(route)) {
    const label = routeStatusLabelZh(route, input.routeStatusLabelByCode)
    const coarseLabel = input.coarseStatusLabel[coarse] || coarse
    const tipExtra =
      coarseLabel && coarseLabel !== label ? `粗状态：${coarseLabel}；` : ''
    return {
      label,
      toneClass: routeStatusBadgeClass(route),
      tipExtra,
    }
  }

  return {
    label: input.coarseStatusLabel[coarse] || coarse,
    toneClass:
      coarse === 'DELIVERED'
        ? 'shipment-status-badge--success'
        : coarse === 'INSPECTION'
          ? 'shipment-status-badge--warning'
          : 'shipment-status-badge--default',
    tipExtra: '',
  }
}
