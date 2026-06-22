<script setup lang="ts">
import { NButton, NPopover, NSpin, NTag, useMessage } from 'naive-ui'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getShipmentGroupUnreadNotifications,
  markAllShipmentGroupNotificationsRead,
  markShipmentGroupNotificationRead,
  type ShipmentGroupNotification,
} from '@/api/shipmentGroups'
import {
  getShipmentTrackingNotifications,
  markAllShipmentTrackingNotificationsRead,
  markShipmentTrackingNotificationRead,
  type ShipmentTrackingNotification,
} from '@/api/shipmentSubscriptions'
import BellIcon from '@/components/common/BellIcon.vue'
import { hasDeliveredKeyword, splitDeliveredHighlight } from '@/utils/highlightDelivered'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const trackingItems = ref<ShipmentTrackingNotification[]>([])
const groupItems = ref<ShipmentGroupNotification[]>([])
const trackingUnread = ref(0)
const groupUnread = ref(0)
const popoverShow = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

const unreadCount = computed(() => trackingUnread.value + groupUnread.value)
const hasUnread = computed(() => unreadCount.value > 0)
const hasAnyItems = computed(() => trackingItems.value.length > 0 || groupItems.value.length > 0)

const severityTag: Record<string, 'default' | 'warning' | 'error'> = {
  info: 'default',
  warning: 'warning',
  urgent: 'error',
}

function trackingSourceLabel(source: string): string {
  if (source === 'internal') return '内部轨迹'
  if (source === 'carrier') return '承运商轨迹'
  if (source === 'arrival') return '到港'
  return '轨迹'
}

function groupDisplayLabel(n: ShipmentGroupNotification): string {
  const name = n.groupName?.trim()
  if (name) return `${name}（${n.groupNo || ''}）`
  return n.groupNo || '分组'
}

function formatTime(raw: string | null | undefined) {
  return raw ? raw.slice(0, 16) : '—'
}

async function load() {
  loading.value = true
  try {
    const [trackingRes, groupRes] = await Promise.all([
      getShipmentTrackingNotifications(20),
      getShipmentGroupUnreadNotifications(20),
    ])
    trackingItems.value = trackingRes.items
    trackingUnread.value = trackingRes.unreadCount
    groupItems.value = groupRes.items
    groupUnread.value = groupRes.unreadCount
  } catch {
    /* 顶栏静默失败，避免打断操作 */
  } finally {
    loading.value = false
  }
}

