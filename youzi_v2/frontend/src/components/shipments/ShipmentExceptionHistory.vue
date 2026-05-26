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
    <div class="mb-2 text-xs font-medium text-[var(--color-fg-secondary)]">异常记录</div>
    <NSpin :show="loading">
      <div v-if="!loading && items.length === 0" class="text-xs text-[var(--color-muted)]">暂无异常事件</div>
      <ul v-else class="space-y-2">
        <li
          v-for="ev in items"
          :key="ev.id"
          class="rounded border border-[var(--color-border)] bg-[var(--color-btn-ghost-bg)] px-2 py-1.5 text-xs"
        >
          <div class="flex flex-wrap items-center gap-2 text-[var(--color-fg)]">
            <span class="font-medium">{{ codeLabel(ev.exceptionCode) }}</span>
            <span class="text-[var(--color-muted)]">{{ ev.durationLabel }}</span>
            <span v-if="!ev.closedTime" class="exception-open-badge rounded px-1.5 py-0.5">进行中</span>
          </div>
          <div class="mt-0.5 text-[var(--color-muted)]">
            {{ ev.openedTime }}
            <template v-if="ev.closedTime"> → {{ ev.closedTime }}</template>
          </div>
          <div v-if="ev.note" class="mt-0.5 text-[var(--color-fg-secondary)]">{{ ev.note }}</div>
        </li>
      </ul>
    </NSpin>
  </div>
</template>

<style scoped>
.exception-open-badge {
  background: var(--tracking-ahead-badge-bg);
  color: var(--tracking-ahead-badge-fg);
}
</style>
