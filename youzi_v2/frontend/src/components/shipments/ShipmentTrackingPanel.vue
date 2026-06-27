<script setup lang="ts">
import { Check, Copy } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NButton, NSpin, useMessage } from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import {
  getShipmentCarrierTrackingLogs,
  getShipmentTrackingLogs,
  getShipment,
  syncCarrierTracking,
  syncTracking,
} from '@/api/shipments'
import type { CarrierTrackingLog } from '@/types/tracking'
import type { Shipment } from '@/types/shipment'
import { notifyTrackingSyncResult } from '@/utils/trackingSyncNotify'

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

const emit = defineEmits<{
  'shipment-updated': [shipment: Shipment]
}>()

type LogRow = { id: string; trackingTime: string; trackingDesc: string }

const message = useMessage()

const activeTab = ref<'internal' | 'carrier'>(props.initialTab)
const loading = ref(false)
const syncingInternal = ref(false)
const syncingCarrier = ref(false)
const logs = ref<LogRow[]>([])
const total = ref(0)
const copiedLogId = ref<string | null>(null)

const isDrawer = computed(() => props.mode === 'drawer')

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

async function copyLog(log: LogRow) {
  try {
    await navigator.clipboard.writeText(`${log.trackingTime}\n${log.trackingDesc}`)
    copiedLogId.value = log.id
    message.success('已复制')
    window.setTimeout(() => {
      if (copiedLogId.value === log.id) copiedLogId.value = null
    }, 1500)
  } catch {
    message.error('复制失败')
  }
}

async function refreshShipmentAfterSync() {
  try {
    const row = await getShipment(props.shipmentId)
    emit('shipment-updated', row)
  } catch {
    /* 列表/抽屉已有行数据兜底 */
  }
}

async function handleSyncInternal() {
  const sn = props.shipment?.shipmentNo?.trim()
  if (!sn) {
    message.warning('缺少运单号')
    return
  }
  syncingInternal.value = true
  try {
    const res = await syncTracking([sn])
    notifyTrackingSyncResult(message, res, '内部轨迹')
    activeTab.value = 'internal'
    await load()
    await refreshShipmentAfterSync()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新内部轨迹失败')
  } finally {
    syncingInternal.value = false
  }
}

async function handleSyncCarrier() {
  const sn = props.shipment?.shipmentNo?.trim()
  if (!sn) {
    message.warning('缺少运单号')
    return
  }
  syncingCarrier.value = true
  try {
    const res = await syncCarrierTracking([sn])
    notifyTrackingSyncResult(message, res, '承运商轨迹')
    activeTab.value = 'carrier'
    await load()
    await refreshShipmentAfterSync()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新承运商轨迹失败')
  } finally {
    syncingCarrier.value = false
  }
}

</script>

