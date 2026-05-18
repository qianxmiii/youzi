import { ofetch } from 'ofetch'

export const api = ofetch.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
})

export interface HealthResponse {
  ok: boolean
  service?: string
  version?: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  return api<HealthResponse>('/api/v1/health')
}

export async function fetchLegacyHealth(): Promise<HealthResponse> {
  return api<HealthResponse>('/api/health')
}
