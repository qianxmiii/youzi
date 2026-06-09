import { api } from '@/api/client'

export interface WorldClockZone {
  tz: string
  label: string
}

export interface WorldClocksSettings {
  enabled: boolean
  use24h: boolean
  zones: WorldClockZone[]
}

export async function getWorldClocksSettings(): Promise<WorldClocksSettings> {
  return api<WorldClocksSettings>('/api/v1/settings/world-clocks')
}

export async function updateWorldClocksSettings(
  payload: WorldClocksSettings,
): Promise<WorldClocksSettings> {
  return api<WorldClocksSettings>('/api/v1/settings/world-clocks', {
    method: 'PUT',
    body: payload,
  })
}
