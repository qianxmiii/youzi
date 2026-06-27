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
