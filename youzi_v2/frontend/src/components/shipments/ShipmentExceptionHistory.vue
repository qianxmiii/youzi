<script setup lang="ts">
import { NSpin } from 'naive-ui'
import { onMounted, ref, watch } from 'vue'
import { getShipmentExceptionEvents } from '@/api/shipments'
import type { ShipmentExceptionEvent } from '@/types/shipment'

const props = defineProps<{
  shipmentId: string
  labelByCode?: Record<string, string>
}>()

function codeLabel(code: string) {
  return props.labelByCode?.[code] || code
}

const loading = ref(false)
const items = ref<ShipmentExceptionEvent[]>([])

async function load() {
  loading.value = true
  try {
    const res = await getShipmentExceptionEvents(props.shipmentId, { limit: 30 })
    items.value = res.items
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.shipmentId, load)
</script>

<template>
  <div class="mt-3 border-t border-[var(--color-border)] pt-3">
    <div class="mb-2 text-xs font-medium text-zinc-400">异常记录</div>
    <NSpin :show="loading">
      <div v-if="!loading && items.length === 0" class="text-xs text-zinc-500">暂无异常事件</div>
      <ul v-else class="space-y-2">
        <li
          v-for="ev in items"
          :key="ev.id"
          class="rounded border border-[var(--color-border)] bg-zinc-900/40 px-2 py-1.5 text-xs"
        >
          <div class="flex flex-wrap items-center gap-2 text-zinc-200">
            <span class="font-medium">{{ codeLabel(ev.exceptionCode) }}</span>
            <span class="text-zinc-500">{{ ev.durationLabel }}</span>
            <span
              v-if="!ev.closedTime"
              class="rounded bg-amber-500/20 px-1.5 py-0.5 text-amber-200"
            >进行中</span>
          </div>
          <div class="mt-0.5 text-zinc-500">
            {{ ev.openedTime }}
            <template v-if="ev.closedTime"> → {{ ev.closedTime }}</template>
          </div>
          <div v-if="ev.note" class="mt-0.5 text-zinc-400">{{ ev.note }}</div>
        </li>
      </ul>
    </NSpin>
  </div>
</template>
