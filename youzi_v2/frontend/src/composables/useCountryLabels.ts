import { ref } from 'vue'
import { listDictByType } from '@/api/dict'

/** country_code → 中文名（及已是中文时的回显） */
const countryByCode = ref<Record<string, string>>({})
const countryByValue = ref<Record<string, string>>({})
let loaded = false

export function useCountryLabels() {
  async function loadCountryLabels() {
    if (loaded) return
    const res = await listDictByType('country_code')
    const byCode: Record<string, string> = {}
    const byValue: Record<string, string> = {}
    for (const item of res.items) {
      if (item.code) byCode[item.code.trim().toUpperCase()] = item.value || item.code
      if (item.value) byValue[item.value.trim()] = item.value
    }
    countryByCode.value = byCode
    countryByValue.value = byValue
    loaded = true
  }

  function countryLabel(raw: string | null | undefined): string {
    if (!raw?.trim()) return '—'
    const text = raw.trim()
    const upper = text.toUpperCase()
    return countryByCode.value[upper] || countryByValue.value[text] || text
  }

  return { loadCountryLabels, countryLabel }
}
