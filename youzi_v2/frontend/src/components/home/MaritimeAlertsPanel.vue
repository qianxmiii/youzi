<script setup lang="ts">
import { Clock, ClipboardCheck, Layers, Package, RefreshCw, Ship, TriangleAlert } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NButton, NSpin, NTag, useMessage } from 'naive-ui'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getMaritimeAlertsOverview,
  markPortArrivalNotificationRead,
  markShipmentArrivalNotificationRead,
  type MaritimeAlertPortCall,
  type MaritimeAlertsOverview,
  type MaritimeAlertShipment,
  type PortArrivalNotification,
  type ShipmentArrivalNotification,
} from '@/api/maritimeAlerts'
import {
  getExceptionFollowupTodoNotifications,
  markExceptionFollowupNotificationRead,
  resolveExceptionFollowupNotification,
  type ShipmentExceptionFollowupNotification,
} from '@/api/exceptionFollowup'
import { getShipmentSlaSummary, type ShipmentSlaSummary } from '@/api/shipmentSla'
import {
  getShipmentGroupTodoNotifications,
  markAllShipmentGroupNotificationsRead,
  markShipmentGroupNotificationRead,
  resolveShipmentGroupNotification,
} from '@/api/shipmentGroups'
import { markAllShipmentTrackingNotificationsRead } from '@/api/shipmentSubscriptions'
import type { ShipmentGroupNotification } from '@/types/shipmentGroup'
import { formatGroupNoDisplay } from '@/utils/shipmentGroup'
import { maritimeStatusTagType } from '@/types/vesselSchedule'
import MaritimeAlertStatCards from '@/components/home/MaritimeAlertStatCards.vue'
import ShipmentGroupAlertCard from '@/components/shipments/ShipmentGroupAlertCard.vue'
import { hasDeliveredKeyword, splitDeliveredHighlight } from '@/utils/highlightDelivered'
import { usePendingTrackingTimeReviewCount } from '@/composables/usePendingTrackingTimeReviewCount'

const { pendingTrackingTimeReviewCount, refreshPendingTrackingTimeReviewCount } =
  usePendingTrackingTimeReviewCount()

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const markingAllRead = ref(false)
const markingGroupRead = ref(false)
const markingShipmentRead = ref(false)
const data = ref<MaritimeAlertsOverview | null>(null)
const groupNotifications = ref<ShipmentGroupNotification[]>([])
const exceptionFollowupNotifications = ref<ShipmentExceptionFollowupNotification[]>([])
const slaSummary = ref<ShipmentSlaSummary | null>(null)
const todoPendingCount = ref(0)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [overview, groupRes, excRes, slaRes] = await Promise.all([
      getMaritimeAlertsOverview(),
      getShipmentGroupTodoNotifications(20),
      getExceptionFollowupTodoNotifications(20),
      getShipmentSlaSummary(),
    ])
    data.value = overview
    groupNotifications.value = groupRes.items
    exceptionFollowupNotifications.value = excRes.items
    slaSummary.value = slaRes
    todoPendingCount.value = groupRes.pendingCount + excRes.pendingCount
  } catch (e) {
    data.value = null
    groupNotifications.value = []
    exceptionFollowupNotifications.value = []
    slaSummary.value = null
    todoPendingCount.value = 0
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
  void refreshPendingTrackingTimeReviewCount()
})

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
  | { kind: 'port'; id: string; data: PortArrivalNotification }
  | { kind: 'eta_port'; id: string; data: MaritimeAlertPortCall }
  | { kind: 'eta_shipment'; id: string; data: MaritimeAlertShipment }

