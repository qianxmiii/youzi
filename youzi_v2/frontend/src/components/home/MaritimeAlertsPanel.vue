<script setup lang="ts">
import { NButton, NSpin, NTag, useMessage } from 'naive-ui'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getMaritimeAlertsOverview,
  markAllMaritimeNotificationsRead,
  markPortArrivalNotificationRead,
  markShipmentArrivalNotificationRead,
  type MaritimeAlertPortCall,
  type MaritimeAlertsOverview,
  type MaritimeAlertShipment,
  type PortArrivalNotification,
  type ShipmentArrivalNotification,
} from '@/api/maritimeAlerts'
import { maritimeStatusTagType } from '@/types/vesselSchedule'
import MaritimeAlertStatCards from '@/components/home/MaritimeAlertStatCards.vue'
import { hasDeliveredKeyword, splitDeliveredHighlight } from '@/utils/highlightDelivered'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const markingAllRead = ref(false)
const data = ref<MaritimeAlertsOverview | null>(null)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getMaritimeAlertsOverview()
  } catch (e) {
    data.value = null
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const alertCards = computed(() => {
  const c = data.value?.counts
  if (!c) return []
  return [
    { key: 'arriving_soon', label: '三天内到港', count: c.arrivingSoon, query: { maritimeStatus: 'arriving_soon' } },
    { key: 'departing_soon', label: '三天内离港', count: c.departingSoon, query: { maritimeStatus: 'departing_soon' } },
    { key: 'in_transit', label: '在途', count: c.inTransit, query: { maritimeStatus: 'in_transit' } },
    { key: 'port_arriving', label: '挂靠将到港', count: c.portArrivingSoon, query: {} },
    { key: 'port_departing', label: '挂靠将离港', count: c.portDepartingSoon, query: {} },
    { key: 'arrived', label: '已到港', count: c.arrived, query: { maritimeStatus: 'arrived' } },
  ]
})

const portArrivalNotifications = computed(() => data.value?.portArrivalNotifications ?? [])
const shipmentArrivalNotifications = computed(() => data.value?.shipmentArrivalNotifications ?? [])
const etaArrivingSoonPortCalls = computed(() => data.value?.etaArrivingSoonPortCalls ?? [])
const etaArrivingSoonShipments = computed(() => data.value?.etaArrivingSoonShipments ?? [])

type AlertFeedItem =
  | { kind: 'shipment'; id: string; data: ShipmentArrivalNotification }
  | { kind: 'port'; id: string; data: PortArrivalNotification }
  | { kind: 'eta_port'; id: string; data: MaritimeAlertPortCall }
  | { kind: 'eta_shipment'; id: string; data: MaritimeAlertShipment }

const alertFeedItems = computed<AlertFeedItem[]>(() => {
  const items: AlertFeedItem[] = []
  for (const n of shipmentArrivalNotifications.value) {
    items.push({ kind: 'shipment', id: 'sh-' + n.id, data: n })
  }
  for (const n of portArrivalNotifications.value) {
    items.push({ kind: 'port', id: 'pt-' + n.id, data: n })
  }
  for (const p of etaArrivingSoonPortCalls.value) {
    items.push({ kind: 'eta_port', id: 'ep-' + p.voyageId + '-' + String(p.sequence), data: p })
  }
  for (const s of etaArrivingSoonShipments.value) {
    items.push({ kind: 'eta_shipment', id: 'es-' + s.shipmentNo, data: s })
  }
  return items
})

const hasUnreadNotifications = computed(
  () => portArrivalNotifications.value.length > 0 || shipmentArrivalNotifications.value.length > 0,
)

const urgentShipments = computed(() => data.value?.urgentShipments ?? [])
const urgentPortCalls = computed(() => data.value?.urgentPortCalls ?? [])

async function dismissPortArrival(n: PortArrivalNotification) {
  try {
    await markPortArrivalNotificationRead(n.id)
    if (data.value) {
      data.value = {
        ...data.value,
        portArrivalNotifications: data.value.portArrivalNotifications.filter((x) => x.id !== n.id),
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissShipmentArrival(n: ShipmentArrivalNotification) {
  try {
    await markShipmentArrivalNotificationRead(n.id)
    if (data.value) {
      data.value = {
        ...data.value,
        shipmentArrivalNotifications: data.value.shipmentArrivalNotifications.filter(
          (x) => x.id !== n.id,
        ),
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissAllNotifications() {
  if (!hasUnreadNotifications.value) return
  markingAllRead.value = true
  try {
    const res = await markAllMaritimeNotificationsRead()
    if (data.value) {
      data.value = {
        ...data.value,
        portArrivalNotifications: [],
        shipmentArrivalNotifications: [],
      }
    }
    if (res.total > 0) {
      message.success('已标记 ' + String(res.total) + ' 条通知为已读')
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    markingAllRead.value = false
  }
}

function goVesselSchedules(query?: Record<string, string>) {
  router.push({ path: '/vessel-schedules', query })
}

function goVoyage(voyageId: string) {
  router.push({ path: '/vessel-schedules', query: { voyageId } })
}

function goShipment(shipmentNo: string) {
  const sn = shipmentNo.trim()
  if (!sn) return
  router.push({ path: '/shipments', query: { shipmentNo: sn, fromNotify: '1' } })
}

function goShipmentsList() {
  router.push({ path: '/shipments' })
}

function trackingSourceLabel(source: string): string {
  if (source === 'internal') return '内部轨迹'
  if (source === 'carrier') return '承运商轨迹'
  if (source === 'arrival') return '到港'
  return '轨迹更新'
}

function formatTime(raw: string | null | undefined) {
  return raw ? raw.slice(0, 16) : '—'
}

function onFeedDismiss(item: AlertFeedItem) {
  if (item.kind === 'shipment') dismissShipmentArrival(item.data)
  else if (item.kind === 'port') dismissPortArrival(item.data)
}
</script>

<template>
  <div class="workbench-home">
    <header class="workbench-header">
      <div class="workbench-header__main">
        <h1 class="workbench-header__title">物流工作台</h1>
        <p v-if="data" class="workbench-header__meta">
          扫描 {{ data.totalScanned }} 票含船期字段运单 · 更新于 {{ data.generatedAt?.slice(0, 16) }}
        </p>
        <p v-else-if="loading" class="workbench-header__meta">数据加载中…</p>
      </div>
      <div class="workbench-header__actions">
        <NButton size="small" type="primary" @click="goVesselSchedules()">
          船期监控
        </NButton>
        <NButton size="small" quaternary :loading="loading" aria-label="刷新" @click="load">
          <template #icon>
            <svg viewBox="0 0 16 16" fill="none" class="h-4 w-4" aria-hidden="true">
              <path
                d="M13.5 2.5v3h-3M2.5 13.5v-3h3M13.1 5.1A5.5 5.5 0 0 0 4.2 3.7L2.5 5.5M2.9 10.9a5.5 5.5 0 0 0 8.9 1.4l1.7-1.8"
                stroke="currentColor"
                stroke-width="1.25"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </template>
        </NButton>
      </div>
    </header>

    <MaritimeAlertStatCards
      :cards="alertCards"
      :loading="loading && !data"
      @navigate="(q) => goVesselSchedules(q)"
    />

    <NSpin :show="loading && !data">
      <div v-if="error" class="panel px-4 py-3 text-sm text-red-400">{{ error }}</div>

      <template v-else-if="data">
        <div class="workbench-modules">
        <article class="panel workbench-alerts">
          <div class="workbench-panel-head">
            <h2 class="workbench-panel-title">海运预警 &amp; ETA 提醒</h2>
            <button
              v-if="hasUnreadNotifications"
              type="button"
              class="workbench-link-btn"
              :disabled="markingAllRead"
              @click="dismissAllNotifications"
            >
              全部已读
            </button>
          </div>

          <ul v-if="alertFeedItems.length" class="workbench-feed">
            <li
              v-for="item in alertFeedItems"
              :key="item.id"
              class="workbench-feed__item"
              :class="{
                'workbench-feed__item--delivered':
                  item.kind === 'shipment' && hasDeliveredKeyword(item.data.latestDesc),
              }"
            >
              <template v-if="item.kind === 'shipment'">
                <button type="button" class="workbench-feed__body" @click="goShipment(item.data.shipmentNo)">
                  <div class="workbench-feed__row">
                    <NTag size="small" :bordered="false" type="info">运单轨迹更新</NTag>
                    <span class="workbench-feed__primary">{{ item.data.shipmentNo }}</span>
                    <span v-if="item.data.customer" class="workbench-feed__muted">{{ item.data.customer }}</span>
                  </div>
                  <p class="workbench-feed__desc line-clamp-2">
                    <template
                      v-for="(part, idx) in splitDeliveredHighlight(item.data.latestDesc)"
                      :key="idx"
                    >
                      <span v-if="part.highlight" class="workbench-feed__highlight">{{ part.text }}</span>
                      <span v-else>{{ part.text }}</span>
                    </template>
                  </p>
                  <p class="workbench-feed__meta">
                    {{ trackingSourceLabel(item.data.trackingSource) }}
                    · {{ formatTime(item.data.latestTime) }}
                  </p>
                </button>
                <NButton size="tiny" quaternary @click="onFeedDismiss(item)">知道了</NButton>
              </template>

              <template v-else-if="item.kind === 'port'">
                <button type="button" class="workbench-feed__body" @click="goVoyage(item.data.voyageId)">
                  <div class="workbench-feed__row">
                    <span class="workbench-feed__icon-clock" aria-hidden="true">
                      <svg viewBox="0 0 16 16" fill="none" class="h-4 w-4">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.25" />
                        <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
                      </svg>
                    </span>
                    <span class="workbench-feed__primary">{{ item.data.portName }}</span>
                    <NTag size="small" :bordered="false" type="success">已到港</NTag>
                  </div>
                  <p class="workbench-feed__desc">{{ item.data.vesselVoyage }}</p>
                  <p class="workbench-feed__meta">ATA {{ formatTime(item.data.ata) }}</p>
                </button>
                <NButton size="tiny" quaternary @click="onFeedDismiss(item)">知道了</NButton>
              </template>

              <template v-else-if="item.kind === 'eta_port'">
                <button type="button" class="workbench-feed__body" @click="goVoyage(item.data.voyageId)">
                  <div class="workbench-feed__row">
                    <span class="workbench-feed__icon-clock" aria-hidden="true">
                      <svg viewBox="0 0 16 16" fill="none" class="h-4 w-4">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.25" />
                        <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
                      </svg>
                    </span>
                    <span class="workbench-feed__primary">{{ item.data.portName }}</span>
                    <NTag size="small" :bordered="false" type="warning">三天内到港</NTag>
                  </div>
                  <p class="workbench-feed__desc">{{ item.data.vesselVoyage }} · 挂靠</p>
                  <p class="workbench-feed__meta">ETA {{ formatTime(item.data.eta) }}</p>
                </button>
              </template>

              <template v-else>
                <button type="button" class="workbench-feed__body" @click="goShipment(item.data.shipmentNo)">
                  <div class="workbench-feed__row">
                    <span class="workbench-feed__icon-clock" aria-hidden="true">
                      <svg viewBox="0 0 16 16" fill="none" class="h-4 w-4">
                        <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.25" />
                        <path d="M8 4.5V8l2.5 1.5" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
                      </svg>
                    </span>
                    <span class="workbench-feed__primary">{{ item.data.shipmentNo }}</span>
                    <NTag size="small" :bordered="false" type="warning">{{ item.data.maritimeStatusLabel }}</NTag>
                  </div>
                  <p class="workbench-feed__desc">
                    {{ item.data.vesselVoyage || '未填船名航次' }}
                    <span v-if="item.data.destinationPortCode"> · {{ item.data.destinationPortCode }}</span>
                  </p>
                  <p class="workbench-feed__meta">ETA {{ formatTime(item.data.eta) }}</p>
                </button>
              </template>
            </li>
          </ul>
          <p v-else class="workbench-feed-empty">暂无海运预警或 ETA 提醒</p>
        </article>

        <div class="workbench-columns">
          <article class="panel workbench-column">
            <div class="workbench-panel-head">
              <h3 class="workbench-panel-title">关注运单</h3>
              <button type="button" class="workbench-link-btn" @click="goShipmentsList">查看全部</button>
            </div>
            <ul v-if="urgentShipments.length" class="workbench-list">
              <li
                v-for="s in urgentShipments"
                :key="s.shipmentNo"
                class="workbench-list__item"
                role="button"
                tabindex="0"
                @click="goShipment(s.shipmentNo)"
                @keydown.enter.prevent="goShipment(s.shipmentNo)"
                @keydown.space.prevent="goShipment(s.shipmentNo)"
              >
                <div class="workbench-list__body">
                  <p class="workbench-list__primary">
                    <span class="workbench-list__no">{{ s.shipmentNo }}</span>
                  </p>
                  <p class="workbench-list__sub">
                    {{ s.vesselVoyage || '未填船名航次' }}
                    <span v-if="s.destinationPortCode"> · {{ s.destinationPortCode }}</span>
                  </p>
                  <p class="workbench-list__meta">
                    ETD {{ formatTime(s.etd) }} · ETA {{ formatTime(s.eta) }}
                  </p>
                </div>
                <NTag size="small" :type="maritimeStatusTagType(s.maritimeStatus)" :bordered="false">
                  {{ s.maritimeStatusLabel }}
                </NTag>
              </li>
            </ul>
            <p v-else class="workbench-list-empty">暂无关注运单</p>
          </article>

          <article class="panel workbench-column">
            <div class="workbench-panel-head">
              <h3 class="workbench-panel-title">挂靠预警</h3>
              <button type="button" class="workbench-link-btn" @click="goVesselSchedules()">查看全部</button>
            </div>
            <ul v-if="urgentPortCalls.length" class="workbench-list">
              <li
                v-for="p in urgentPortCalls"
                :key="p.voyageId + '-' + String(p.sequence)"
                class="workbench-list__item"
                role="button"
                tabindex="0"
                @click="goVoyage(p.voyageId)"
                @keydown.enter.prevent="goVoyage(p.voyageId)"
                @keydown.space.prevent="goVoyage(p.voyageId)"
              >
                <div class="workbench-list__body">
                  <p class="workbench-list__primary">{{ p.portName }}</p>
                  <p class="workbench-list__sub">{{ p.vesselVoyage }}</p>
                  <p class="workbench-list__meta">
                    ETD {{ formatTime(p.etd) }} · ETA {{ formatTime(p.eta) }}
                  </p>
                </div>
                <NTag size="small" :type="maritimeStatusTagType(p.status)" :bordered="false">
                  {{ p.statusLabel }}
                </NTag>
              </li>
            </ul>
            <p v-else class="workbench-list-empty">暂无挂靠预警</p>
          </article>
        </div>

        <div
          v-if="data.unconfiguredVesselVoyages.length"
          class="panel workbench-footnote"
        >
          <p class="text-xs font-medium text-[var(--tracking-ahead-desc)]">运单有船名航次但未配置航次主数据</p>
          <ul class="mt-2 flex flex-wrap gap-2">
            <li
              v-for="u in data.unconfiguredVesselVoyages"
              :key="u.vesselVoyage"
              class="rounded-md bg-[var(--color-btn-ghost-bg)] px-2 py-1 text-xs text-[var(--color-fg-secondary)]"
            >
              {{ u.vesselVoyage }}（{{ u.shipmentCount }} 票）
            </li>
          </ul>
        </div>
        </div>
      </template>
    </NSpin>
  </div>
</template>

<style scoped>
.workbench-home {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.workbench-modules {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.workbench-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.workbench-header__title {
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--color-fg-emphasis);
}

.workbench-header__meta {
  margin-top: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.workbench-header__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.workbench-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.workbench-panel-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.workbench-link-btn {
  border: none;
  background: transparent;
  padding: 0.25rem 0.5rem;
  margin: -0.25rem -0.5rem;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: rgb(124 58 237);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.workbench-link-btn:hover:not(:disabled) {
  background: rgb(237 233 254);
  color: rgb(109 40 217);
}

.workbench-link-btn:focus-visible {
  outline: 2px solid rgb(139 92 246 / 0.45);
  outline-offset: 2px;
}

.workbench-link-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

.workbench-alerts {
  padding: 1.25rem 1.25rem 0.75rem;
}

.workbench-feed {
  list-style: none;
  margin: 0;
  padding: 0;
}

.workbench-feed__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 0 -0.5rem;
  padding: 0.875rem 0.5rem;
  border-bottom: 1px solid var(--color-list-divider);
  border-radius: 0.5rem;
  transition: background-color 0.15s ease;
}

.workbench-feed__item:last-child {
  border-bottom: none;
}

.workbench-feed__item:hover {
  background: var(--color-nav-hover);
}

.workbench-feed__item--delivered {
  background: rgb(16 185 129 / 0.06);
}

.workbench-feed__item--delivered:hover {
  background: rgb(16 185 129 / 0.12);
}

.workbench-feed__body {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
  border-radius: 0.25rem;
  transition: opacity 0.15s ease;
}

.workbench-feed__item:hover .workbench-feed__primary {
  color: var(--color-accent-text);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.workbench-feed__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.workbench-feed__primary {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-accent-text);
}

.workbench-feed__muted {
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.workbench-feed__icon-clock {
  display: inline-flex;
  color: var(--color-muted);
}

.workbench-feed__desc {
  margin-top: 0.25rem;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: var(--color-fg-secondary);
}

.workbench-feed__meta {
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  color: var(--color-muted);
}

.workbench-feed__highlight {
  border-radius: 0.125rem;
  background: rgb(70 72 212 / 0.12);
  padding: 0 0.125rem;
  font-weight: 600;
  color: var(--color-accent-text);
}

.workbench-feed-empty,
.workbench-list-empty {
  padding: 2rem 0;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.workbench-columns {
  display: grid;
  gap: 1.5rem;
}

@media (min-width: 1024px) {
  .workbench-columns {
    grid-template-columns: 1fr 1fr;
  }
}

.workbench-column {
  padding: 1.25rem;
  min-height: 12rem;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.workbench-column:hover {
  border-color: var(--color-border);
  box-shadow: 0 2px 10px rgb(24 24 27 / 0.04);
}

.workbench-alerts:hover {
  border-color: var(--color-border);
  box-shadow: 0 2px 10px rgb(24 24 27 / 0.04);
}

.workbench-alerts {
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.workbench-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.workbench-list__item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 0 -0.375rem;
  padding: 0.75rem 0.375rem;
  border-bottom: 1px solid var(--color-list-divider);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.workbench-list__item:last-child {
  border-bottom: none;
}

.workbench-list__item:hover {
  background: var(--color-nav-hover);
}

.workbench-list__body {
  flex: 1;
  min-width: 0;
  padding: 0;
  text-align: left;
  pointer-events: none;
}

.workbench-list__item:focus-visible {
  outline: 2px solid rgb(139 92 246 / 0.45);
  outline-offset: 2px;
}

.workbench-feed__body:focus-visible {
  outline: 2px solid rgb(139 92 246 / 0.45);
  outline-offset: 2px;
}

.workbench-list__item:hover .workbench-list__no {
  text-decoration: underline;
  text-underline-offset: 2px;
  color: var(--color-accent-text);
}

.workbench-list__primary {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-accent-text);
}

.workbench-list__no {
  color: var(--color-accent-text);
}

.workbench-list__sub {
  margin-top: 0.125rem;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.workbench-list__meta {
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  color: var(--color-fg-secondary);
}

.workbench-footnote {
  padding: 1rem 1.25rem;
}

[data-theme='dark'] .workbench-link-btn {
  color: rgb(167 139 250);
}

[data-theme='dark'] .workbench-link-btn:hover:not(:disabled) {
  background: rgb(91 33 182 / 0.35);
  color: rgb(196 181 253);
}

[data-theme='dark'] .workbench-column:hover,
[data-theme='dark'] .workbench-alerts:hover {
  box-shadow: 0 2px 12px rgb(0 0 0 / 0.2);
}

/* 知道了 等操作按钮 hover */
.workbench-feed :deep(.n-button.n-button--quaternary-type:hover) {
  background-color: var(--color-btn-ghost-hover) !important;
}
</style>
