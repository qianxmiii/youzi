import { api } from '@/api/client'
import type { DictListResponse } from '@/types/dict'

export async function listDictByType(dictType: string): Promise<DictListResponse> {
  return api<DictListResponse>(`/api/v1/dict/${encodeURIComponent(dictType)}`)
}