<template>
  <!-- Drawer：设计稿时间轴 -->
  <div v-if="isDrawer" class="tracking-timeline-section">
    <div class="tracking-tab-switch tracking-tab-switch--full mb-3 rounded-lg p-0.5">
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

    <div class="tracking-sync-actions mb-4 flex gap-2">
      <NButton
        size="small"
        class="flex-1"
        :loading="syncingInternal"
        :disabled="syncingCarrier"
        @click="handleSyncInternal"
      >
        更新内部轨迹
      </NButton>
      <NButton
        size="small"
        class="flex-1"
        :loading="syncingCarrier"
        :disabled="syncingInternal"
        @click="handleSyncCarrier"
      >
        更新承运商轨迹
      </NButton>
    </div>

    <NSpin :show="loading">
      <div v-if="!loading && total === 0" class="text-sm text-[var(--color-muted)]">
        暂无轨迹记录
      </div>
      <ol v-else class="tracking-timeline-list">
        <li
          v-for="(log, index) in logs"
          :key="log.id"
          class="tracking-timeline-item"
          :class="{
            'tracking-timeline-item--latest': index === 0,
            'tracking-timeline-item--past': index > 0,
          }"
        >
          <div
            class="tracking-timeline-marker"
            :class="index === 0 ? 'tracking-timeline-marker--solid' : 'tracking-timeline-marker--dot'"
            aria-hidden="true"
          />
          <div
            class="tracking-timeline-body tracking-timeline-body--copyable"
            role="button"
            tabindex="0"
            title="点击复制时间与描述"
            @click="copyLog(log)"
            @keydown.enter.prevent="copyLog(log)"
          >
            <button
              type="button"
              class="tracking-copy-btn"
              :class="{ 'tracking-copy-btn--copied': copiedLogId === log.id }"
              :aria-label="copiedLogId === log.id ? '已复制' : '复制轨迹'"
              @click.stop="copyLog(log)"
            >
              <Check
                v-if="copiedLogId === log.id"
                class="h-3.5 w-3.5"
                :stroke-width="ICON_STROKE"
                aria-hidden="true"
              />
              <Copy
                v-else
                class="h-3.5 w-3.5"
                :stroke-width="ICON_STROKE"
                aria-hidden="true"
              />
            </button>
            <div class="timeline-time">{{ log.trackingTime }}</div>
            <div
              class="timeline-content"
              :class="{ 'timeline-content--emphasis': index === 0 }"
            >
              {{ log.trackingDesc }}
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
          class="tracking-log-item tracking-log-item--copyable border-l-2 pl-3 text-xs"
          :class="activeTab === 'carrier' ? 'tracking-log-item--carrier' : 'tracking-log-item--internal'"
          role="button"
          tabindex="0"
          title="点击复制时间与描述"
          @click="copyLog(log)"
          @keydown.enter.prevent="copyLog(log)"
        >
          <button
            type="button"
            class="tracking-copy-btn tracking-copy-btn--compact"
            :class="{ 'tracking-copy-btn--copied': copiedLogId === log.id }"
            :aria-label="copiedLogId === log.id ? '已复制' : '复制轨迹'"
            @click.stop="copyLog(log)"
          >
            <Check
              v-if="copiedLogId === log.id"
              class="h-3 w-3"
              :stroke-width="ICON_STROKE"
              aria-hidden="true"
            />
            <Copy
              v-else
              class="h-3 w-3"
              :stroke-width="ICON_STROKE"
              aria-hidden="true"
            />
          </button>
            <div class="timeline-time">{{ log.trackingTime }}</div>
          <div class="timeline-content mt-0.5">{{ log.trackingDesc }}</div>
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

.tracking-timeline-body--copyable {
  position: relative;
  margin: -0.375rem -0.5rem;
  padding: 0.375rem 2rem 0.375rem 0.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.15s;
}

.tracking-timeline-body--copyable:hover {
  background: var(--color-btn-ghost-bg);
}

.tracking-timeline-body--copyable:focus-visible {
  outline: 2px solid rgb(59 130 246 / 0.45);
  outline-offset: 1px;
}

.tracking-copy-btn {
  position: absolute;
  top: 0.375rem;
  right: 0.375rem;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 1.625rem;
  width: 1.625rem;
  border-radius: 0.375rem;
  color: var(--color-muted);
  opacity: 0;
  transition: opacity 0.15s, color 0.15s, background-color 0.15s;
}

.tracking-timeline-body--copyable:hover .tracking-copy-btn,
.tracking-timeline-body--copyable:focus-within .tracking-copy-btn,
.tracking-copy-btn--copied {
  opacity: 1;
}

.tracking-copy-btn:hover {
  background: var(--color-panel);
  color: rgb(37 99 235);
}

.tracking-copy-btn--copied {
  color: rgb(22 163 74);
}

[data-theme='dark'] .tracking-copy-btn:hover {
  color: rgb(96 165 250);
}

[data-theme='dark'] .tracking-copy-btn--copied {
  color: rgb(74 222 128);
}

.timeline-content {
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-fg);
  margin-top: 0.25rem;
}

.timeline-content--emphasis {
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.timeline-time {
  font-size: 13px;
  color: #8c8c8c;
  line-height: 1.35;
}

.tracking-log-item--internal {
  border-color: rgb(139 92 246 / 0.45);
}

.tracking-log-item--copyable {
  position: relative;
  margin-left: -0.25rem;
  padding: 0.375rem 1.75rem 0.375rem 0.75rem;
  border-radius: 0.375rem;
  cursor: pointer;
  transition: background-color 0.15s;
}

.tracking-log-item--copyable:hover {
  background: var(--color-btn-ghost-bg);
}

.tracking-log-item--copyable:focus-visible {
  outline: 2px solid rgb(59 130 246 / 0.45);
  outline-offset: 1px;
}

.tracking-copy-btn--compact {
  top: 0.25rem;
  right: 0.125rem;
  height: 1.375rem;
  width: 1.375rem;
}

.tracking-log-item--copyable:hover .tracking-copy-btn,
.tracking-log-item--copyable:focus-within .tracking-copy-btn,
.tracking-log-item--copyable .tracking-copy-btn--copied {
  opacity: 1;
}

.tracking-log-item--carrier {
  border-color: rgb(14 165 233 / 0.45);
}
</style>
