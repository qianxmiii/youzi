export type MaritimeStatus =
  | 'departed'
  | 'arrived'
  | 'arriving_soon'
  | 'departing_soon'
  | 'in_transit'
  | 'planned'
  | 'unknown'

export interface VoyagePortCall {
  id?: string
  voyageId?: string
  /** 船公司/接口原始港口名，入库字段 */
  portName: string
  /** 以下由 port_codes 码表解析，仅展示 */
  portCode?: string | null
  portCnname?: string | null
  portNameEn?: string | null
  sequence: number
  eta: string | null
  ata: string | null
  etd: string | null
  atd: string | null
  status?: MaritimeStatus
  statusLabel?: string
  createdTime?: string
  updatedTime?: string
  /** 最近一次变更的时间字段：eta / ata / etd / atd */
  timeFieldsUpdated?: string[]
  /** 是否已订阅到港通知 */
  subscribed?: boolean
}

export interface VesselVoyageSummary {
  id: string
  vesselVoyage: string
  vesselName: string | null
  voyageNo: string | null
  vesselCode: string | null
  shippingCompany: string | null
  notes: string
  portCount?: number
  shipmentCount?: number
  createdTime: string
  updatedTime: string
}

export interface ShipmentSummary {
  arrivingSoon: number
  departingSoon: number
  arrived: number
  inTransit: number
  planned: number
  unknown: number
}

export interface VesselVoyageDetail extends VesselVoyageSummary {
  portCalls: VoyagePortCall[]
  shipmentSummary?: ShipmentSummary
}

export interface VesselVoyageListResponse {
  items: VesselVoyageSummary[]
  total: number
  limit: number
  offset: number
}

export interface VesselVoyagePayload {
  vesselVoyage?: string | null
  vesselName?: string | null
  voyageNo?: string | null
  vesselCode?: string | null
  shippingCompany?: string | null
  notes?: string
  portCalls: Array<{
    id?: string
    portName: string
    sequence: number
    eta?: string | null
    ata?: string | null
    etd?: string | null
    atd?: string | null
  }>
}

export interface VoyageImportResult {
  created: number
  updated: number
  failed: number
  errors: Array<{ row: number; message: string }>
}

export interface MaritimeScheduleProviderInfo {
  id: string
  shippingCompany: string
  label: string
  aliases: string[]
  features?: {
    vesselSearch?: boolean
  }
}

export interface CarrierVesselOption {
  vesselCode: string
  vesselName: string
  label: string
}

export interface CarrierVesselSearchResponse {
  items: CarrierVesselOption[]
}

export interface MaritimeScheduleProvidersResponse {
  items: MaritimeScheduleProviderInfo[]
}

export interface ExternalSchedulePreview {
  vesselVoyage: string
  vesselName: string | null
  voyageNo: string | null
  vesselCode: string | null
  shippingCompany: string
  notes: string
  portCalls: Array<{
    portName: string
    sequence: number
    eta: string | null
    ata: string | null
    etd: string | null
    atd: string | null
  }>
  source?: {
    provider: string
    shippingCompany: string
    vesselCode: string
    period: number
    rowCount: number
  }
}

export interface ExternalScheduleSyncResult {
  voyage: VesselVoyageDetail
  created: boolean
  source?: ExternalSchedulePreview['source']
}

export interface VoyageShipment extends Record<string, unknown> {
  shipmentNo: string
  customer: string | null
  customerNo: string | null
  vesselVoyage: string | null
  eta: string | null
  ata: string | null
  etd: string | null
  atd: string | null
  originPortCode: string | null
  destinationPortCode: string | null
  maritimeStatus?: MaritimeStatus
  maritimeStatusLabel?: string
}

export interface VoyageShipmentListResponse {
  items: VoyageShipment[]
  total: number
  limit: number
  offset: number
}

export const MARITIME_STATUS_OPTIONS: Array<{ label: string; value: MaritimeStatus | '' }> = [
  { label: '全部状态', value: '' },
  { label: '三天内到港', value: 'arriving_soon' },
  { label: '三天内离港', value: 'departing_soon' },
  { label: '已到港', value: 'arrived' },
  { label: '已离港/在途', value: 'in_transit' },
  { label: '计划中', value: 'planned' },
  { label: '待更新', value: 'unknown' },
]

export function maritimeStatusTagType(
  status?: MaritimeStatus,
): 'default' | 'info' | 'success' | 'warning' | 'error' {
  if (status === 'arriving_soon' || status === 'departing_soon') return 'warning'
  if (status === 'arrived') return 'success'
  if (status === 'in_transit' || status === 'departed') return 'info'
  if (status === 'unknown') return 'error'
  return 'default'
}
