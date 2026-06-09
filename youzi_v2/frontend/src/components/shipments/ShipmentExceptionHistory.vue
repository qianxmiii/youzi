<script setup lang="ts">
import { TriangleAlert } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NSpin } from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { getShipmentExceptionEvents } from '@/api/shipments'
import type { Shipment, ShipmentExceptionEvent } from '@/types/shipment'

const props = withDefaults(
  defineProps<{
    shipmentId: string
    shipment?: Shipment | null
    labelByCode?: Record<string, string>
    mode?: 'default' | 'drawer'
  }>(),
  { mode: 'default' },
)

function codeLabel(code: string) {
  return props.labelByCode?.[code] || code
}

const loading = ref(false)
const items = ref<ShipmentExceptionEvent[]>([])

const openException = computed(() => {
  const code = props.shipment?.exceptionCode?.trim()
  if (!code) return null
  const openEvent = items.value.find((ev) => ev.exceptionCode === code && !ev.closedTime)
  return {
    code,
    label: codeLabel(code),
    note: openEvent?.note || null,
    openedTime: props.shipment?.exceptionOpenedTime || openEvent?.openedTime || null,
  }
})

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
  <!-- Drawer：设计稿异常卡片 -->
  <div v-if="mode === 'drawer' && openException" class="abnormal-section">
    <h3 class="section-label">
      Abnormal Status <span class="section-label-zh">（异常信息）</span>
    </h3>
    <NSpin :show="loading">
      <div class="abnormal-card">
        <div class="flex gap-3">
          <div class="abnormal-icon shrink-0" aria-hidden="true">
            <TriangleAlert class="h-5 w-5" :stroke-width="ICON_STROKE" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="abnormal-title">
              Issue: {{ openException.label }}
            </div>
            <p v-if="openException.note" class="abnormal-desc">
              {{ openException.note }}
            </p>
            <p v-else class="abnormal-desc">该运单存在未关闭异常，请及时跟进。</p>
          </div>
        </div>
      </div>
    </NSpin>
  </div>

  <!-- Default：历史列表 -->
  <div v-else-if="mode === 'default'" class="exception-history-default">
    <div class="mb-2 text-xs font-medium text-secondary">异常记录</div>
    <NSpin :show="loading">
      <div v-if="!loading && items.length === 0" class="text-xs text-muted">暂无异常事件</div>
      <ul v-else class="space-y-2">
        <li
          v-for="ev in items"
          :key="ev.id"
          class="exception-history-item"
        >
          <div class="flex flex-wrap items-center gap-2 text-fg">
            <span class="font-medium">{{ codeLabel(ev.exceptionCode) }}</span>
            <span class="text-muted">{{ ev.durationLabel }}</span>
            <span v-if="!ev.closedTime" class="exception-open-badge rounded px-1.5 py-0.5">进行中</span>
          </div>
          <div class="mt-0.5 text-muted">
            {{ ev.openedTime }}
            <template v-if="ev.closedTime"> → {{ ev.closedTime }}</template>
          </div>
          <div v-if="ev.note" class="mt-0.5 text-secondary">{{ ev.note }}</div>
        </li>
      </ul>
    </NSpin>
  </div>
</template>

<style scoped>
.abnormal-section {
  border-top: 1px solid var(--color-border);
  padding-top: 1.125rem;
  margin-top: 0;
}

.section-label {
  margin-bottom: 0.75rem;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.section-label-zh {
  text-transform: none;
  letter-spacing: normal;
  font-weight: 600;
}

.abnormal-card {
  border-radius: 0.625rem;
  border: 1px solid rgb(191 219 254);
  background: rgb(240 247 255);
  padding: 1rem 1rem 0.875rem;
}

[data-theme='dark'] .abnormal-card {
  border-color: rgb(30 58 138 / 0.55);
  background: rgb(30 58 138 / 0.2);
}

.abnormal-icon {
  color: rgb(220 38 38);
}

.abnormal-title {
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.35;
  color: var(--color-fg-emphasis);
}

.abnormal-desc {
  margin-top: 0.375rem;
  font-size: 0.8125rem;
  line-height: 1.55;
  color: var(--color-fg-secondary);
}

.exception-open-badge {
  background: var(--tracking-ahead-badge-bg);
  color: var(--tracking-ahead-badge-fg);
}

.exception-history-default {
  margin-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  padding-top: 0.75rem;
}

.text-secondary {
  color: var(--color-fg-secondary);
}

.text-muted {
  color: var(--color-muted);
}

.text-fg {
  color: var(--color-fg);
}

.exception-history-item {
  border-radius: 0.25rem;
  border: 1px solid var(--color-border);
  background: var(--color-btn-ghost-bg);
  padding: 0.375rem 0.5rem;
  font-size: 0.75rem;
}
</style>
