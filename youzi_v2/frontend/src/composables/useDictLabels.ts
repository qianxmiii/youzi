import { computed, ref } from 'vue'
import { listDictByType } from '@/api/dict'

type DictCache = { byCode: Record<string, string>; byValue: Record<string, string> }

const caches = ref<Record<string, DictCache>>({})
const loadedTypes = new Set<string>()

function buildCache(items: { code: string; value: string }[]): DictCache {
  const byCode: Record<string, string> = {}
  const byValue: Record<string, string> = {}
  for (const item of items) {
    if (item.code) byCode[item.code.trim().toUpperCase()] = item.value || item.code
    if (item.value) byValue[item.value.trim()] = item.value
  }
  return { byCode, byValue }
}

export function useDictLabels() {
  async function loadDictTypes(...dictTypes: string[]) {
    const pending = dictTypes.filter((t) => t && !loadedTypes.has(t))
    if (!pending.length) return
    await Promise.all(
      pending.map(async (dictType) => {
        const res = await listDictByType(dictType)
        caches.value = { ...caches.value, [dictType]: buildCache(res.items) }
        loadedTypes.add(dictType)
      }),
    )
  }

  function dictLabel(dictType: string, raw: string | null | undefined): string {
    if (!raw?.trim()) return '—'
    const text = raw.trim()
    const cache = caches.value[dictType]
    if (!cache) return text
    return cache.byCode[text.toUpperCase()] || cache.byValue[text] || text
  }

  function dictOptions(dictType: string) {
    return computed(() => {
      const cache = caches.value[dictType]
      if (!cache) return []
      return Object.entries(cache.byCode)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([code, label]) => ({ label, value: code }))
    })
  }

  return { loadDictTypes, dictLabel, dictOptions }
}

/** @deprecated 使用 useDictLabels */
export function useCountryLabels() {
  const { loadDictTypes, dictLabel } = useDictLabels()
  return {
    loadCountryLabels: () => loadDictTypes('country_code'),
    countryLabel: (raw: string | null | undefined) => dictLabel('country_code', raw),
  }
}
