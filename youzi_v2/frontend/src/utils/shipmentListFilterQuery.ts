import type { ListShipmentsParams } from '@/api/shipments'
import { CARRIER_FILTER_EMPTY } from '@/constants/shipmentFilters'
import type { ShipmentAdvancedTimeRanges, ShipmentTimeField } from '@/constants/shipmentListFilterMeta'
import { SHIPMENT_TIME_FIELD_OPTIONS } from '@/constants/shipmentListFilterMeta'
import { formatDateOnlyForApi } from '@/utils/formatDateTime'
import { parseBatchSearchTokens } from '@/utils/parseBatchSearch'

function rangeToApi(range: [number, number] | null | undefined): { from?: string; to?: string } {
  if (!range || range.length !== 2) return {}
  return {
    from: formatDateOnlyForApi(range[0]),
    to: formatDateOnlyForApi(range[1]),
  }
}

function timeFieldLabel(field: string | null | undefined): string {
  return SHIPMENT_TIME_FIELD_OPTIONS.find((o) => o.value === field)?.label || field || ''
}

export interface ShipmentFilterQueryInput {
  searchKeyword: string
  searchShipmentNo: string
  searchTrackingContent: string
  advExactShipmentNo: string
  advContainerNos: string
  advBillNos: string
  advCustomerShipmentIds: string
  filterStatus: string | null
  filterCustomer: string | null
  filterChannelCode: string | null
  timeField: ShipmentTimeField | null
  timeRange: [number, number] | null
  filterCarrier: string | null
  filterCountry: string | null
  filterChannelNameZh: string | null
  filterChannelCategory: string | null
  filterCustomerNo: string | null
  filterDestinationPort: string | null
  filterAddressKeyword: string | null
  filterVesselVoyage: string | null
  filterVipOnly: boolean
  filterNoInternalTracking: boolean
  filterNoCarrierTracking: boolean
  filterCarrierAheadOfInternal: boolean
  filterPendingTrackingTimeReview: boolean
  filterStaleDays: number | null
  filterNoTracking: boolean
  filterNoZipcode: boolean
  filterHasTrackingNumber: boolean
  filterException: string | null
  filterHasException: boolean | null
  filterGroupId: string | null
  filterGroupNo: string | null
  filterRuleType: string | null
  filterHasGroup: boolean | null
  missingEtd: boolean
  missingAtd: boolean
  missingEta: boolean
  missingAta: boolean
  missingExpectedDelivery: boolean
  missingDelivered: boolean
  notDelivered: boolean
  hasAta: boolean
  deliveryRisk: string | null
  advancedTimes: ShipmentAdvancedTimeRanges
  shipmentNoSearchActive: boolean
}

