<script setup lang="ts">
import { NButton, NSpin, NTabPane, NTabs } from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { getShipmentCarrierTrackingLogs, getShipmentTrackingLogs } from '@/api/shipments'
import type { CarrierTrackingLog } from '@/types/tracking'

const props = withDefaults(
  defineProps<{
    shipmentId: string
    /** drawer：默认加载全部轨迹，由抽屉自身滚动 */
    mode?: 'compact' | 'drawer'
    initialTab?: 'internal' | 'carrier'
  }>(),
  {
    mode: 'compact',
    initialTab: 'internal',
  },
)

type LogRow = { id: string; trackingTime: string; trackingDesc: string; vendorName?: string }

const activeTab = ref<'internal' | 'carrier'>(props.initialTab)
const loading = ref(false)
const logs = ref<LogRow[]>([])
const total = ref(0)
const showAll = ref(props.mode === 'drawer')

const PREVIEW = 3
const isDrawer = computed(() => props.mode === 'drawer')

async function load() {
  loading.value = true
  try {
    const limit = showAll.value || isDrawer.value ? 200 : PREVIEW
    if (activeTab.value === 'internal') {
      const res = await getShipmentTrackingLogs(props.shipmentId, { limit, offset: 0 })
      logs.value = res.items
      total.value = res.total
    } else {
      const res = await getShipmentCarrierTrackingLogs(props.shipmentId, { limit, offset: 0 })
      logs.value = (res.items as CarrierTrackingLog[]).map((item) => ({
        id: item.id,
        trackingTime: item.trackingTime,
        trackingDesc: item.trackingDesc,
        vendorName: item.vendorName,
      }))
      total.value = res.total
    }
  } finally {
    loading.value = false
  }
}

function resetForShipment() {
  activeTab.value = props.initialTab
  showAll.value = props.mode === 'drawer'
}

onMounted(() => {
  resetForShipment()
  load()
})
watch(() => props.shipmentId, () => {
  resetForShipment()
  load()
})
watch(() => props.initialTab, (tab) => {
  activeTab.value = tab
  load()
})
watch([showAll, activeTab], load)
</script>

<template>
  <div :class="isDrawer ? 'py-1' : 'px-4 py-3'">
    <NTabs v-model:value="activeTab" type="segment" size="small" class="mb-3">
      <NTabPane name="internal" tab="内部路由" />
      <NTabPane name="carrier" tab="承运商" />
    </NTabs>
    <NSpin :show="loading">
      <div v-if="!loading && total === 0" class="text-xs text-zinc-500">暂无轨迹记录</div>
      <ul v-else class="space-y-2">
        <li
          v-for="log in logs"
          :key="log.id"
          class="border-l-2 pl-3 text-xs"
          :class="activeTab === 'carrier' ? 'border-sky-500/40' : 'border-violet-500/40'"
        >
          <div class="font-mono text-zinc-400">{{ log.trackingTime }}</div>
          <div v-if="activeTab === 'carrier' && log.vendorName" class="text-zinc-500">
            {{ log.vendorName }}
          </div>
          <div class="mt-0.5 text-zinc-200">{{ log.trackingDesc || '—' }}</div>
        </li>
      </ul>
      <div v-if="!isDrawer && total > PREVIEW" class="mt-3">
        <NButton v-if="!showAll" size="tiny" quaternary type="primary" @click="showAll = true">
          展开全部（共 {{ total }} 条）
        </NButton>
        <NButton v-else size="tiny" quaternary @click="showAll = false">收起</NButton>
      </div>
    </NSpin>
  </div>
</template>
