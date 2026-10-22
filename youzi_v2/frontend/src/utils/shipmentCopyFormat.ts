import { SHIPMENT_STATUS_LABEL_ZH, normalizeShipmentStatusCode } from '@/constants/shipmentWorkspace'
import type { Shipment } from '@/types/shipment'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'
import { resolveLastMileTracking } from '@/utils/lastMileTracking'

/** 与 config/shipment_excel_columns.json 导出列顺序一致 */
export const SHIPMENT_DETAIL_COPY_HEADERS = [
  '运单号',
  '状态',
  '客户订单号',
  '关联单号',
  '货件号',
  '亚马逊预约号',
  '用户名',
  '件数',
  '国家',
  '派送仓库',
  '派送地址',
  '邮编',
  '渠道',
  '承运商',
  '转单号',
  '供应商',
  '品名',
  '收货仓',
  '内部轨迹时间',
  '内部最新轨迹',
] as const

const COUNTRY_CODE_TO_ZH: Record<string, string> = {
  US: '美国',
  CA: '加拿大',
  GB: '英国',
  DE: '德国',
  FR: '法国',
  EU: '欧洲',
  AU: '澳大利亚',
  JP: '日本',
}

function cell(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return ''
  const s = String(value).trim()
  return s.replace(/\t/g, ' ').replace(/\r?\n/g, ' ')
}

function countryLabel(code: string | null | undefined): string {
  const c = (code || '').trim().toUpperCase()
  if (!c) return ''
  return COUNTRY_CODE_TO_ZH[c] || c
}

function channelLabel(row: Shipment): string {
  const zh = row.channelNameZh?.trim()
  if (zh) return zh
  return row.channelCode?.trim() || ''
}

function internalTrackingForCopy(row: Shipment): { time: string; desc: string } {
  if (!hasEffectiveInternalTracking(row)) {
    return { time: '', desc: '' }
  }
  return {
    time: row.latestTrackingTime?.trim() || '',
    desc: row.latestTrackingDesc?.trim() || '',
  }
}

export function formatShipmentDetailTsvRow(row: Shipment): string {
  const code = normalizeShipmentStatusCode(row.statusCode) || 'UNKNOWN'
  const tracking = internalTrackingForCopy(row)
  const cells = [
    row.shipmentNo,
    SHIPMENT_STATUS_LABEL_ZH[code] || code,
    row.customerNo,
    row.refShipmentNo,
    row.customerShipmentId,
    row.amazonRefId,
    row.customer,
    row.ctns,
    countryLabel(row.countryCode),
    row.addressCode,
    row.deliveryAddress,
    row.zipcode,
    channelLabel(row),
    row.carrierNameZh?.trim() || row.carrierCode,
    row.trackingNumber,
    row.supplierName,
    row.productName,
    row.originWarehouseCode,
    tracking.time,
    tracking.desc,
  ]
  return cells.map(cell).join('\t')
}

/** 表头 + 多行 TSV，粘贴到 Excel 可还原为运单明细表 */
export function formatShipmentDetailsCopyText(rows: Shipment[]): string {
  if (!rows.length) return ''
  const header = SHIPMENT_DETAIL_COPY_HEADERS.join('\t')
  const body = rows.map((row) => formatShipmentDetailTsvRow(row))
  return [header, ...body].join('\n')
}

function formatCtnsForCopy(ctns: number | null | undefined): string {
  if (ctns === null || ctns === undefined) return ''
  return `${ctns}ctns`
}

function formatChargedWeightKgForCopy(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return ''
  const n = Number(value)
  if (Number.isInteger(n)) return String(n)
  return String(Number(n.toFixed(3)).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, ''))
}

/** 港前复制：英文客户 Chargeweight，中文客户 计费重 */
export function isEnglishShipmentCopyContext(row: Shipment): boolean {
  if (row.customerLang === 'en') return true
  if (row.customerLang === 'zh') return false
  const name = (row.customer || '').trim()
  if (!name) return false
  return !/[\u4e00-\u9fff]/.test(name)
}

