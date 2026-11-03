export interface WarehouseMatch {
  warehouseCode: string
  postalCode: string
  countryCode: string
}

export interface WarehouseSearchResult {
  status: 'ok' | 'skipped' | 'unavailable'
  items: WarehouseMatch[]
  hasMore: boolean
}

export function exactWarehouseMatch(query: string, result: WarehouseSearchResult): WarehouseMatch | null {
  if (result.status !== 'ok' || result.hasMore) return null
  const matches = result.items.filter(item => item.warehouseCode.trim().toUpperCase() === query.trim().toUpperCase())
  const unique = new Map(matches.map(item => [JSON.stringify([item.postalCode, item.countryCode.toUpperCase()]), item]))
  const match = unique.size === 1 ? [...unique.values()][0] : null
  return match?.postalCode ? match : null
}

// Invalidating on edits also covers the debounce interval before the next request.
export function createWarehouseSearch(lookup: (query: string) => Promise<WarehouseSearchResult>) {
  let revision = 0
  return {
    invalidate() { revision++ },
    async run(query: string) {
      const request = ++revision
      try {
        const result = await lookup(query)
        return request === revision ? result : null
      } catch {
        return request === revision ? { status: 'unavailable', items: [], hasMore: false } as WarehouseSearchResult : null
      }
    },
  }
}