const alertFeedItems = computed<AlertFeedItem[]>(() => {
  const items: AlertFeedItem[] = []
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

const hasUnreadPortNotifications = computed(() => portArrivalNotifications.value.length > 0)

const hasShipmentReminders = computed(() => shipmentArrivalNotifications.value.length > 0)

const hasBatchReminders = computed(
  () => hasTodoReminders.value || hasShipmentReminders.value,
)

const batchReminderCount = computed(
  () => todoItems.value.length + shipmentArrivalNotifications.value.length,
)

type WorkbenchTodoItem =
  | { kind: 'group'; id: string; triggeredAt: string; group: ShipmentGroupNotification }
  | {
      kind: 'exception'
      id: string
      triggeredAt: string
      exception: ShipmentExceptionFollowupNotification
    }

const todoItems = computed<WorkbenchTodoItem[]>(() => {
  const merged: WorkbenchTodoItem[] = [
    ...groupNotifications.value.map((g) => ({
      kind: 'group' as const,
      id: `group:${g.id}`,
      triggeredAt: g.triggeredAt,
      group: g,
    })),
    ...exceptionFollowupNotifications.value.map((e) => ({
      kind: 'exception' as const,
      id: `exception:${e.id}`,
      triggeredAt: e.triggeredAt,
      exception: e,
    })),
  ]
  merged.sort((a, b) => b.triggeredAt.localeCompare(a.triggeredAt))
  return merged
})

const hasGroupNotifications = computed(() => groupNotifications.value.length > 0)

const hasTodoReminders = computed(() => todoItems.value.length > 0)

const totalAlertFeedCount = computed(() => alertFeedItems.value.length)

const headerSummary = computed(() => {
  const c = data.value?.counts
  if (!c) return null
  const attention =
    (c.arrivingSoon ?? 0) +
    (c.portArrivingSoon ?? 0) +
    urgentShipments.value.length +
    urgentPortCalls.value.length
  return {
    attention,
    batch: todoPendingCount.value,
    maritime: totalAlertFeedCount.value,
  }
})

const quickLinks = computed(() => [
  { key: 'shipments', label: '运单管理', path: '/shipments', icon: Package },
  { key: 'vessel', label: '船期监控', path: '/vessel-schedules', icon: Ship },
  {
    key: 'approval',
    label: '轨迹审批',
    path: '/approvals/tracking-time',
    icon: ClipboardCheck,
    badge: pendingTrackingTimeReviewCount.value,
  },
  { key: 'groups', label: '运单分组', path: '/shipment-groups', icon: Layers },
  {
    key: 'exceptions',
    label: '异常跟踪',
    path: '/shipment-exceptions',
    icon: TriangleAlert,
    badge: slaSummary.value?.pendingOpen ?? 0,
  },
])

function goQuickLink(path: string) {
  router.push(path)
}

function groupDisplayLabel(n: ShipmentGroupNotification): string {
  const name = n.groupName?.trim()
  if (name) return name
  return formatGroupNoDisplay(n.groupNo) || '分组'
}

async function dismissGroupNotification(n: ShipmentGroupNotification) {
  try {
    await markShipmentGroupNotificationRead(n.id)
    groupNotifications.value = groupNotifications.value.filter((x) => x.id !== n.id)
    todoPendingCount.value = Math.max(0, todoPendingCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function resolveGroupNotification(n: ShipmentGroupNotification) {
  try {
    await resolveShipmentGroupNotification(n.id)
    groupNotifications.value = groupNotifications.value.filter((x) => x.id !== n.id)
    todoPendingCount.value = Math.max(0, todoPendingCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissExceptionFollowup(n: ShipmentExceptionFollowupNotification) {
  try {
    await markExceptionFollowupNotificationRead(n.id)
    exceptionFollowupNotifications.value = exceptionFollowupNotifications.value.filter(
      (x) => x.id !== n.id,
    )
    todoPendingCount.value = Math.max(0, todoPendingCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function resolveExceptionFollowup(n: ShipmentExceptionFollowupNotification) {
  try {
    await resolveExceptionFollowupNotification(n.id)
    exceptionFollowupNotifications.value = exceptionFollowupNotifications.value.filter(
      (x) => x.id !== n.id,
    )
    todoPendingCount.value = Math.max(0, todoPendingCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissAllGroupNotifications() {
  if (!hasGroupNotifications.value) return
  markingGroupRead.value = true
  try {
    const cleared = groupNotifications.value.length
    const count = await markAllShipmentGroupNotificationsRead()
    groupNotifications.value = []
    todoPendingCount.value = Math.max(0, todoPendingCount.value - cleared)
    if (count > 0) {
      message.success('已标记 ' + String(count) + ' 条分组待办为已读')
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    markingGroupRead.value = false
  }
}

function goShipmentGroup(groupId: string) {
  router.push({ path: '/shipment-groups', query: { groupId } })
}

const urgentShipments = computed(() => data.value?.urgentShipments ?? [])
const urgentPortCalls = computed(() => data.value?.urgentPortCalls ?? [])

async function dismissAllShipmentNotifications() {
  if (!hasShipmentReminders.value) return
  markingShipmentRead.value = true
  try {
    const res = await markAllShipmentTrackingNotificationsRead()
    if (data.value) {
      data.value = {
        ...data.value,
        shipmentArrivalNotifications: [],
      }
    }
    if (res.count > 0) {
      message.success('已标记 ' + String(res.count) + ' 条消息提醒为已读')
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    markingShipmentRead.value = false
  }
}

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

async function dismissAllPortNotifications() {
  if (!hasUnreadPortNotifications.value) return
  markingAllRead.value = true
  try {
    const pending = [...portArrivalNotifications.value]
    for (const n of pending) {
      await markPortArrivalNotificationRead(n.id)
    }
    if (data.value) {
      data.value = {
        ...data.value,
        portArrivalNotifications: [],
      }
    }
    if (pending.length > 0) {
      message.success('已标记 ' + String(pending.length) + ' 条到港通知为已读')
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
  if (item.kind === 'port') dismissPortArrival(item.data)
}
</script>

<template>
  <div class="workbench-home">
    <header class="workbench-hero panel">
      <div class="workbench-hero__copy">
        <p class="workbench-hero__eyebrow">Operations</p>
        <h1 class="workbench-hero__title page-h2-hero">物流工作台</h1>
        <p v-if="data" class="workbench-hero__meta page-subtitle">
          已扫描 {{ data.totalScanned }} 票含船期字段运单 · 更新于 {{ data.generatedAt?.slice(0, 16) }}
        </p>
        <p v-else-if="loading" class="workbench-hero__meta page-subtitle">数据加载中…</p>
        <div v-if="headerSummary && !loading" class="workbench-hero__stats" role="list">
          <span class="workbench-hero__stat" role="listitem">
            <span class="workbench-hero__stat-value">{{ headerSummary.attention }}</span>
            <span class="workbench-hero__stat-label">需关注</span>
          </span>
          <span class="workbench-hero__stat" role="listitem">
            <span class="workbench-hero__stat-value">{{ headerSummary.maritime }}</span>
            <span class="workbench-hero__stat-label">海运提醒</span>
          </span>
          <span v-if="headerSummary.batch > 0" class="workbench-hero__stat" role="listitem">
            <span class="workbench-hero__stat-value">{{ headerSummary.batch }}</span>
            <span class="workbench-hero__stat-label">批次待办</span>
          </span>
        </div>
      </div>
      <div class="workbench-hero__actions">
        <NButton size="small" type="primary" @click="goVesselSchedules()">船期监控</NButton>
        <NButton size="small" quaternary @click="goShipmentsList">运单列表</NButton>
        <NButton size="small" quaternary :loading="loading" aria-label="刷新工作台" @click="load">
          <template #icon>
            <RefreshCw class="h-4 w-4" :stroke-width="ICON_STROKE" aria-hidden="true" />
          </template>
        </NButton>
      </div>
    </header>

    <nav class="workbench-quick-nav" aria-label="快捷入口">
      <button
        v-for="link in quickLinks"
        :key="link.key"
        type="button"
        class="workbench-quick-nav__item"
        @click="goQuickLink(link.path)"
      >
        <span class="workbench-quick-nav__icon" aria-hidden="true">
          <component :is="link.icon" class="h-4 w-4" :stroke-width="ICON_STROKE" />
        </span>
        <span class="workbench-quick-nav__label">{{ link.label }}</span>
        <span v-if="link.badge" class="workbench-quick-nav__badge">{{ link.badge }}</span>
      </button>
    </nav>

    <MaritimeAlertStatCards
      :cards="alertCards"
      :loading="loading && !data"
      @navigate="(q) => goVesselSchedules(q)"
    />

    <section v-if="slaSummary" class="panel workbench-sla-summary px-4 py-3">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="workbench-panel-title">异常跟踪</h2>
          <p class="mt-1 text-xs text-zinc-500">运输时效预警摘要</p>
        </div>
        <NButton size="small" quaternary @click="router.push('/shipment-exceptions')">查看全部</NButton>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          class="workbench-sla-chip"
          @click="router.push({ path: '/shipment-exceptions', query: { status: 'open' } })"
        >
          待处理 <strong>{{ slaSummary.pendingOpen }}</strong>
        </button>
        <button
          type="button"
          class="workbench-sla-chip workbench-sla-chip--danger"
          @click="router.push({ path: '/shipment-exceptions', query: { timelinessStatus: 'severe_overdue', status: 'open' } })"
        >
          严重超时 <strong>{{ slaSummary.severeOverdue }}</strong>
        </button>
        <button
          type="button"
          class="workbench-sla-chip workbench-sla-chip--warn"
          @click="router.push({ path: '/shipment-exceptions', query: { timelinessStatus: 'overdue', status: 'open' } })"
        >
          已超时 <strong>{{ slaSummary.overdue }}</strong>
        </button>
        <button
          type="button"
          class="workbench-sla-chip"
          @click="router.push({ path: '/shipment-exceptions', query: { hasException: 'true' } })"
        >
          当前人工异常 <strong>{{ slaSummary.currentExceptions }}</strong>
        </button>
      </div>
    </section>

    <NSpin :show="loading && !data">
      <div v-if="error" class="panel px-4 py-3 text-sm text-red-400">{{ error }}</div>

      <template v-else-if="data">
        <div class="workbench-modules">
        <article v-if="hasBatchReminders" class="panel workbench-alerts workbench-alerts--batch">
          <div class="workbench-panel-head">
            <h2 class="workbench-panel-title">
              批次提醒
              <span v-if="batchReminderCount" class="workbench-panel-count">{{ batchReminderCount }}</span>
            </h2>
          </div>
          <div class="workbench-batch-columns">
            <section class="workbench-batch-column">
              <div class="workbench-batch-column__head">
                <h3 class="workbench-panel-title">
                  待办提醒
                  <span v-if="todoItems.length" class="workbench-panel-count">{{ todoItems.length }}</span>
                </h3>
                <button
                  v-if="hasGroupNotifications"
                  type="button"
                  class="workbench-link-btn"
                  :disabled="markingGroupRead"
                  @click="dismissAllGroupNotifications"
                >
                  分组全部已读
                </button>
              </div>
              <ul v-if="todoItems.length" class="workbench-feed workbench-feed--alerts">
                <li v-for="n in todoItems" :key="n.id">
                  <ShipmentGroupAlertCard
                    v-if="n.kind === 'group'"
                    :title="n.group.title"
                    :subtitle="formatGroupNoDisplay(n.group.groupNo)"
                    :customer-name="n.group.customer || ''"
                    :rule-type="n.group.ruleType"
                    :message="n.group.message"
                    :triggered-at="n.group.triggeredAt"
                    :severity="n.group.severity"
                    clickable
                    @click="goShipmentGroup(n.group.groupId)"
                  >
                    <template #aside>
                      <button
                        type="button"
                        class="group-alert-card__btn"
                        @click.stop="dismissGroupNotification(n.group)"
                      >
                        知道了
                      </button>
                      <button
                        type="button"
                        class="group-alert-card__btn group-alert-card__btn--ghost"
                        @click.stop="resolveGroupNotification(n.group)"
                      >
                        已处理
                      </button>
                    </template>
                  </ShipmentGroupAlertCard>
                  <ShipmentGroupAlertCard
                    v-else
                    :title="n.exception.title"
                    :subtitle="n.exception.shipmentNo"
                    :customer-name="n.exception.customer || ''"
                    rule-type="EXCEPTION_FOLLOWUP"
                    :message="n.exception.message"
                    :triggered-at="n.exception.triggeredAt"
                    :severity="n.exception.severity"
                    clickable
                    @click="goShipment(n.exception.shipmentNo)"
                  >
                    <template #aside>
                      <button
                        type="button"
                        class="group-alert-card__btn"
                        @click.stop="dismissExceptionFollowup(n.exception)"
                      >
                        知道了
                      </button>
                      <button
                        type="button"
                        class="group-alert-card__btn group-alert-card__btn--ghost"
                        @click.stop="resolveExceptionFollowup(n.exception)"
                      >
                        已跟进
                      </button>
                    </template>
                  </ShipmentGroupAlertCard>
                </li>
              </ul>
              <p v-else class="workbench-batch-empty">暂无待办提醒</p>
            </section>

            <section class="workbench-batch-column">
              <div class="workbench-batch-column__head">
                <h3 class="workbench-panel-title">
                  消息提醒
                  <span v-if="shipmentArrivalNotifications.length" class="workbench-panel-count">{{
                    shipmentArrivalNotifications.length
                  }}</span>
                </h3>
                <button
                  v-if="shipmentArrivalNotifications.length"
                  type="button"
                  class="workbench-link-btn"
                  :disabled="markingShipmentRead"
                  @click="dismissAllShipmentNotifications"
                >
                  全部已读
                </button>
              </div>
              <ul v-if="shipmentArrivalNotifications.length" class="workbench-feed">
                <li
                  v-for="n in shipmentArrivalNotifications"
                  :key="n.id"
                  class="workbench-feed__item"
                  :class="{ 'workbench-feed__item--delivered': hasDeliveredKeyword(n.latestDesc) }"
                >
                  <button type="button" class="workbench-feed__body" @click="goShipment(n.shipmentNo)">
                    <div class="workbench-feed__row">
                      <NTag size="small" :bordered="false" type="info">运单轨迹更新</NTag>
                      <span class="workbench-feed__primary">{{ n.shipmentNo }}</span>
                      <span v-if="n.customer" class="workbench-feed__muted">{{ n.customer }}</span>
                    </div>
                    <p class="workbench-feed__desc line-clamp-2">
                      <template
                        v-for="(part, idx) in splitDeliveredHighlight(n.latestDesc)"
                        :key="idx"
                      >
                        <span v-if="part.highlight" class="workbench-feed__highlight">{{ part.text }}</span>
                        <span v-else>{{ part.text }}</span>
                      </template>
                    </p>
                    <p class="workbench-feed__meta">
                      {{ trackingSourceLabel(n.trackingSource) }}
                      · {{ formatTime(n.latestTime) }}
                    </p>
                  </button>
                  <NButton size="tiny" quaternary @click="dismissShipmentArrival(n)">知道了</NButton>
                </li>
              </ul>
              <p v-else class="workbench-batch-empty">暂无消息提醒</p>
            </section>
          </div>
        </article>

        <article class="panel workbench-alerts">
          <div class="workbench-panel-head">
            <h2 class="workbench-panel-title">
              海运预警 &amp; ETA 提醒
              <span v-if="alertFeedItems.length" class="workbench-panel-count">{{
                alertFeedItems.length
              }}</span>
            </h2>
            <button
              v-if="hasUnreadPortNotifications"
              type="button"
              class="workbench-link-btn"
              :disabled="markingAllRead"
              @click="dismissAllPortNotifications"
            >
              全部已读
            </button>
          </div>

          <ul v-if="alertFeedItems.length" class="workbench-feed">
            <li
              v-for="item in alertFeedItems"
              :key="item.id"
              class="workbench-feed__item"
            >
              <template v-if="item.kind === 'port'">
                <button type="button" class="workbench-feed__body" @click="goVoyage(item.data.voyageId)">
                  <div class="workbench-feed__row">
                    <span class="workbench-feed__icon-clock" aria-hidden="true">
                      <Clock class="h-4 w-4" :stroke-width="ICON_STROKE" />
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
                      <Clock class="h-4 w-4" :stroke-width="ICON_STROKE" />
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
                      <Clock class="h-4 w-4" :stroke-width="ICON_STROKE" />
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
          <p v-else class="workbench-feed-empty">
            暂无海运预警或 ETA 提醒
            <NButton size="tiny" quaternary class="mt-2" @click="goVesselSchedules()">打开船期监控</NButton>
          </p>
        </article>

        <div class="workbench-columns">
          <article class="panel workbench-column">
            <div class="workbench-panel-head">
              <h3 class="workbench-panel-title">
                关注运单
                <span v-if="urgentShipments.length" class="workbench-panel-count">{{
                  urgentShipments.length
                }}</span>
              </h3>
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
            <p v-else class="workbench-list-empty">
              暂无关注运单
              <NButton size="tiny" quaternary class="mt-2" @click="goShipmentsList">查看运单列表</NButton>
            </p>
          </article>

          <article class="panel workbench-column">
            <div class="workbench-panel-head">
              <h3 class="workbench-panel-title">
                挂靠预警
                <span v-if="urgentPortCalls.length" class="workbench-panel-count">{{
                  urgentPortCalls.length
                }}</span>
              </h3>
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
            <p v-else class="workbench-list-empty">
              暂无挂靠预警
              <NButton size="tiny" quaternary class="mt-2" @click="goVesselSchedules()">打开船期监控</NButton>
            </p>
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
  gap: 1.25rem;
}

.workbench-modules {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.workbench-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem 1.5rem;
  padding: 1.25rem 1.5rem;
}

.workbench-hero__eyebrow {
  margin: 0;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.workbench-hero__title {
  margin: 0.25rem 0 0;
  color: var(--color-fg-emphasis);
}

.workbench-hero__meta {
  margin: 0.5rem 0 0;
}

.workbench-hero__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  margin-top: 1rem;
}

.workbench-hero__stat {
  display: inline-flex;
  align-items: baseline;
  gap: 0.375rem;
}

.workbench-hero__stat-value {
  font-size: 1.125rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.workbench-hero__stat-label {
  font-size: 0.75rem;
  color: var(--color-muted);
}

.workbench-hero__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.workbench-quick-nav {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.625rem;
}

@media (min-width: 640px) {
  .workbench-quick-nav {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.workbench-quick-nav__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.75rem;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border);
  border-radius: 0.625rem;
  background: var(--color-panel);
  color: var(--color-fg-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.workbench-quick-nav__item:hover {
  border-color: color-mix(in srgb, var(--color-accent) 28%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 4%, var(--color-panel));
  color: var(--color-fg-emphasis);
}

.workbench-quick-nav__item:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--color-accent) 45%, transparent);
  outline-offset: 2px;
}

.workbench-quick-nav__icon {
  display: inline-flex;
  flex-shrink: 0;
  color: var(--color-accent-text);
}

.workbench-quick-nav__label {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.workbench-quick-nav__badge {
  flex-shrink: 0;
  min-width: 1.25rem;
  padding: 0.125rem 0.375rem;
  border-radius: 9999px;
  background: var(--color-accent);
  color: #fff;
  font-size: 0.6875rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
  text-align: center;
}

.workbench-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.workbench-panel-title {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.workbench-panel-count {
  display: inline-flex;
  min-width: 1.25rem;
  align-items: center;
  justify-content: center;
  padding: 0.125rem 0.4375rem;
  border-radius: 9999px;
  background: color-mix(in srgb, var(--color-accent) 12%, var(--color-btn-ghost-bg));
  color: var(--color-accent-text);
  font-size: 0.6875rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.workbench-link-btn {
  border: none;
  background: transparent;
  padding: 0.25rem 0.5rem;
  margin: -0.25rem -0.5rem;
  border-radius: 0.375rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-accent-text);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.workbench-link-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-accent) 10%, transparent);
  color: var(--color-accent-hover);
}

.workbench-link-btn:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--color-accent) 45%, transparent);
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

.workbench-feed--alerts {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.workbench-feed--alerts > li {
  list-style: none;
}

.workbench-alerts--batch {
  border-color: var(--group-alert-warning-border);
}

.workbench-batch-columns {
  display: grid;
  gap: 1.25rem;
}

@media (min-width: 1024px) {
  .workbench-batch-columns {
    grid-template-columns: 1fr 1fr;
  }
}

.workbench-batch-column {
  min-width: 0;
}

.workbench-batch-column__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.workbench-batch-empty {
  padding: 1.5rem 0;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--color-muted);
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
  display: flex;
  flex-direction: column;
  align-items: center;
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
  outline: 2px solid color-mix(in srgb, var(--color-accent) 45%, transparent);
  outline-offset: 2px;
}

.workbench-feed__body:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--color-accent) 45%, transparent);
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

[data-theme='dark'] .workbench-column:hover,
[data-theme='dark'] .workbench-alerts:hover {
  box-shadow: 0 2px 12px rgb(0 0 0 / 0.2);
}

.workbench-footnote {
  padding: 1rem 1.25rem;
}

.workbench-sla-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 9999px;
  border: 1px solid var(--color-border);
  background: var(--color-btn-ghost-bg);
  font-size: 0.8125rem;
  color: var(--color-fg-secondary);
  cursor: pointer;
}

.workbench-sla-chip strong {
  color: var(--color-fg-emphasis);
}

.workbench-sla-chip--warn {
  border-color: rgb(245 158 11 / 0.35);
  color: rgb(180 83 9);
}

.workbench-sla-chip--danger {
  border-color: rgb(239 68 68 / 0.35);
  color: rgb(185 28 28);
}

/* 知道了 等操作按钮 hover */
.workbench-feed :deep(.n-button.n-button--quaternary-type:hover) {
  background-color: var(--color-btn-ghost-hover) !important;
}

@media (prefers-reduced-motion: reduce) {
  .workbench-feed__item,
  .workbench-list__item,
  .workbench-column,
  .workbench-alerts,
  .workbench-link-btn,
  .workbench-quick-nav__item,
  .workbench-feed__body {
    transition: none;
  }
}
</style>
