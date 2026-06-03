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
    /* 顶栏静默失败，避免打断操作 */
  } finally {
    loading.value = false
  }
}

async function dismissOne(n: ShipmentTrackingNotification) {
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
  popoverShow.value = false
  router.push({ path: '/shipments', query: { shipmentNo } })
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
    :width="360"
    :show-arrow="false"
    @update:show="onPopoverShowChange"
  >
    <template #trigger>
      <button
        type="button"
        class="subscription-bell-trigger"
        :class="{ 'subscription-bell-trigger--active': hasUnread }"
        aria-label="订阅消息"
        title="订阅消息"
      >
        <BellIcon :filled="hasUnread" size="1.125rem" />
        <span v-if="hasUnread" class="subscription-bell-badge" aria-hidden="true" />
      </button>
    </template>

    <div class="subscription-popover">
      <div class="subscription-popover__head">
        <span class="subscription-popover__title">订阅消息</span>
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
        <p v-if="!loading && items.length === 0" class="subscription-popover__empty">
          暂无未读订阅消息
        </p>
        <ul v-else class="subscription-popover__list">
          <li
            v-for="n in items"
            :key="n.id"
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
            <NButton size="tiny" quaternary @click="dismissOne(n)">知道了</NButton>
          </li>
        </ul>
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
  max-height: min(24rem, 70vh);
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

.subscription-popover__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: min(20rem, 60vh);
  overflow-y: auto;
}

.subscription-popover__item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: rgb(14 165 233 / 0.08);
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
