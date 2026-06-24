export interface TrackingLog {
  id: string
  shipmentNo: string
  trackingTime: string
  trackingDesc: string
  createdTime: string
}

export interface TrackingLogListResponse {
  items: TrackingLog[]
  total: number
  limit: number
  offset: number
}

export interface TrackingSyncResult {
  total: number
  updated: number
  skipped: number
  empty: number
  notFound: number
  logCount: number
  errors: string[]
  batchSize: number
  batches: number
  jobId?: string
  unassigned?: number
  excludedNotInTransit?: number
  groupAlertsEvaluated?: number
  groupAlertsCreated?: number
  logs?: string[]
}

export interface TrackingSyncDailyStats {
  source: string
  updatedShipments: number
  newLogCount: number
  jobCount: number
  lastFinished: string | null
}

export interface CarrierTrackingLog {
  id: string
  shipmentNo: string
  vendorName: string
  carrierCode: string
  trackingTime: string
  trackingDesc: string
  vendorEventId?: string | null
  createdTime: string
}
