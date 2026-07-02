<script setup lang="ts">
import { ClipboardList } from 'lucide-vue-next'
import { NPopover, NSpin, useMessage } from 'naive-ui'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getExceptionFollowupTodoNotifications,
  markExceptionFollowupNotificationRead,
  resolveExceptionFollowupNotification,
  type ShipmentExceptionFollowupNotification,
} from '@/api/exceptionFollowup'
import {
  getShipmentGroupTodoNotifications,
  markShipmentGroupNotificationRead,
  resolveShipmentGroupNotification,
} from '@/api/shipmentGroups'
import type { ShipmentGroupNotification } from '@/types/shipmentGroup'
import ShipmentGroupAlertCard from '@/components/shipments/ShipmentGroupAlertCard.vue'
import { ICON_STROKE } from '@/constants/icons'
import { formatGroupNoDisplay } from '@/utils/shipmentGroup'

type TodoItem =
  | { kind: 'group'; id: string; triggeredAt: string; group: ShipmentGroupNotification }
  | { kind: 'exception'; id: string; triggeredAt: string; exception: ShipmentExceptionFollowupNotification }

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const items = ref<TodoItem[]>([])
const pendingCount = ref(0)
const popoverShow = ref(false)

let pollTimer: ReturnType<typeof setInterval> | null = null

const hasPending = computed(() => pendingCount.value > 0)

function mergeTodos(
  groups: ShipmentGroupNotification[],
  exceptions: ShipmentExceptionFollowupNotification[],
  limit: number,
): TodoItem[] {
  const merged: TodoItem[] = [
    ...groups.map((g) => ({
      kind: 'group' as const,
      id: `group:${g.id}`,
      triggeredAt: g.triggeredAt,
      group: g,
    })),
    ...exceptions.map((e) => ({
      kind: 'exception' as const,
      id: `exception:${e.id}`,
      triggeredAt: e.triggeredAt,
      exception: e,
    })),
  ]
  merged.sort((a, b) => b.triggeredAt.localeCompare(a.triggeredAt))
  return merged.slice(0, limit)
}

async function load() {
  loading.value = true
  try {
    const [groupRes, excRes] = await Promise.all([
      getShipmentGroupTodoNotifications(20),
      getExceptionFollowupTodoNotifications(20),
    ])
    items.value = mergeTodos(groupRes.items, excRes.items, 20)
    pendingCount.value = groupRes.pendingCount + excRes.pendingCount
  } catch {
    /* 顶栏静默失败 */
  } finally {
    loading.value = false
  }
}

