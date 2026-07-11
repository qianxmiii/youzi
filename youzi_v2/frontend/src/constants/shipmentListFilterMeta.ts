import type { ListShipmentsParams } from '@/api/shipments'
import type { TrackingFreshnessBucket } from '@/utils/trackingFreshness'

export const SHIPMENT_TIME_FIELD_OPTIONS = [
  { label: '创建时间', value: 'createdTime' },
  { label: 'ETD', value: 'etd' },
  { label: 'ATD', value: 'atd' },
  { label: 'ETA', value: 'eta' },
  { label: 'ATA', value: 'ata' },
  { label: '入仓时间', value: 'warehouseEntryTime' },
  { label: '预计送仓', value: 'expectedDeliveryTime' },
  { label: '签收时间', value: 'deliveredTime' },
  { label: '更新时间', value: 'updatedTime' },
] as const

export type ShipmentTimeField = (typeof SHIPMENT_TIME_FIELD_OPTIONS)[number]['value']

export const SHIPMENT_LIST_COLUMN_GROUPS = [
  {
    group: '基础信息',
    keys: [
      'customer',
      'channelCode',
      'addressCode',
      'zipcode',
      'carrierCode',
      'supplierName',
      'customerShipmentId',
      'amazonRefId',
      'ctns',
      'groups',
      'customerNo',
      'countryCode',
      'deliveryAddress',
      'productName',
      'originWarehouseCode',
      'paymentStatus',
    ],
  },
  {
    group: '时间节点',
    keys: ['warehouseEntryTime', 'etd', 'atd', 'eta', 'ata', 'expectedDeliveryTime', 'deliveredTime', 'createdTime'],
  },
  {
    group: '轨迹状态',
    keys: ['latestTracking', 'latestCarrier', 'staleDays', 'updatedTime'],
  },
  {
    group: '异常审批',
    keys: ['exceptionCode', 'exceptionDurationLabel'],
  },
] as const

export const SHIPMENT_COLUMN_LABELS: Record<string, string> = {
  statusCode: '状态',
  customer: '客户',
  channelCode: '渠道',
  addressCode: '派送仓库',
  zipcode: '邮编',
  carrierCode: '承运商',
  supplierName: '供应商',
  customerShipmentId: '货件号',
  amazonRefId: '亚马逊预约号',
  ctns: '件数',
  groups: '分组',
  customerNo: '客户编号',
  countryCode: '国家',
  deliveryAddress: '派送地址',
  productName: '品名',
  originWarehouseCode: '起运仓',
  paymentStatus: '付款状态',
  etd: 'ETD',
  atd: 'ATD',
  eta: 'ETA',
  ata: 'ATA',
  warehouseEntryTime: '入仓时间',
  expectedDeliveryTime: '预计送仓',
  deliveredTime: '签收时间',
  createdTime: '创建时间',
  latestTracking: '内部轨迹',
  latestCarrier: '承运商轨迹',
  staleDays: '未更新',
  updatedTime: '更新时间',
  exceptionCode: '异常状态',
  exceptionDurationLabel: '异常时长',
}

/** 与 shipment-list-filter-design.md 默认列一致（不含固定列运单号/状态/操作） */
export const DEFAULT_SHIPMENT_VISIBLE_COLUMNS = [
  'customer',
  'groups',
  'channelCode',
  'ctns',
  'paymentStatus',
  'addressCode',
  'zipcode',
  'carrierCode',
  'latestTracking',
  'latestCarrier',
  'customerNo',
  'customerShipmentId',
  'amazonRefId',
  'supplierName',
  'productName',
  'updatedTime',
] as const

export const SHIPMENT_COLUMN_STORAGE_KEY = 'youzi-shipment-list-columns-v3'

export type ShipmentSystemViewId =
  | 'warning_soon'
  | 'overdue_unsigned'
  | 'arrived_unsigned'
  | 'pending_tracking_review'

export interface ShipmentSystemView {
  id: ShipmentSystemViewId
  label: string
  description: string
}

export const SHIPMENT_SYSTEM_VIEWS: ShipmentSystemView[] = [
  {
    id: 'warning_soon',
    label: '即将超时',
    description: '预计送仓日在未来 3 天内且未签收',
  },
  {
    id: 'overdue_unsigned',
    label: '已超时未签收',
    description: '已过预计送仓日且未签收',
  },
  {
    id: 'arrived_unsigned',
    label: '已到港未签收',
    description: '已有 ATA 且未签收',
  },
  {
    id: 'pending_tracking_review',
    label: '待签收时间审批',
    description: '存在待审批的签收时间候选',
  },
]

/** 系统视图对应的 API 筛选（会覆盖部分当前条件） */
export function systemViewFilters(id: ShipmentSystemViewId): Partial<ListShipmentsParams> {
  switch (id) {
    case 'warning_soon':
      return { deliveryRisk: 'warning_soon', notDelivered: true, statusCode: undefined }
    case 'overdue_unsigned':
      return { deliveryRisk: 'overdue', notDelivered: true, statusCode: undefined }
    case 'arrived_unsigned':
      return { hasAta: true, notDelivered: true, statusCode: undefined }
    case 'pending_tracking_review':
      return { pendingTrackingTimeReview: true, statusCode: undefined }
    default:
      return {}
  }
}

export interface ShipmentAdvancedTimeRanges {
  etd: [number, number] | null
  atd: [number, number] | null
  eta: [number, number] | null
  ata: [number, number] | null
  expectedDelivery: [number, number] | null
  delivered: [number, number] | null
  created: [number, number] | null
  updated: [number, number] | null
}

export function emptyAdvancedTimeRanges(): ShipmentAdvancedTimeRanges {
  return {
    etd: null,
    atd: null,
    eta: null,
    ata: null,
    expectedDelivery: null,
    delivered: null,
    created: null,
    updated: null,
  }
}

export type ShipmentFilterSummaryContext = {
  statusLabel: Record<string, string>
  countryLabel: (code: string | null | undefined) => string
  carrierLabel: (code: string | null | undefined) => string
  channelLabel: (code: string | null | undefined) => string
  groupLabel: (id: string | null | undefined) => string
  exceptionLabel: (code: string | null | undefined) => string
  freshnessLabel: Record<TrackingFreshnessBucket, string>
}
