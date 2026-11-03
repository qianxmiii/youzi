<script setup lang="ts">
import { Workflow } from 'lucide-vue-next'
import { NPopover, NSpin } from 'naive-ui'
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getOrderFlowNodes, markOrderFlowRemindersSeen, type OrderFlowNodeCount } from '@/api/orderFlow'
import { useOrderFlowTodoCount } from '@/composables/useOrderFlowTodoCount'
import { ICON_STROKE } from '@/constants/icons'

const router = useRouter()
const { orderFlowTodoCount, refreshOrderFlowTodoCount } = useOrderFlowTodoCount()

const popoverShow = ref(false)
const loading = ref(false)
const unseenCount = ref(0)
const nodes = ref<OrderFlowNodeCount[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

async function load() {
  loading.value = true
  try {
    const res = await getOrderFlowNodes()
    unseenCount.value = res.unseenCount
    nodes.value = res.nodes
    await markOrderFlowRemindersSeen()
    await refreshOrderFlowTodoCount()
  } catch {
    nodes.value = []
    unseenCount.value = 0
  } finally {
    loading.value = false
  }
}

function isMineStatus(status: string) {
  return status.startsWith('销售-')
}

function openStatus(status: string) {
  popoverShow.value = false
  if (status === '已结束') {
    void router.push({ path: '/order-flow', query: { scope: 'ended' } })
    return
  }
  if (isMineStatus(status)) {
    void router.push({ path: '/order-flow', query: { scope: 'mine', status } })
    return
  }
  void router.push({ path: '/order-flow', query: { scope: 'active', status } })
}

function onPopoverShowChange(show: boolean) {
  if (show) void load()
}

onMounted(() => {
  void refreshOrderFlowTodoCount()
  pollTimer = setInterval(() => {
    if (!popoverShow.value) void refreshOrderFlowTodoCount()
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
    :width="340"
    :show-arrow="false"
    display-directive="if"
    @update:show="onPopoverShowChange"
  >
    <template #trigger>
      <button
        type="button"
        class="order-flow-bell"
        :class="{ 'order-flow-bell--active': orderFlowTodoCount > 0 }"
        aria-label="订单流转待办"
        title="订单流转待办"
      >
        <Workflow class="h-4 w-4" :stroke-width="ICON_STROKE" aria-hidden="true" />
        <span v-if="orderFlowTodoCount > 0" class="order-flow-bell__count">
          {{ orderFlowTodoCount > 99 ? '99+' : orderFlowTodoCount }}
        </span>
      </button>
    </template>

    <div class="order-flow-popover">
      <div class="order-flow-popover__head">
        <span>订单流转</span>
        <span class="order-flow-popover__unseen">未看的新节点 {{ unseenCount }}</span>
      </div>
      <NSpin :show="loading" size="small">
        <p v-if="!loading && nodes.length === 0" class="order-flow-popover__empty">还没有流转数据</p>
        <ul v-else class="order-flow-popover__list">
          <li v-for="node in nodes" :key="node.status">
            <button
              type="button"
              class="order-flow-popover__item"
              :class="{ 'order-flow-popover__item--mine': isMineStatus(node.status) }"
              @click="openStatus(node.status)"
            >
              <span class="order-flow-popover__no">{{ node.status }}</span>
              <span v-if="isMineStatus(node.status)" class="order-flow-popover__mine">待处理</span>
              <span class="order-flow-popover__count">{{ node.count }}</span>
              <span v-if="node.unseen > 0" class="order-flow-popover__plus">+{{ node.unseen }}</span>
            </button>
          </li>
        </ul>
      </NSpin>
    </div>
  </NPopover>
</template>

<style scoped>
.order-flow-bell {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  border: 1px solid rgb(139 92 246 / 0.45);
  background: rgb(139 92 246 / 0.08);
  color: rgb(109 40 217);
  cursor: pointer;
}

.order-flow-bell:hover,
.order-flow-bell--active {
  background: rgb(139 92 246 / 0.16);
  color: rgb(91 33 182);
}

.order-flow-bell__count {
  position: absolute;
  top: -0.35rem;
  right: -0.4rem;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.25rem;
  border-radius: 9999px;
  background: rgb(109 40 217);
  color: white;
  font-size: 0.625rem;
  font-weight: 700;
  line-height: 1rem;
  text-align: center;
}

.order-flow-popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding-bottom: 0.5rem;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  font-size: 0.875rem;
  font-weight: 600;
}

.order-flow-popover__link,
.order-flow-popover__item {
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.order-flow-popover__link {
  font-size: 0.75rem;
  font-weight: 500;
  color: rgb(109 40 217);
}

.order-flow-popover__empty {
  margin: 0;
  padding: 1.25rem 0.25rem;
  text-align: center;
  font-size: 0.8125rem;
  color: var(--color-muted);
}

.order-flow-popover__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 18rem;
  overflow-y: auto;
}

.order-flow-popover__unseen {
  font-size: 0.75rem;
  font-weight: 600;
  color: rgb(109 40 217);
}

.order-flow-popover__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.45rem 0.25rem;
  border-radius: 0.5rem;
}

.order-flow-popover__count {
  margin-left: auto;
  font-size: 0.875rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.order-flow-popover__plus {
  min-width: 1.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: rgb(109 40 217);
}

.order-flow-popover__item:hover {
  background: rgb(139 92 246 / 0.08);
}

.order-flow-popover__item--mine {
  background: color-mix(in srgb, #f59e0b 16%, transparent);
}

.order-flow-popover__item--mine:hover {
  background: color-mix(in srgb, #f59e0b 26%, transparent);
}

.order-flow-popover__mine {
  flex-shrink: 0;
  border-radius: 999px;
  background: rgb(245 158 11 / 0.22);
  padding: 0 6px;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
  color: rgb(180 83 9);
}

[data-theme='dark'] .order-flow-popover__mine {
  color: rgb(253 230 138);
}

.order-flow-popover__no {
  font-size: 0.8125rem;
  font-weight: 600;
}

.order-flow-popover__status {
  font-size: 0.75rem;
  color: rgb(109 40 217);
}

.order-flow-popover__meta {
  font-size: 0.75rem;
  color: var(--color-muted);
}

[data-theme='dark'] .order-flow-bell {
  color: rgb(196 181 253);
  border-color: rgb(167 139 250 / 0.5);
}

[data-theme='dark'] .order-flow-bell__count {
  background: rgb(139 92 246);
}
</style>