async function dismissGroup(n: ShipmentGroupNotification) {
  try {
    await markShipmentGroupNotificationRead(n.id)
    const idx = items.value.findIndex((x) => x.kind === 'group' && x.group.id === n.id)
    if (idx >= 0) {
      const row = items.value[idx]
      if (row.kind === 'group') {
        items.value[idx] = {
          ...row,
          group: {
            ...row.group,
            readAt: new Date().toISOString().slice(0, 19).replace('T', ' '),
          },
        }
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function resolveGroup(n: ShipmentGroupNotification) {
  try {
    await resolveShipmentGroupNotification(n.id)
    items.value = items.value.filter((x) => !(x.kind === 'group' && x.group.id === n.id))
    pendingCount.value = Math.max(0, pendingCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function dismissException(n: ShipmentExceptionFollowupNotification) {
  try {
    await markExceptionFollowupNotificationRead(n.id)
    const idx = items.value.findIndex((x) => x.kind === 'exception' && x.exception.id === n.id)
    if (idx >= 0) {
      const row = items.value[idx]
      if (row.kind === 'exception') {
        items.value[idx] = {
          ...row,
          exception: {
            ...row.exception,
            readAt: new Date().toISOString().slice(0, 19).replace('T', ' '),
          },
        }
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function resolveException(n: ShipmentExceptionFollowupNotification) {
  try {
    await resolveExceptionFollowupNotification(n.id)
    items.value = items.value.filter((x) => !(x.kind === 'exception' && x.exception.id === n.id))
    pendingCount.value = Math.max(0, pendingCount.value - 1)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

function goGroup(groupId: string) {
  if (!groupId) return
  popoverShow.value = false
  router.push({ path: '/shipment-groups', query: { groupId } })
}

function goShipment(shipmentNo: string) {
  if (!shipmentNo) return
  popoverShow.value = false
  router.push({ path: '/shipments', query: { shipmentNo } })
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
    :width="400"
    :show-arrow="false"
    display-directive="if"
    @update:show="onPopoverShowChange"
  >
    <template #trigger>
      <button
        type="button"
        class="header-notify-trigger header-notify-trigger--todo"
        :class="{ 'header-notify-trigger--active': hasPending }"
        aria-label="待办通知"
        title="待办通知"
      >
        <ClipboardList class="h-[1.125rem] w-[1.125rem]" :stroke-width="ICON_STROKE" aria-hidden="true" />
        <span v-if="hasPending" class="header-notify-badge" aria-hidden="true" />
      </button>
    </template>

    <div class="header-notify-popover">
      <div class="header-notify-popover__head">
        <span class="header-notify-popover__title">待办</span>
        <span v-if="hasPending" class="header-notify-popover__count">{{ pendingCount }} 项待处理</span>
      </div>

      <NSpin :show="loading" size="small">
        <p v-if="!loading && items.length === 0" class="header-notify-popover__empty">
          暂无待办
        </p>
        <ul v-else class="header-notify-popover__list header-notify-popover__list--alerts">
          <li v-for="n in items" :key="n.id">
            <ShipmentGroupAlertCard
              v-if="n.kind === 'group'"
              compact
              clickable
              :title="n.group.title"
              :subtitle="formatGroupNoDisplay(n.group.groupNo)"
              :customer-name="n.group.customer || ''"
              :rule-type="n.group.ruleType"
              :message="n.group.message"
              :triggered-at="n.group.triggeredAt"
              :severity="n.group.severity"
              :read="Boolean(n.group.readAt)"
              :resolved="Boolean(n.group.resolvedAt)"
              @click="goGroup(n.group.groupId)"
            >
              <template #aside>
                <button type="button" class="group-alert-card__btn" @click.stop="dismissGroup(n.group)">
                  知道了
                </button>
                <button
                  type="button"
                  class="group-alert-card__btn group-alert-card__btn--ghost"
                  @click.stop="resolveGroup(n.group)"
                >
                  已处理
                </button>
              </template>
            </ShipmentGroupAlertCard>

            <ShipmentGroupAlertCard
              v-else
              compact
              clickable
              :title="n.exception.title"
              :subtitle="n.exception.shipmentNo"
              :customer-name="n.exception.customer || ''"
              rule-type="EXCEPTION_FOLLOWUP"
              :message="n.exception.message"
              :triggered-at="n.exception.triggeredAt"
              :severity="n.exception.severity"
              :read="Boolean(n.exception.readAt)"
              :resolved="Boolean(n.exception.resolvedAt)"
              @click="goShipment(n.exception.shipmentNo)"
            >
              <template #aside>
                <button type="button" class="group-alert-card__btn" @click.stop="dismissException(n.exception)">
                  知道了
                </button>
                <button
                  type="button"
                  class="group-alert-card__btn group-alert-card__btn--ghost"
                  @click.stop="resolveException(n.exception)"
                >
                  已跟进
                </button>
              </template>
            </ShipmentGroupAlertCard>
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

.header-notify-trigger--todo.header-notify-trigger--active {
  color: rgb(217 119 6);
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

.header-notify-popover__count {
  font-size: 0.75rem;
  color: rgb(217 119 6);
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

.header-notify-popover__list--alerts {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.header-notify-popover__list--alerts > li {
  list-style: none;
}

[data-theme='dark'] .header-notify-trigger--todo.header-notify-trigger--active {
  color: rgb(251 191 36);
}
</style>
