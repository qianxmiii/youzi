import { api } from './client'

export interface Channel {
  code: string
  nameZh: string
  nameEn: string
  country: string
  category: string
  note: string
  sortOrder: number
  isActive: boolean
  createdTime: string
  updatedTime: string
}

export interface ChannelListResponse {
  items: Channel[]
  total: number
  limit: number
  offset: number
}

export interface ChannelPayload {
  code: string
  nameZh: string
  nameEn?: string
  country: string
  category: string
  note?: string
  sortOrder?: number
  isActive?: boolean
}

export interface ChannelSeedResult {
  inserted: number
  updated: number
  total: number
}

export async function getChannelMeta(): Promise<{ categories: string[] }> {
  return api<{ categories: string[] }>('/api/v1/channels/meta')
}

export async function listChannels(params?: {
  search?: string
  country?: string
  category?: string
  activeOnly?: boolean
  limit?: number
  offset?: number
}): Promise<ChannelListResponse> {
  const q: Record<string, string | number | boolean> = {}
  if (params?.search) q.search = params.search
  if (params?.country) q.country = params.country
  if (params?.category) q.category = params.category
  if (params?.activeOnly !== undefined) q.activeOnly = params.activeOnly
  if (params?.limit !== undefined) q.limit = params.limit
  if (params?.offset !== undefined) q.offset = params.offset
  return api<ChannelListResponse>('/api/v1/channels', { query: q })
}

export async function seedDefaultChannels(): Promise<ChannelSeedResult> {
  return api<ChannelSeedResult>('/api/v1/channels/seed-defaults', { method: 'POST' })
}

export async function createChannel(payload: ChannelPayload): Promise<Channel> {
  return api<Channel>('/api/v1/channels', {
    method: 'POST',
    body: payload,
  })
}

export async function updateChannel(
  code: string,
  payload: Partial<Omit<ChannelPayload, 'code'>>,
): Promise<Channel> {
  return api<Channel>(`/api/v1/channels/${encodeURIComponent(code)}`, {
    method: 'PATCH',
    body: payload,
  })
}

export async function deleteChannel(code: string): Promise<void> {
  await api(`/api/v1/channels/${encodeURIComponent(code)}`, { method: 'DELETE' })
}
