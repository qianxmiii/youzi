import { api } from '@/api/client'

export type BillState = '' | 'unbound' | 'review' | 'planned' | 'departed' | 'arrived' | 'inspection' | 'delivered'
export type BillDeliveryScope = 'all' | 'open' | 'delivered'

export interface CustomsEvidence {
  shipmentNo: string
  status: 'inspection' | 'released'
  time: string | null
  description: string
}

interface BillShipment {
  id: string
  shipmentNo: string
  customer: string | null
  channelCode: string | null
  channelNameZh: string | null
  addressCode: string | null
  routeStatus: string | null
  vesselVoyage: string | null
  latestTrackingTime: string | null
  latestTrackingDesc: string | null
}

interface BillContainer {
  containerNo: string | null
  unassigned: boolean
  shipmentCount: number
  customs: Record<'export' | 'import', CustomsEvidence | null>
}

export interface BillBinding {
  voyageId: string
  vesselVoyage: string | null
  originCallId: string
  destinationCallId: string
  originPort: string | null
  destinationPort: string | null
  etd: string | null
  atd: string | null
  eta: string | null
  ata: string | null
  needsReview: boolean
}

export interface BillOfLading {
  billNo: string
  shipmentCount: number
  countries: string[]
  deliveredCount: number
  originPorts?: string[]
  destinationPorts?: string[]
  binding: BillBinding | null
  state: Exclude<BillState, '' | 'inspection' | 'delivered'>
  hasInspection: boolean
  containers: BillContainer[]
}

export interface BillDetail extends BillOfLading {
  containers: Array<BillContainer & { shipments: BillShipment[] }>
}

const endpoint = '/api/v1/bills-of-lading'
type BillPortOption = { value: string; label: string }
export type BillPortOptions = { origins: BillPortOption[]; destinations: BillPortOption[] }

export function listBillsOfLading(query: {
  country: string
  search?: string
  state?: BillState
  limit: number
  offset: number
  voyage_id?: string
  port_call_id?: string
  origin_port?: string
  destination_port?: string
  delivery_scope?: BillDeliveryScope
}) {
  return api<{
    items: BillOfLading[]
    total: number
    portOptions: BillPortOptions
  }>(endpoint, { query })
}

export function getBillOfLading(billNo: string) {
  return api<BillDetail>(`${endpoint}/detail`, { query: { bill_no: billNo } })
}

export function bindBillOfLading(billNo: string, voyageId: string | null, originCallId: string | null, destinationCallId: string | null) {
  return api<BillDetail>(`${endpoint}/binding`, {
    method: 'PUT', query: { bill_no: billNo }, body: { voyageId, originCallId, destinationCallId }, retry: 0,
  })
}