export function buildShipmentFilterQuery(input: ShipmentFilterQueryInput): ListShipmentsParams {
  const staleRaw = input.filterStaleDays
  const staleDays =
    staleRaw == null
      ? undefined
      : typeof staleRaw === 'number'
        ? staleRaw
        : Number(staleRaw)

  const topTime = rangeToApi(input.timeRange)
  const adv = input.advancedTimes
  const etd = rangeToApi(adv.etd)
  const atd = rangeToApi(adv.atd)
  const eta = rangeToApi(adv.eta)
  const ata = rangeToApi(adv.ata)
  const expected = rangeToApi(adv.expectedDelivery)
  const delivered = rangeToApi(adv.delivered)
  const created = rangeToApi(adv.created)
  const updated = rangeToApi(adv.updated)

  const keyword = input.searchKeyword.trim()
  const tokens = parseBatchSearchTokens(input.searchShipmentNo)
  const exactShipmentTokens = parseBatchSearchTokens(input.advExactShipmentNo)
  const containerTokens = parseBatchSearchTokens(input.advContainerNos)
  const billTokens = parseBatchSearchTokens(input.advBillNos)
  const customerShipmentTokens = parseBatchSearchTokens(input.advCustomerShipmentIds)
  const customerNoTokens = parseBatchSearchTokens(input.filterCustomerNo || '')
  const noInternal = input.filterNoInternalTracking || input.filterNoTracking

  return {
    ...(tokens.length ? { shipmentNos: tokens } : {}),
    ...(exactShipmentTokens.length ? { exactShipmentNos: exactShipmentTokens } : {}),
    ...(containerTokens.length ? { containerNos: containerTokens } : {}),
    ...(billTokens.length ? { billNos: billTokens } : {}),
    ...(customerShipmentTokens.length ? { customerShipmentIds: customerShipmentTokens } : {}),
    ...(customerNoTokens.length ? { customerNos: customerNoTokens } : {}),
    ...(keyword ? { search: keyword } : {}),
    ...(input.searchTrackingContent.trim()
      ? { trackingSearch: input.searchTrackingContent.trim() }
      : {}),
    statusCode: input.shipmentNoSearchActive ? undefined : input.filterStatus || undefined,
    exceptionCode: input.filterException || undefined,
    hasException:
      input.filterHasException === true ? true
      : input.filterHasException === false ? false
      : undefined,
    customer: input.filterCustomer || undefined,
    vipOnly: input.filterVipOnly ? true : undefined,
    carrierCode: input.filterCarrier || undefined,
    countryCode: input.filterCountry || undefined,
    channelCode: input.filterChannelCode || undefined,
    channelNameZh: input.filterChannelNameZh || undefined,
    channelCategory: input.filterChannelCategory || undefined,
    destinationPortCode: input.filterDestinationPort || undefined,
    addressKeyword: input.filterAddressKeyword || undefined,
    vesselVoyage: input.filterVesselVoyage || undefined,
    internalFreshness: noInternal ? 'none' : undefined,
    carrierFreshness: input.filterNoCarrierTracking ? 'none' : undefined,
    carrierAheadOfInternal: input.filterCarrierAheadOfInternal || undefined,
    pendingTrackingTimeReview: input.filterPendingTrackingTimeReview || undefined,
    minStaleDays:
      noInternal || staleDays == null || Number.isNaN(staleDays) || staleDays <= 0
        ? undefined
        : staleDays,
    noZipcode: input.filterNoZipcode || undefined,
    hasTrackingNumber: input.filterHasTrackingNumber || undefined,
    groupId: input.filterGroupId || undefined,
    groupNo: input.filterGroupNo || undefined,
    ruleType: input.filterRuleType || undefined,
    hasGroup:
      input.filterHasGroup === true ? true
      : input.filterHasGroup === false ? false
      : undefined,
    timeField:
      input.timeField && (topTime.from || topTime.to) ? input.timeField : undefined,
    timeFrom: topTime.from,
    timeTo: topTime.to,
    etdFrom: etd.from,
    etdTo: etd.to,
    atdFrom: atd.from,
    atdTo: atd.to,
    etaFrom: eta.from,
    etaTo: eta.to,
    ataFrom: ata.from,
    ataTo: ata.to,
    expectedDeliveryFrom: expected.from,
    expectedDeliveryTo: expected.to,
    deliveredFrom: delivered.from,
    deliveredTo: delivered.to,
    createdFrom: created.from,
    createdTo: created.to,
    updatedFrom: updated.from,
    updatedTo: updated.to,
    missingEtd: input.missingEtd || undefined,
    missingAtd: input.missingAtd || undefined,
    missingEta: input.missingEta || undefined,
    missingAta: input.missingAta || undefined,
    missingExpectedDelivery: input.missingExpectedDelivery || undefined,
    missingDelivered: input.missingDelivered || undefined,
    notDelivered: input.notDelivered || undefined,
    hasAta: input.hasAta || undefined,
    deliveryRisk: input.deliveryRisk || undefined,
  }
}

export type ShipmentFilterTag = {
  key: string
  label: string
}

