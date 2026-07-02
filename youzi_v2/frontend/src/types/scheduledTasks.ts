export interface ScheduledTaskConfig {

  internalEnabled: boolean

  internalIntervalHours: number

  carrierEnabled: boolean

  carrierIntervalHours: number

  initialDelaySec: number

  lastInternalFinished: string | null

  lastCarrierFinished: string | null

  groupAutoArchiveEnabled?: boolean

  groupAutoArchiveLastFinished?: string | null

  zipcodeBackfillEnabled?: boolean

  zipcodeBackfillLastFinished?: string | null

  dpsShipmentSyncEnabled?: boolean

  dpsShipmentSyncTransitTimeStart?: string | null

  dpsShipmentSyncTransitTimeEnd?: string | null

  dpsShipmentSyncTransitTimeStartDefault?: string | null

  dpsShipmentSyncTransitTimeEndDefault?: string | null

  dpsShipmentSyncTransitTimeStartEffective?: string | null

  dpsShipmentSyncTransitTimeEndEffective?: string | null

  dpsShipmentSyncLastFinished?: string | null

  exceptionFollowupEnabled?: boolean

  exceptionFollowupLastFinished?: string | null

  schedulerActive: boolean

  scriptPath?: string

  pollIntervalSec?: number

}



export interface ScheduledSyncSettingsUpdate {

  internalEnabled: boolean

  internalIntervalHours: number

  carrierEnabled: boolean

  carrierIntervalHours: number

  initialDelaySec: number

  groupAutoArchiveEnabled?: boolean

  zipcodeBackfillEnabled?: boolean

  dpsShipmentSyncEnabled?: boolean

  dpsShipmentSyncTransitTimeStart?: string | null

  dpsShipmentSyncTransitTimeEnd?: string | null

  exceptionFollowupEnabled?: boolean

}



export interface BuiltinScheduledTask {

  id: string

  name: string

  source: string

  schedule: string

  description: string

}



export interface TrackingSyncDailySlice {

  source: string

  updatedShipments: number

  newLogCount: number

  jobCount: number

  lastFinished: string | null

}



export interface ScheduledTaskOverview {

  config: ScheduledTaskConfig

  internalToday: TrackingSyncDailySlice

  carrierToday: TrackingSyncDailySlice

  tasks: BuiltinScheduledTask[]

}



export interface TrackingSyncJobRecord {

  id: string

  source: string

  triggerType: string

  status: string

  totalShipments: number

  updatedShipments: number

  newLogCount: number

  skipped: number

  emptyCount: number

  notFound: number

  errorCount: number

  errors: string[]

  startedTime: string

  finishedTime: string | null

}



export interface TrackingSyncJobListResponse {

  items: TrackingSyncJobRecord[]

  total: number

  limit: number

  offset: number

}



export interface ExceptionFollowupRunResult {
  skipped: boolean
  reason?: string | null
  scanned: number
  created: number
}

export interface ScheduledSyncRunResult {

  skipped: boolean

  reason?: string | null

  internal?: Record<string, unknown> | null

  carrier?: Record<string, unknown> | null

}



export interface GroupAutoArchiveRunResult {

  skipped: boolean

  reason?: string | null

  total: number

  archived: number

  groupIds: string[]

}



export interface ZipcodeBackfillRunResult {

  skipped: boolean

  reason?: string | null

  total: number

  updated: number

  unmatched: number

}



export interface ShipmentDpsSyncRunRequest {

  transitTimeStart?: string | null

  transitTimeEnd?: string | null

}



export interface ShipmentDpsSyncRunResult {

  skipped: boolean

  reason?: string | null

  error?: string | null

  transitTimeStart?: string | null

  transitTimeEnd?: string | null

  remoteTotal?: number

  total: number

  created: number

  updated: number

  failed: number

  pages?: number

  errors?: string[]

}