export function formatChargedWeightCopyLine(row: Shipment): string {
  const kg = formatChargedWeightKgForCopy(row.chargedWeight ?? null)
  if (!kg) return ''
  if (isEnglishShipmentCopyContext(row)) {
    return `Chargeweight: ${kg}kg`
  }
  return `计费重: ${kg}kg`
}

function warehouseOrZipForCopy(row: Shipment): string {
  const warehouse = cell(row.addressCode)
  if (warehouse) return warehouse
  return cell(row.zipcode)
}

/** 用 ` = ` 连接非空片段；空值不产生多余等号 */
export function joinEqualsParts(
  parts: Array<string | number | null | undefined>,
): string {
  return parts.map(cell).filter(Boolean).join(' = ')
}

function normCopyKey(value: string): string {
  return value.trim().toUpperCase()
}

/** 关联单号、客户编号、货件号；关联单号与货件号相同（忽略大小写）只保留一处 */
export function shipmentDetailIdentifierPartsForCopy(row: Shipment): string[] {
  const ref = cell(row.refShipmentNo)
  const customerNo = cell(row.customerNo)
  const shipmentId = cell(row.customerShipmentId)
  const refSameAsShipment =
    Boolean(ref && shipmentId) && normCopyKey(ref) === normCopyKey(shipmentId)

  const parts: string[] = []
  const seen = new Set<string>()
  const add = (value: string) => {
    if (!value) return
    const key = normCopyKey(value)
    if (seen.has(key)) return
    seen.add(key)
    parts.push(value)
  }

  add(ref)
  add(customerNo)
  if (!refSameAsShipment) add(shipmentId)
  return parts
}

/** 单行：运单号 = [关联单号] [= 客户编号] [= 货件号] = 仓库（空则邮编）= Nctns */
export function formatShipmentDetailSummaryLine(row: Shipment): string {
  return joinEqualsParts([
    row.shipmentNo,
    ...shipmentDetailIdentifierPartsForCopy(row),
    warehouseOrZipForCopy(row),
    formatCtnsForCopy(row.ctns),
  ])
}

/** 运单明细摘要 + 可选第二行计费重（港前） */
export function formatShipmentDetailSummaryBlock(
  row: Shipment,
  options?: { appendChargedWeight?: boolean },
): string {
  const head = formatShipmentDetailSummaryLine(row)
  if (!options?.appendChargedWeight) return head
  const cw = formatChargedWeightCopyLine(row)
  return cw ? `${head}\n${cw}` : head
}

/** 转单号行：`-- FedEx 876457312498`；无转单号时返回空 */
export function formatShipmentTrackingNumberSuffixLine(row: Shipment): string {
  const info = resolveLastMileTracking(row)
  if (!info) return ''
  return `-- ${info.carrierLabel} ${info.number}`
}

/** 明细摘要 + 转单号（有则第二行 `-- 承运商 转单号`）；供「复制转单号」使用 */
export function formatShipmentDetailSummaryWithTrackingBlock(row: Shipment): string {
  const head = formatShipmentDetailSummaryLine(row)
  const tn = formatShipmentTrackingNumberSuffixLine(row)
  return tn ? `${head}\n${tn}` : head
}

/** 多行运单明细摘要（不含转单号），运单之间只换行 */
export function formatShipmentDetailSummaryCopyText(rows: Shipment[]): string {
  if (!rows.length) return ''
  return rows.map((row) => formatShipmentDetailSummaryLine(row)).join('\n')
}

/** 港前「复制 → 数据」：运单明细摘要 + 换行 + 计费重（无计费重仍保留摘要行） */
export function formatPreportShipmentDataCopyText(rows: Shipment[]): string {
  if (!rows.length) return ''
  return rows
    .map((row) => formatShipmentDetailSummaryBlock(row, { appendChargedWeight: true }))
    .join('\n\n')
}

/**
 * 「复制转单号」：沿用原运单明细规则（明细行 + 可选第二行 `-- 承运商 转单号`），
 * 运单之间空一行。
 */
export function formatShipmentTrackingNumbersCopyText(rows: Shipment[]): string {
  if (!rows.length) return ''
  return rows.map((row) => formatShipmentDetailSummaryWithTrackingBlock(row)).join('\n\n')
}
