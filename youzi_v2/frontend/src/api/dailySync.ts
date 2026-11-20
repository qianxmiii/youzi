import { api } from '@/api/client'

export interface DailySyncStep {
  key: string
  label: string
  status: 'pending' | 'running' | 'done' | 'partial'
  attempt: number
  message?: string
  errors?: string[]
  stats?: Record<string, number>
  candidateCount?: number
  completedCount?: number
  pendingCount?: number
}
export interface DailySyncRun {
  id: string
  started: number
  start: string
  end: string
  status: 'queued' | 'running' | 'done' | 'partial' | 'waiting_authorization' | 'interrupted' | 'closed'
  message: string
  steps: DailySyncStep[]
  authorizationSaved?: boolean
}
export function getDailySync() {
  return api<{configured: boolean; run: DailySyncRun | null}>('/api/v1/daily-sync')
}
export function startDailySync(body: {authorization: string; resumeId?: string; start?: string | null; end?: string | null}) {
  return api<DailySyncRun>('/api/v1/daily-sync', {method: 'POST', body, retry: 0, timeout: 30_000})
}
export function closeDailySync(id: string) {
  return api<DailySyncRun>(`/api/v1/daily-sync/${encodeURIComponent(id)}/close`, {method:'POST',retry:0})
}
