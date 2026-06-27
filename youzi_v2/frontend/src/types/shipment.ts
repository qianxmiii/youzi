import type { ShipmentGroupSummary } from '@/types/shipmentGroup'

export interface Shipment {
  id: string
  shipmentNo: string
  customer: string | null
  /** 客户名在 VIP 客户表中 */
  isVip?: boolean
  /** 客户语言（zh/en），用于 UPS/FedEx 等官网跳转 */
  customerLang?: 'zh' | 'en'
  customerNo: string | null
  channelCode: string | null
  channelNameZh?: string | null
  channelCategory?: string | null
  countryCode: string | null
  addressType: 'AMZ' | 'WFS' | '3PL' | string | null
  addressCode: string | null
  deliveryAddress: string | null
  ctns: number | null
  zipcode: string | null
  productName: string | null
  originWarehouseCode: string | null
  supplierName: string | null
  carrierCode: string | null
  carrierId: string | null
  trackingNumber: string | null
  /** 尾程快递：UPS/FEDEX/DPD/CWE 等，优先于单号自动识别跳转 */
  expressCode?: string | null
  customerShipmentId: string | null
  amazonRefId: string | null
  vesselName: string | null
  voyageNo: string | null
  vesselVoyage: string | null
  etd: string | null
  eta: string | null
  atd: string | null
  ata: string | null
  originPortCode: string | null
  destinationPortCode: string | null
  expectedDeliveryTime: string | null
  deliveredTime: string | null
  statusCode: string | null
  exceptionCode: string | null
  exceptionOpenedTime: string | null
  exceptionDurationSeconds: number | null
  exceptionDurationLabel: string | null
  latestTrackingTime: string | null
  latestTrackingDesc: string | null
  trackingLogCount: number
  latestCarrierTime: string | null
  latestCarrierDesc: string | null
  carrierLogCount: number
  createdTime: string
  updatedTime: string
  /** 是否已订阅轨迹更新（内部/承运商最新轨迹变更时提醒） */
  subscribed?: boolean
  /** 签收时间存在待轨迹审批候选 */
  hasPendingSignedTimeReview?: boolean
  /** 所属分组（只读，来自 shipment_group_members） */
  groups?: ShipmentGroupSummary[]
}

export type ShipmentPayload = Partial<
  Omit<Shipment, 'id' | 'createdTime' | 'updatedTime'>
> & {
  shipmentNo: string
}

export interface ShipmentListResponse {
  items: Shipment[]
  total: number
  limit: number
  offset: number
}

export interface ShipmentExceptionType {
  code: string
  nameZh: string
}

export interface ShipmentExceptionEvent {
  id: string
  shipmentNo: string
  exceptionCode: string
  openedTime: string
  closedTime: string | null
  note: string | null
  durationSeconds: number | null
  durationLabel: string
  createdTime: string
  updatedTime: string
}

export interface ShipmentExceptionBatchResult {
  ok: boolean
  opened?: number
  closed?: number
  skipped: { shipmentNo: string; message: string }[]
  errors: { shipmentNo: string; message: string }[]
}

export interface ShipmentBatchItemError {
  id?: string
  shipmentNo?: string
  message: string
}

export interface ShipmentBatchResult {
  total: number
  updated?: number
  deleted?: number
  skipped: ShipmentBatchItemError[]
  errors: ShipmentBatchItemError[]
}

export interface ShipmentImportResult {
  ok: boolean
  totalRows: number
  created: number
  updated: number
  failed: number
  errors: { row?: number; message: string; shipmentNo?: string }[]
  /** Excel 表头中未配置映射、已忽略的列名 */
  skippedColumns?: string[]
  groupsCreated?: number
  groupsTouched?: number
  membersAdded?: number
  groupErrors?: { row?: number; message: string; shipmentNo?: string; groupNo?: string }[]
}

export function emptyShipmentForm(): ShipmentPayload {
  return {
    shipmentNo: '',
    customer: null,
    customerNo: null,
    channelCode: null,
    countryCode: null,
    addressType: null,
    addressCode: null,
    deliveryAddress: null,
    ctns: null,
    zipcode: null,
    productName: null,
    originWarehouseCode: null,
    supplierName: null,
    carrierCode: null,
    carrierId: null,
    trackingNumber: null,
    expressCode: null,
    customerShipmentId: null,
    amazonRefId: null,
    vesselName: null,
    voyageNo: null,
    vesselVoyage: null,
    etd: null,
    eta: null,
    atd: null,
    ata: null,
    originPortCode: null,
    destinationPortCode: null,
    expectedDeliveryTime: null,
    deliveredTime: null,
    statusCode: 'IN_TRANSIT',
  }
}

export function shipmentToForm(row: Shipment): ShipmentPayload {
  return {
    shipmentNo: row.shipmentNo,
    customer: row.customer,
    customerNo: row.customerNo,
    channelCode: row.channelCode,
    countryCode: row.countryCode,
    addressType: row.addressType,
    addressCode: row.addressCode,
    deliveryAddress: row.deliveryAddress,
    ctns: row.ctns,
    zipcode: row.zipcode,
    productName: row.productName,
    originWarehouseCode: row.originWarehouseCode,
    supplierName: row.supplierName,
    carrierCode: row.carrierCode,
    carrierId: row.carrierId,
    trackingNumber: row.trackingNumber,
    expressCode: row.expressCode ?? null,
    customerShipmentId: row.customerShipmentId,
    amazonRefId: row.amazonRefId,
    vesselName: row.vesselName,
    voyageNo: row.voyageNo,
    vesselVoyage: row.vesselVoyage,
    etd: row.etd,
    eta: row.eta,
    atd: row.atd,
    ata: row.ata,
    originPortCode: row.originPortCode,
    destinationPortCode: row.destinationPortCode,
    expectedDeliveryTime: row.expectedDeliveryTime,
    deliveredTime: row.deliveredTime,
    statusCode: row.statusCode,
  }
}
