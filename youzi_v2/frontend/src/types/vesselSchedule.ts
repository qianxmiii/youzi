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
  portName: string
  sequence: number
  eta: string | null
  ata: string | null
  etd: string | null
  atd: string | null
  status?: MaritimeStatus
  statusLabel?: string
  createdTime?: string
  updatedTime?: string
}

export interface VesselVoyageSummary {
  id: string
  vesselVoyage: string
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
  vesselVoyage: string
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