async function dismissTracking(n: ShipmentTrackingNotification) {
  try {
    await markShipmentTrackingNotificationRead(n.id)
    trackingItems.value = trackingItems.value.filter((x) => x.id !== n.id)
    trackingUnread.value = Math.max(0, trackingUnread.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissGroup(n: ShipmentGroupNotification) {
  try {
    await markShipmentGroupNotificationRead(n.id)
    groupItems.value = groupItems.value.filter((x) => x.id !== n.id)
    groupUnread.value = Math.max(0, groupUnread.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissAll() {
  if (!hasUnread.value) return
  try {
    const [trackingRes, groupRes] = await Promise.all([
      trackingUnread.value > 0 ? markAllShipmentTrackingNotificationsRead() : Promise.resolve({ count: 0 }),
      groupUnread.value > 0 ? markAllShipmentGroupNotificationsRead() : Promise.resolve(0),
    ])
    trackingItems.value = []
    groupItems.value = []
    trackingUnread.value = 0
    groupUnread.value = 0
    const total = (trackingRes.count ?? 0) + (groupRes ?? 0)
    if (total > 0) {
      message.success('已标记 ' + String(total) + ' 条为已读')
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

function goShipment(shipmentNo: string) {
  const sn = shipmentNo.trim()
  if (!sn) return
  popoverShow.value = false
  router.push({ path: '/shipments', query: { shipmentNo: sn, fromNotify: '1' } })
}

function goGroup(groupId: string) {
  if (!groupId) return
  popoverShow.value = false
  router.push({ path: '/shipment-groups', query: { groupId } })
}

function onPopoverShowChange(show: boolean) {
  popoverShow.value = show
  if (show) void load()
}

onMounted(() => {
  void load()
  pollTimer = setInterval(() => {
    if (!popoverShow.value) void load()
  }, 60_000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <NPopover
    trigger="click"
    placement="bottom-end"
    :show="popoverShow"
    :width="380"
    :show-arrow="false"
    @update:show="onPopoverShowChange"
  >
    <template #trigger>
      <button
        type="button"
        class="subscription-bell-trigger"
        :class="{ 'subscription-bell-trigger--active': hasUnread }"
        aria-label="消息通知"
        title="消息通知"
      >
        <BellIcon :filled="hasUnread" size="1.125rem" />
        <span v-if="hasUnread" class="subscription-bell-badge" aria-hidden="true" />
      </button>
    </template>

    <div class="subscription-popover">
      <div class="subscription-popover__head">
        <span class="subscription-popover__title">消息通知</span>
        <NButton
          v-if="hasUnread"
          size="tiny"
          quaternary
          :disabled="loading"
          @click="dismissAll"
        >
          全部已读
        </NButton>
      </div>

      <NSpin :show="loading" size="small">
        <p v-if="!loading && !hasAnyItems" class="subscription-popover__empty">
          暂无未读消息
        </p>
        <div v-else class="subscription-popover__sections">
          <section v-if="groupItems.length" class="subscription-popover__section">
            <p class="subscription-popover__section-title">分组提醒</p>
            <ul class="subscription-popover__list">
              <li
                v-for="n in groupItems"
                :key="'g-' + n.id"
                class="subscription-popover__item subscription-popover__item--group"
              >
                <button type="button" class="subscription-popover__body" @click="goGroup(n.groupId)">
                  <p class="subscription-popover__shipment">
                    <NTag size="small" :type="severityTag[n.severity] ?? 'warning'" :bordered="false">
                      {{ n.title }}
                    </NTag>
                    <span class="subscription-popover__shipment-no">{{ groupDisplayLabel(n) }}</span>
                  </p>
                  <p class="subscription-popover__desc line-clamp-2">{{ n.message }}</p>
                  <p class="subscription-popover__meta">{{ formatTime(n.triggeredAt) }}</p>
                </button>
                <NButton size="tiny" quaternary @click="dismissGroup(n)">知道了</NButton>
              </li>
            </ul>
          </section>

          <section v-if="trackingItems.length" class="subscription-popover__section">
            <p class="subscription-popover__section-title">轨迹订阅</p>
            <ul class="subscription-popover__list">
              <li
                v-for="n in trackingItems"
                :key="'t-' + n.id"
                class="subscription-popover__item"
                :class="
                  hasDeliveredKeyword(n.latestDesc)
                    ? 'subscription-popover__item--delivered'
                    : ''
                "
              >
                <button type="button" class="subscription-popover__body" @click="goShipment(n.shipmentNo)">
                  <p class="subscription-popover__shipment">
                    <span class="subscription-popover__shipment-no">{{ n.shipmentNo }}</span>
                    <span v-if="n.customer" class="text-[var(--color-muted)]">{{ n.customer }}</span>
                    <span class="text-[var(--color-muted)]">{{ trackingSourceLabel(n.trackingSource) }}</span>
                  </p>
                  <p class="subscription-popover__desc line-clamp-2">
                    <template
                      v-for="(part, idx) in splitDeliveredHighlight(n.latestDesc)"
                      :key="idx"
                    >
                      <span v-if="part.highlight" class="subscription-popover__highlight">
                        {{ part.text }}
                      </span>
                      <span v-else>{{ part.text }}</span>
                    </template>
                  </p>
                  <p class="subscription-popover__meta">
                    {{ formatTime(n.latestTime) }} · {{ formatTime(n.createdAt) }}
                  </p>
                </button>
                <NButton size="tiny" quaternary @click="dismissTracking(n)">知道了</NButton>
              </li>
            </ul>
          </section>
        </div>
      </NSpin>
    </div>
  </NPopover>
</template>

<style scoped>
.subscription-bell-trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 0.5rem;
  padding: 0;
  background: transparent;
  color: rgb(113 113 122);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.subscription-bell-trigger:hover {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg);
}

.subscription-bell-trigger--active {
  color: rgb(124 58 237);
}

.subscription-bell-badge {
  position: absolute;
  top: 0.3125rem;
  right: 0.3125rem;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  background: rgb(239 68 68);
  border: 1.5px solid var(--color-panel);
  pointer-events: none;
}

.subscription-popover {
  max-height: min(28rem, 75vh);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.subscription-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0.5rem;
}

.subscription-popover__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.subscription-popover__empty {
  padding: 1.5rem 0.5rem;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.subscription-popover__sections {
  max-height: min(24rem, 65vh);
  overflow-y: auto;
}

.subscription-popover__section + .subscription-popover__section {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

.subscription-popover__section-title {
  margin: 0 0 0.375rem;
  padding: 0 0.5rem;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.subscription-popover__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.subscription-popover__item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: rgb(14 165 233 / 0.08);
}

.subscription-popover__item--group {
  background: rgb(245 158 11 / 0.08);
}

.subscription-popover__item + .subscription-popover__item {
  margin-top: 0.375rem;
}

.subscription-popover__item--delivered {
  background: rgb(16 185 129 / 0.1);
  border: 1px solid rgb(16 185 129 / 0.25);
}

.subscription-popover__body {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
}

.subscription-popover__shipment {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-fg-emphasis);
}

.subscription-popover__shipment-no {
  font-weight: 600;
  color: var(--color-accent-text);
}

.subscription-popover__highlight {
  border-radius: 0.125rem;
  background: rgb(70 72 212 / 0.12);
  padding: 0 0.125rem;
  font-weight: 600;
  color: var(--color-accent-text);
}

.subscription-popover__desc {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--color-muted);
}

.subscription-popover__meta {
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  color: var(--color-fg-secondary);
}

[data-theme='dark'] .subscription-bell-trigger--active {
  color: rgb(167 139 250);
}
</style>