export function buildShipmentFilterSummaryTags(
  input: ShipmentFilterQueryInput,
  ctx: import('@/constants/shipmentListFilterMeta').ShipmentFilterSummaryContext,
): ShipmentFilterTag[] {
  const tags: ShipmentFilterTag[] = []
  const kw = input.searchKeyword.trim()
  if (kw) tags.push({ key: 'searchKeyword', label: `关键词 = ${kw}` })
  if (input.searchShipmentNo.trim()) {
    const n = parseBatchSearchTokens(input.searchShipmentNo).length
    tags.push({
      key: 'searchShipmentNo',
      label: n > 1 ? `多号搜索 × ${n}` : `多号搜索 = ${input.searchShipmentNo.trim().slice(0, 40)}`,
    })
  }
  if (input.advExactShipmentNo.trim()) {
    const n = parseBatchSearchTokens(input.advExactShipmentNo).length
    tags.push({ key: 'advExactShipmentNo', label: n > 1 ? `运单号 × ${n}` : `运单号 = ${input.advExactShipmentNo.trim()}` })
  }
  if (input.advContainerNos.trim()) {
    const n = parseBatchSearchTokens(input.advContainerNos).length
    tags.push({ key: 'advContainerNos', label: n > 1 ? `柜号 × ${n}` : `柜号 = ${input.advContainerNos.trim()}` })
  }
  if (input.advBillNos.trim()) {
    const n = parseBatchSearchTokens(input.advBillNos).length
    tags.push({ key: 'advBillNos', label: n > 1 ? `提单号 × ${n}` : `提单号 = ${input.advBillNos.trim()}` })
  }
  if (input.advCustomerShipmentIds.trim()) {
    const n = parseBatchSearchTokens(input.advCustomerShipmentIds).length
    tags.push({
      key: 'advCustomerShipmentIds',
      label: n > 1 ? `货件号 × ${n}` : `货件号 = ${input.advCustomerShipmentIds.trim()}`,
    })
  }
  if (input.searchTrackingContent.trim()) {
    tags.push({ key: 'searchTrackingContent', label: `轨迹 = ${input.searchTrackingContent.trim()}` })
  }
  if (input.filterStatus) {
    tags.push({
      key: 'filterStatus',
      label: `状态 = ${ctx.statusLabel[input.filterStatus] || input.filterStatus}`,
    })
  }
  if (input.filterCustomer) tags.push({ key: 'filterCustomer', label: `客户 = ${input.filterCustomer}` })
  if (input.filterChannelCode) {
    tags.push({
      key: 'filterChannelCode',
      label: `渠道 = ${ctx.channelLabel(input.filterChannelCode)}`,
    })
  }
  if (input.timeField && input.timeRange) {
    const { from, to } = rangeToApi(input.timeRange)
    tags.push({
      key: 'timeRange',
      label: `${timeFieldLabel(input.timeField)}：${from || '…'} ~ ${to || '…'}`,
    })
  }
  if (input.filterCarrier && input.filterCarrier !== CARRIER_FILTER_EMPTY) {
    tags.push({ key: 'filterCarrier', label: `承运商 = ${ctx.carrierLabel(input.filterCarrier)}` })
  } else if (input.filterCarrier === CARRIER_FILTER_EMPTY) {
    tags.push({ key: 'filterCarrier', label: '承运商 = （未填写）' })
  }
  if (input.filterCountry) {
    tags.push({ key: 'filterCountry', label: `国家 = ${ctx.countryLabel(input.filterCountry)}` })
  }
  if (input.filterChannelNameZh) {
    tags.push({ key: 'filterChannelNameZh', label: `渠道名 = ${input.filterChannelNameZh}` })
  }
  if (input.filterChannelCategory) {
    tags.push({ key: 'filterChannelCategory', label: `大类 = ${input.filterChannelCategory}` })
  }
  if (input.filterCustomerNo?.trim()) {
    const n = parseBatchSearchTokens(input.filterCustomerNo).length
    tags.push({
      key: 'filterCustomerNo',
      label: n > 1 ? `客户编号 × ${n}` : `客户编号 = ${input.filterCustomerNo.trim()}`,
    })
  }
  if (input.filterDestinationPort) {
    tags.push({ key: 'filterDestinationPort', label: `目的港 = ${input.filterDestinationPort}` })
  }
  if (input.filterAddressKeyword) {
    tags.push({ key: 'filterAddressKeyword', label: `地址 = ${input.filterAddressKeyword}` })
  }
  if (input.filterVesselVoyage) {
    tags.push({ key: 'filterVesselVoyage', label: `船名航次 = ${input.filterVesselVoyage}` })
  }
  if (input.filterVipOnly) tags.push({ key: 'filterVipOnly', label: '仅 VIP' })
  if (input.filterHasException === true) tags.push({ key: 'filterHasException', label: '有异常' })
  if (input.filterHasException === false) tags.push({ key: 'filterHasException', label: '无异常' })
  if (input.filterException) {
    tags.push({ key: 'filterException', label: `异常类型 = ${ctx.exceptionLabel(input.filterException)}` })
  }
  if (input.filterNoTracking || input.filterNoInternalTracking) {
    tags.push({ key: 'filterNoInternalTracking', label: '内部无轨迹' })
  }
  if (input.filterNoCarrierTracking) tags.push({ key: 'filterNoCarrierTracking', label: '承运商无轨迹' })
  if (input.filterNoZipcode) tags.push({ key: 'filterNoZipcode', label: '无邮编' })
  if (input.filterHasTrackingNumber) tags.push({ key: 'filterHasTrackingNumber', label: '有转单号' })
  if (input.filterStaleDays) tags.push({ key: 'filterStaleDays', label: `停滞 ≥ ${input.filterStaleDays} 天` })
  if (input.filterCarrierAheadOfInternal) tags.push({ key: 'filterCarrierAheadOfInternal', label: '承新于内' })
  if (input.filterPendingTrackingTimeReview) {
    tags.push({ key: 'filterPendingTrackingTimeReview', label: '待轨迹审批' })
  }
  if (input.filterGroupId) tags.push({ key: 'filterGroupId', label: `分组 = ${ctx.groupLabel(input.filterGroupId)}` })
  if (input.filterGroupNo) tags.push({ key: 'filterGroupNo', label: `分组编号 = ${input.filterGroupNo}` })
  if (input.filterRuleType) tags.push({ key: 'filterRuleType', label: `规则 = ${input.filterRuleType}` })
  if (input.filterHasGroup === true) tags.push({ key: 'filterHasGroup', label: '已分组' })
  if (input.filterHasGroup === false) tags.push({ key: 'filterHasGroup', label: '未分组' })
  if (input.missingEtd) tags.push({ key: 'missingEtd', label: '缺 ETD' })
  if (input.missingAtd) tags.push({ key: 'missingAtd', label: '缺 ATD' })
  if (input.missingEta) tags.push({ key: 'missingEta', label: '缺 ETA' })
  if (input.missingAta) tags.push({ key: 'missingAta', label: '缺 ATA' })
  if (input.missingExpectedDelivery) tags.push({ key: 'missingExpectedDelivery', label: '缺预计送仓' })
  if (input.missingDelivered) tags.push({ key: 'missingDelivered', label: '缺签收时间' })
  if (input.notDelivered) tags.push({ key: 'notDelivered', label: '未签收' })
  if (input.hasAta) tags.push({ key: 'hasAta', label: '已到港' })
  if (input.deliveryRisk === 'warning_soon') tags.push({ key: 'deliveryRisk', label: '即将超时' })
  if (input.deliveryRisk === 'overdue') tags.push({ key: 'deliveryRisk', label: '已超时' })
  if (input.deliveryRisk === 'severe_overdue') tags.push({ key: 'deliveryRisk', label: '严重超时' })
  return tags
}
