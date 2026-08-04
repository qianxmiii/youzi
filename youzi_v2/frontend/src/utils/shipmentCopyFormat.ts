import type { Shipment } from '@/types/shipment'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'

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
  '交货仓库',
  '内部轨迹时间',
  '内部最新轨迹',
] as const

const STATUS_LABEL: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

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
  const code = (row.statusCode || 'UNKNOWN').trim().toUpperCase()
  const tracking = internalTrackingForCopy(row)
  const cells = [
    row.shipmentNo,
    STATUS_LABEL[code] || code,
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

/** 单行：运单号 = 货件号 = 派送仓库（空则邮编）= 件数ctns（缺段跳过） */
export function formatShipmentDetailSummaryLine(row: Shipment): string {
  return joinEqualsParts([
    row.shipmentNo,
    row.customerShipmentId,
    warehouseOrZipForCopy(row),
    formatCtnsForCopy(row.ctns),
  ])
}

/** 单行：运单号 = 关联单号 = 客户编号 = 货件号 = 派送仓库（空则邮编）= 件数ctns（缺段跳过） */
export function formatShipmentDetailSummaryWithCustomerNoLine(row: Shipment): string {
  return joinEqualsParts([
    row.shipmentNo,
    row.refShipmentNo,
    row.customerNo,
    row.customerShipmentId,
    warehouseOrZipForCopy(row),
    formatCtnsForCopy(row.ctns),
  ])
}

/** 多行运单明细摘要，每行一条运单 */
export function formatShipmentDetailSummaryCopyText(rows: Shipment[]): string {
  if (!rows.length) return ''
  return rows.map((row) => formatShipmentDetailSummaryLine(row)).join('\n')
}

/** 多行运单明细（含关联单号 / 客户编号），每行一条运单 */
export function formatShipmentDetailSummaryWithCustomerNoCopyText(rows: Shipment[]): string {
  if (!rows.length) return ''
  return rows.map((row) => formatShipmentDetailSummaryWithCustomerNoLine(row)).join('\n')
}
