import type { CarrierVesselOption } from '@/types/vesselSchedule'

/** 船名检索：防抖、最短前缀、缓存 TTL */
export const VESSEL_SEARCH_DEBOUNCE_MS = 500
export const VESSEL_SEARCH_MIN_PREFIX_LEN = 3
const CACHE_TTL_MS = 5 * 60 * 1000
const MAX_CACHE_ENTRIES = 80

interface CacheEntry {
  items: CarrierVesselOption[]
  expiresAt: number
}

const cache = new Map<string, CacheEntry>()

export function vesselSearchCacheKey(company: string, prefix: string): string {
  return `${company.trim().toUpperCase()}\u0000${prefix.trim().toUpperCase()}`
}

export function getCachedVesselSearch(
  company: string,
  prefix: string,
): CarrierVesselOption[] | null {
  const key = vesselSearchCacheKey(company, prefix)
  const entry = cache.get(key)
  if (!entry) return null
  if (Date.now() > entry.expiresAt) {
    cache.delete(key)
    return null
  }
  return entry.items
}

export function setCachedVesselSearch(
  company: string,
  prefix: string,
  items: CarrierVesselOption[],
): void {
  const key = vesselSearchCacheKey(company, prefix)
  if (cache.size >= MAX_CACHE_ENTRIES) {
    const oldest = cache.keys().next().value
    if (oldest) cache.delete(oldest)
  }
  cache.set(key, { items, expiresAt: Date.now() + CACHE_TTL_MS })
}

export function clearVesselSearchCache(company?: string): void {
  if (!company) {
    cache.clear()
    return
  }
  const prefix = company.trim().toUpperCase()
  for (const key of cache.keys()) {
    if (key.startsWith(`${prefix}\u0000`)) cache.delete(key)
  }
}
