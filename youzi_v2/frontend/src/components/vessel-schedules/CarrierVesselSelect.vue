<script setup lang="ts">
import { NSelect } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { searchCarrierVessels } from '@/api/vesselSchedules'
import type { CarrierVesselOption } from '@/types/vesselSchedule'
import {
  VESSEL_SEARCH_DEBOUNCE_MS,
  VESSEL_SEARCH_MIN_PREFIX_LEN,
  clearVesselSearchCache,
  getCachedVesselSearch,
  setCachedVesselSearch,
  vesselSearchCacheKey,
} from '@/utils/carrierVesselSearchCache'

const props = defineProps<{
  shippingCompany: string | null | undefined
  vesselCode: string | null | undefined
  vesselName: string | null | undefined
  enabled: boolean
  placeholder?: string
  size?: 'small' | 'medium' | 'large'
}>()

const emit = defineEmits<{
  'update:vesselCode': [value: string | null]
  'update:vesselName': [value: string | null]
}>()

const loading = ref(false)
const options = ref<CarrierVesselOption[]>([])
let searchTimer: ReturnType<typeof setTimeout> | null = null
let abortController: AbortController | null = null
let inflightKey: string | null = null

const selectValue = computed({
  get: () => props.vesselCode || null,
  set: (code: string | null) => {
    const picked = options.value.find((o) => o.vesselCode === code)
    emit('update:vesselCode', code)
    emit('update:vesselName', picked?.vesselName ?? props.vesselName ?? null)
  },
})

function mapOptions(items: CarrierVesselOption[]) {
  return items.map((item) => ({
    label: item.label,
    value: item.vesselCode,
  }))
}

function withCurrentSelection(items: CarrierVesselOption[]): CarrierVesselOption[] {
  if (!props.vesselCode || !props.vesselName) return items
  if (items.some((x) => x.vesselCode === props.vesselCode)) return items
  return [
    {
      vesselCode: props.vesselCode,
      vesselName: props.vesselName,
      label: `${props.vesselName}（${props.vesselCode}）`,
    },
    ...items,
  ]
}

function applyOptions(items: CarrierVesselOption[]) {
  options.value = withCurrentSelection(items)
}

function cancelInflight() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  inflightKey = null
}

async function runSearch(query: string) {
  const company = (props.shippingCompany || '').trim()
  const q = query.trim()
  if (!props.enabled || !company || q.length < VESSEL_SEARCH_MIN_PREFIX_LEN) {
    cancelInflight()
    options.value = []
    return
  }

  const key = vesselSearchCacheKey(company, q)
  const cached = getCachedVesselSearch(company, q)
  if (cached) {
    cancelInflight()
    applyOptions(cached)
    return
  }

  if (inflightKey === key) return

  cancelInflight()
  abortController = new AbortController()
  inflightKey = key
  loading.value = true

  try {
    const res = await searchCarrierVessels(company, q, abortController.signal)
    setCachedVesselSearch(company, q, res.items)
    if (inflightKey === key) {
      applyOptions(res.items)
    }
  } catch (e) {
    const aborted =
      (e instanceof Error && e.name === 'AbortError') ||
      (typeof e === 'object' && e !== null && (e as { name?: string }).name === 'AbortError')
    if (!aborted) {
      options.value = []
    }
  } finally {
    if (inflightKey === key) {
      inflightKey = null
      loading.value = false
    }
  }
}

function handleSearch(query: string) {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    void runSearch(query)
  }, VESSEL_SEARCH_DEBOUNCE_MS)
}

watch(
  () => props.shippingCompany,
  (company, prev) => {
    cancelInflight()
    if (searchTimer) clearTimeout(searchTimer)
    options.value = []
    if (prev && prev !== company) {
      clearVesselSearchCache(prev)
    }
  },
)

watch(
  () => [props.vesselCode, props.vesselName, props.enabled] as const,
  ([code, name, enabled]) => {
    if (!enabled || !code || !name) return
    if (!options.value.some((o) => o.vesselCode === code)) {
      options.value = [
        {
          vesselCode: code,
          vesselName: name,
          label: `${name}（${code}）`,
        },
      ]
    }
  },
  { immediate: true },
)
</script>

<template>
  <NSelect
    v-model:value="selectValue"
    :options="mapOptions(options)"
    filterable
    remote
    clearable
    :loading="loading"
    :disabled="!enabled || !shippingCompany"
    :placeholder="
      placeholder || `输入至少 ${VESSEL_SEARCH_MIN_PREFIX_LEN} 个字符检索船名`
    "
    :size="size"
    @search="handleSearch"
  />
</template>
