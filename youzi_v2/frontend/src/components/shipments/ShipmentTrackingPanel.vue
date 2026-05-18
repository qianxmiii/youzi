<script setup lang="ts">
import { NButton, NSpin } from 'naive-ui'
import { onMounted, ref, watch } from 'vue'
import { getShipmentTrackingLogs } from '@/api/shipments'

const props = defineProps<{
  shipmentId: string
}>()

const loading = ref(false)
const logs = ref<
  { id: string; trackingTime: string; trackingDesc: string }[]
>([])
const total = ref(0)
const showAll = ref(false)

const PREVIEW = 3

async function load() {
  loading.value = true
  try {
    const limit = showAll.value ? 200 : PREVIEW
    const res = await getShipmentTrackingLogs(props.shipmentId, { limit, offset: 0 })
    logs.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.shipmentId, load)
watch(showAll, load)
</script>

<template>
  <div class="px-4 py-3">
    <NSpin :show="loading">
      <div v-if="!loading && total === 0" class="text-xs text-zinc-500">暂无轨迹记录</div>
      <ul v-else class="space-y-2">
        <li
          v-for="log in logs"
          :key="log.id"
          class="border-l-2 border-violet-500/40 pl-3 text-xs"
        >
          <div class="font-mono text-zinc-400">{{ log.trackingTime }}</div>
          <div class="mt-0.5 text-zinc-200">{{ log.trackingDesc || '—' }}</div>
        </li>
      </ul>
      <div v-if="total > PREVIEW" class="mt-3">
        <NButton v-if="!showAll" size="tiny" quaternary type="primary" @click="showAll = true">
          展开全部（共 {{ total }} 条）
        </NButton>
        <NButton v-else size="tiny" quaternary @click="showAll = false">收起</NButton>
      </div>
    </NSpin>
  </div>
</template>
