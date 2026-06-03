import type { Shipment } from '@/types/shipment'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'

/** 与 config/shipment_excel_columns.json 导出列顺序一致 */
export const SHIPMENT_DETAIL_COPY_HEADERS = [
  '运单号',
  '状态',
  '客户订单号',
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
    row.customerShipmentId,
    row.amazonRefId,
    row.customer,
    row.ctns,
    countryLabel(row.countryCode),
    row.addressCode,
    row.deliveryAddress,
    row.zipcode,
    channelLabel(row),
    row.carrierCode,
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
