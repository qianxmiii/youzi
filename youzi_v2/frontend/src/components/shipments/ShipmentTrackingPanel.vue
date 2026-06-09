<script setup lang="ts">
import { Clock } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NSpin } from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { getShipmentCarrierTrackingLogs, getShipmentTrackingLogs } from '@/api/shipments'
import type { CarrierTrackingLog } from '@/types/tracking'
import type { Shipment } from '@/types/shipment'
import { formatAbsoluteDateTime } from '@/utils/formatDateTime'

const props = withDefaults(
  defineProps<{
    shipmentId: string
    shipment?: Shipment | null
    mode?: 'compact' | 'drawer'
    initialTab?: 'internal' | 'carrier'
  }>(),
  {
    mode: 'compact',
    initialTab: 'internal',
  },
)

type LogRow = { id: string; trackingTime: string; trackingDesc: string }

const activeTab = ref<'internal' | 'carrier'>(props.initialTab)
const loading = ref(false)
const logs = ref<LogRow[]>([])
const total = ref(0)

const isDrawer = computed(() => props.mode === 'drawer')

const expectedItem = computed(() => {
  const s = props.shipment
  if (!s || s.statusCode === 'DELIVERED') return null
  const eta = s.eta?.trim()
  if (!eta) return null
  const d = new Date(eta.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return null
  const dateStr = d.getMonth() + 1 + '/' + d.getDate()
  const label = isDrawer.value
    ? 'Expected to be delivered on ' + dateStr
    : '预计送达 ' + dateStr
  return {
    id: 'expected',
    desc: label,
    time: formatAbsoluteDateTime(eta) || eta,
  }
})

async function load() {
  loading.value = true
  try {
    const limit = isDrawer.value ? 200 : 3
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
      }))
      total.value = res.total
    }
  } finally {
    loading.value = false
  }
}

function resetForShipment() {
  activeTab.value = props.initialTab
}

function selectTab(tab: 'internal' | 'carrier') {
  if (activeTab.value === tab) return
  activeTab.value = tab
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
watch(activeTab, load)
</script>

<template>
  <!-- Drawer：设计稿时间轴 -->
  <div v-if="isDrawer" class="tracking-timeline-section">
    <div class="tracking-tab-switch tracking-tab-switch--full mb-4 rounded-lg p-0.5">
      <button
        type="button"
        class="tracking-tab-btn"
        :class="{ 'tracking-tab-btn--active': activeTab === 'internal' }"
        @click="selectTab('internal')"
      >
        内部路由
      </button>
      <button
        type="button"
        class="tracking-tab-btn"
        :class="{ 'tracking-tab-btn--active': activeTab === 'carrier' }"
        @click="selectTab('carrier')"
      >
        承运商路由
      </button>
    </div>

    <NSpin :show="loading">
      <div v-if="!loading && total === 0 && !expectedItem" class="text-sm text-[var(--color-muted)]">
        暂无轨迹记录
      </div>
      <ol v-else class="tracking-timeline-list">
        <li v-if="expectedItem" class="tracking-timeline-item tracking-timeline-item--expected">
          <div class="tracking-timeline-marker tracking-timeline-marker--clock" aria-hidden="true">
            <Clock class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
          </div>
          <div class="tracking-timeline-body">
            <div class="tracking-timeline-time">{{ expectedItem.time }}</div>
            <div class="tracking-timeline-desc tracking-timeline-desc--emphasis">{{ expectedItem.desc }}</div>
          </div>
        </li>

        <li
          v-for="(log, index) in logs"
          :key="log.id"
          class="tracking-timeline-item"
          :class="{
            'tracking-timeline-item--latest': index === 0 && !expectedItem,
            'tracking-timeline-item--past': index > 0 || !!expectedItem,
          }"
        >
          <div
            class="tracking-timeline-marker"
            :class="index === 0 && !expectedItem ? 'tracking-timeline-marker--solid' : 'tracking-timeline-marker--dot'"
            aria-hidden="true"
          />
          <div class="tracking-timeline-body">
            <div class="tracking-timeline-time">{{ log.trackingTime }}</div>
            <div
              class="tracking-timeline-desc"
              :class="{ 'tracking-timeline-desc--emphasis': index === 0 && !expectedItem }"
            >
              {{ log.trackingDesc || '—' }}
            </div>
          </div>
        </li>
      </ol>
    </NSpin>
  </div>

  <!-- Compact：列表页内嵌（保留原样式） -->
  <div v-else class="px-4 py-3">
    <div class="mb-3 inline-flex rounded-lg bg-[var(--color-btn-ghost-bg)] p-0.5">
      <button
        type="button"
        class="tracking-tab-btn"
        :class="{ 'tracking-tab-btn--active': activeTab === 'internal' }"
        @click="selectTab('internal')"
      >
        内部路由
      </button>
      <button
        type="button"
        class="tracking-tab-btn"
        :class="{ 'tracking-tab-btn--active': activeTab === 'carrier' }"
        @click="selectTab('carrier')"
      >
        承运商
      </button>
    </div>
    <NSpin :show="loading">
      <div v-if="!loading && total === 0" class="text-xs text-[var(--color-muted)]">暂无轨迹记录</div>
      <ul v-else class="space-y-2">
        <li
          v-for="log in logs"
          :key="log.id"
          class="tracking-log-item border-l-2 pl-3 text-xs"
          :class="activeTab === 'carrier' ? 'tracking-log-item--carrier' : 'tracking-log-item--internal'"
        >
          <div class="tracking-log-time font-mono">{{ log.trackingTime }}</div>
          <div class="tracking-log-desc mt-0.5">{{ log.trackingDesc || '—' }}</div>
        </li>
      </ul>
    </NSpin>
  </div>
