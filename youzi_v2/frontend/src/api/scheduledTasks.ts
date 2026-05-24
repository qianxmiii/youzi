import { api } from '@/api/client'
import type {
  ScheduledSyncRunResult,
  ScheduledSyncSettingsUpdate,
  ScheduledTaskConfig,
  ScheduledTaskOverview,
  TrackingSyncJobListResponse,
} from '@/types/scheduledTasks'

export async function getScheduledTasksOverview(): Promise<ScheduledTaskOverview> {
  return api<ScheduledTaskOverview>('/api/v1/scheduled-tasks/overview')
}

export async function updateScheduledTasksSettings(
  body: ScheduledSyncSettingsUpdate,
): Promise<ScheduledTaskConfig> {
  return api<ScheduledTaskConfig>('/api/v1/scheduled-tasks/settings', {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export async function listScheduledTaskJobs(params?: {
  source?: string
  limit?: number
  offset?: number
}): Promise<TrackingSyncJobListResponse> {
  const q = new URLSearchParams()
  if (params?.source) q.set('source', params.source)
  if (params?.limit != null) q.set('limit', String(params.limit))
  if (params?.offset != null) q.set('offset', String(params.offset))
  const suffix = q.toString() ? `?${q}` : ''
  return api<TrackingSyncJobListResponse>(`/api/v1/scheduled-tasks/jobs${suffix}`)
}

export async function runScheduledInternalSync(): Promise<ScheduledSyncRunResult> {
  return api<ScheduledSyncRunResult>('/api/v1/scheduled-tasks/run-internal-sync', {
    method: 'POST',
  })
}

export async function runScheduledCarrierSync(): Promise<ScheduledSyncRunResult> {
  return api<ScheduledSyncRunResult>('/api/v1/scheduled-tasks/run-carrier-sync', {
    method: 'POST',
  })
}

export async function runScheduledTrackingSync(): Promise<ScheduledSyncRunResult> {
  return api<ScheduledSyncRunResult>('/api/v1/scheduled-tasks/run-tracking-sync', {
    method: 'POST',
  })
}
