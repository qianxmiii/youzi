<script setup lang="ts">
import { NButton, NPopover, NSpin, useMessage } from 'naive-ui'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
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
const items = ref<ShipmentTrackingNotification[]>([])
const unreadCount = ref(0)
const popoverShow = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

const hasUnread = computed(() => unreadCount.value > 0)

function trackingSourceLabel(source: string): string {
  if (source === 'internal') return '内部轨迹'
  if (source === 'carrier') return '承运商轨迹'
  if (source === 'arrival') return '到港'
  return '轨迹'
}

function formatTime(raw: string | null | undefined) {
  return raw ? raw.slice(0, 16) : '—'
}

async function load() {
  loading.value = true
  try {
    const res = await getShipmentTrackingNotifications(20)
    items.value = res.items
    unreadCount.value = res.unreadCount
  } catch {
    /* 顶栏静默失败 */
  } finally {
    loading.value = false
  }
}

async function dismiss(n: ShipmentTrackingNotification) {
  try {
    await markShipmentTrackingNotificationRead(n.id)
    items.value = items.value.filter((x) => x.id !== n.id)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissAll() {
  if (!hasUnread.value) return
  try {
    const res = await markAllShipmentTrackingNotificationsRead()
    items.value = []
    unreadCount.value = 0
    if (res.count > 0) {
      message.success('已标记 ' + String(res.count) + ' 条为已读')
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

function onPopoverShowChange(show: boolean) {
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
    v-model:show="popoverShow"
    trigger="click"
    placement="bottom-end"
    :width="380"
    :show-arrow="false"
    display-directive="if"
    @update:show="onPopoverShowChange"
  >
    <template #trigger>
      <button
        type="button"
        class="header-notify-trigger header-notify-trigger--message"
        :class="{ 'header-notify-trigger--active': hasUnread }"
        aria-label="消息通知"
        title="消息通知"
      >
        <BellIcon :filled="hasUnread" size="1.125rem" />
        <span v-if="hasUnread" class="header-notify-badge" aria-hidden="true" />
      </button>
    </template>

    <div class="header-notify-popover">
      <div class="header-notify-popover__head">
        <span class="header-notify-popover__title">消息通知</span>
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
        <p v-if="!loading && items.length === 0" class="header-notify-popover__empty">
          暂无未读消息
        </p>
        <ul v-else class="header-notify-popover__list">
          <li
            v-for="n in items"
            :key="n.id"
            class="header-notify-popover__item"
            :class="
              hasDeliveredKeyword(n.latestDesc) ? 'header-notify-popover__item--delivered' : ''
            "
          >
            <button type="button" class="header-notify-popover__body" @click="goShipment(n.shipmentNo)">
              <p class="header-notify-popover__shipment">
                <span class="header-notify-popover__shipment-no">{{ n.shipmentNo }}</span>
                <span v-if="n.customer" class="text-[var(--color-muted)]">{{ n.customer }}</span>
                <span class="text-[var(--color-muted)]">{{ trackingSourceLabel(n.trackingSource) }}</span>
              </p>
              <p class="header-notify-popover__desc line-clamp-2">
                <template v-for="(part, idx) in splitDeliveredHighlight(n.latestDesc)" :key="idx">
                  <span v-if="part.highlight" class="header-notify-popover__highlight">
                    {{ part.text }}
                  </span>
                  <span v-else>{{ part.text }}</span>
                </template>
              </p>
              <p class="header-notify-popover__meta">
                {{ formatTime(n.latestTime) }} · {{ formatTime(n.createdAt) }}
              </p>
            </button>
            <NButton size="tiny" quaternary @click="dismiss(n)">知道了</NButton>
          </li>
        </ul>
      </NSpin>
    </div>
  </NPopover>
</template>

<style scoped>
.header-notify-trigger {
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

.header-notify-trigger:hover {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg);
}

.header-notify-trigger--message.header-notify-trigger--active {
  color: rgb(124 58 237);
}

.header-notify-badge {
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

.header-notify-popover {
  max-height: min(28rem, 75vh);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.header-notify-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.625rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0.5rem;
}

.header-notify-popover__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.header-notify-popover__empty {
  padding: 1.5rem 0.5rem;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.header-notify-popover__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: min(24rem, 65vh);
  overflow-y: auto;
}

.header-notify-popover__item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: rgb(14 165 233 / 0.08);
}

.header-notify-popover__item + .header-notify-popover__item {
  margin-top: 0.375rem;
}

.header-notify-popover__item--delivered {
  background: rgb(16 185 129 / 0.1);
  border: 1px solid rgb(16 185 129 / 0.25);
}

.header-notify-popover__body {
  flex: 1;
  min-width: 0;
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  cursor: pointer;
}

.header-notify-popover__shipment {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--color-fg-emphasis);
}

.header-notify-popover__shipment-no {
  font-weight: 600;
  color: var(--color-accent-text);
}

.header-notify-popover__highlight {
  border-radius: 0.125rem;
  background: rgb(70 72 212 / 0.12);
  padding: 0 0.125rem;
  font-weight: 600;
  color: var(--color-accent-text);
}

.header-notify-popover__desc {
  margin-top: 0.25rem;
  font-size: 0.75rem;
  line-height: 1.45;
  color: var(--color-muted);
}

.header-notify-popover__meta {
  margin-top: 0.25rem;
  font-size: 0.6875rem;
  color: var(--color-fg-secondary);
}

[data-theme='dark'] .header-notify-trigger--message.header-notify-trigger--active {
  color: rgb(167 139 250);
}
</style>