</template>

<style scoped>
.tracking-tab-switch {
  background: rgb(241 245 249);
}

.tracking-tab-switch--full {
  display: flex;
  width: 100%;
}

[data-theme='dark'] .tracking-tab-switch {
  background: rgb(39 39 42);
}

.tracking-tab-btn {
  border-radius: 0.375rem;
  padding: 0.5rem 0.875rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-muted);
  transition: background-color 0.15s, color 0.15s, box-shadow 0.15s;
}

.tracking-tab-switch--full .tracking-tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.tracking-tab-btn--active {
  background: var(--color-panel);
  color: rgb(79 70 229);
  box-shadow: 0 1px 3px rgb(24 24 27 / 0.08);
}

[data-theme='dark'] .tracking-tab-btn--active {
  color: rgb(196 181 253);
}

.tracking-timeline-list {
  position: relative;
  list-style: none;
  margin: 0;
  padding: 0;
}

.tracking-timeline-item {
  position: relative;
  display: flex;
  gap: 0.875rem;
  padding-bottom: 1.25rem;
}

.tracking-timeline-item:last-child {
  padding-bottom: 0;
}

.tracking-timeline-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 24px;
  bottom: 0;
  width: 1px;
  background: var(--color-border);
}

.tracking-timeline-marker {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.tracking-timeline-marker--clock {
  display: flex;
  height: 24px;
  width: 24px;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: rgb(139 92 246);
  color: #fff;
}

.tracking-timeline-marker--solid,
.tracking-timeline-marker--dot {
  display: flex;
  height: 24px;
  width: 24px;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: rgb(219 234 254);
}

.tracking-timeline-marker--solid::after,
.tracking-timeline-marker--dot::after {
  content: '';
  border-radius: 9999px;
  background: rgb(59 130 246);
}

.tracking-timeline-marker--solid::after {
  height: 10px;
  width: 10px;
}

.tracking-timeline-marker--dot::after {
  height: 8px;
  width: 8px;
  background: rgb(96 165 250);
}

[data-theme='dark'] .tracking-timeline-marker--solid,
[data-theme='dark'] .tracking-timeline-marker--dot {
  background: rgb(30 58 138 / 0.5);
}

[data-theme='dark'] .tracking-timeline-marker--solid::after,
[data-theme='dark'] .tracking-timeline-marker--dot::after {
  background: rgb(96 165 250);
}

.tracking-timeline-body {
  min-width: 0;
  flex: 1;
  padding-top: 1px;
}

.tracking-timeline-desc {
  font-size: 0.875rem;
  line-height: 1.4;
  color: var(--color-fg);
  margin-top: 0.25rem;
}

.tracking-timeline-desc--emphasis {
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.tracking-timeline-time {
  font-size: 0.75rem;
  font-family: ui-monospace, monospace;
  color: var(--color-muted);
  line-height: 1.35;
}

.tracking-log-item--internal {
  border-color: rgb(139 92 246 / 0.45);
}

.tracking-log-item--carrier {
  border-color: rgb(14 165 233 / 0.45);
}

.tracking-log-time {
  color: var(--tracking-log-time);
}

.tracking-log-desc {
  color: var(--tracking-log-desc);
}
</style>
