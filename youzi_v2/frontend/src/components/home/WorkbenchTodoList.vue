<script setup lang="ts">
import { NButton, NTabs, NTabPane } from 'naive-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { WorkbenchTodoItem, WorkbenchTodoKind } from '@/api/workbench'

const props = defineProps<{
  items: WorkbenchTodoItem[]
  loading?: boolean
  error?: string | null
  available?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()
const tab = ref<'all' | WorkbenchTodoKind>('all')

const filtered = computed(() => {
  if (tab.value === 'all') return props.items
  return props.items.filter((item) => item.kinds.includes(tab.value as WorkbenchTodoKind))
})

function severityClass(severity: string) {
  if (severity === 'severe') return 'todo-row--severe'
  if (severity === 'high') return 'todo-row--high'
  return ''
}

function openItem(item: WorkbenchTodoItem) {
  const href = (item.href || '').trim()
  if (!href) return
  void router.push(href)
}

function openAll() {
  if (tab.value === 'payment') {
    void router.push({ path: '/shipments/payment-reminders', query: { scope: 'todo' } })
    return
  }
  if (tab.value === 'tracking_review') {
    void router.push({ path: '/approvals/tracking-time', query: { status: 'pending_review' } })
    return
  }
  void router.push({ path: '/shipment-exceptions', query: { status: 'open' } })
}
</script>

<template>
  <section class="panel todo-panel">
    <div class="todo-panel__head">
      <h2 class="todo-panel__title">待处理事项</h2>
      <NButton text size="tiny" type="primary" @click="openAll">查看全部</NButton>
    </div>

    <div v-if="error && available === false" class="todo-panel__error">
      <span>{{ error }}</span>
      <button type="button" @click="emit('retry')">重试</button>
    </div>

    <NTabs v-model:value="tab" type="segment" size="small" class="todo-tabs">
      <NTabPane name="all" tab="全部" />
      <NTabPane name="exception" tab="异常" />
      <NTabPane name="payment" tab="催款" />
      <NTabPane name="tracking_review" tab="审批" />
    </NTabs>

    <div v-if="loading && !items.length" class="todo-empty">加载中…</div>
    <div v-else-if="!filtered.length" class="todo-empty">暂无待处理事项</div>
    <ul v-else class="todo-list">
      <li v-for="item in filtered" :key="item.id">
        <button
          type="button"
          class="todo-row"
          :class="severityClass(item.severity)"
          @click="openItem(item)"
        >
          <div class="todo-row__main">
            <span class="todo-row__no">{{ item.shipmentNo || '—' }}</span>
            <span class="todo-row__title">{{ item.title }}</span>
          </div>
          <div class="todo-row__meta">
            <span v-if="item.customer">{{ item.customer }}</span>
            <span v-if="item.summary" class="todo-row__summary">{{ item.summary }}</span>
            <span v-if="item.overdueDays > 0">逾期 {{ item.overdueDays }} 天</span>
          </div>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.todo-panel {
  padding: 0.9rem 1rem 0.75rem;
  min-height: 16rem;
}

.todo-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.55rem;
}

.todo-panel__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
}

.todo-panel__error {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  color: #e11d48;
}

.todo-panel__error button {
  border: 0;
  background: transparent;
  color: var(--yz-primary, #2563eb);
  cursor: pointer;
}

.todo-tabs {
  margin-bottom: 0.55rem;
}

.todo-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.todo-row {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: color-mix(in srgb, var(--yz-bg, #f8fafc) 80%, transparent);
  padding: 0.55rem 0.65rem;
  text-align: left;
  cursor: pointer;
}

.todo-row:hover {
  border-color: var(--yz-border, #e5e7eb);
  background: #fff;
}

.todo-row--severe {
  border-left: 3px solid #e11d48;
}

.todo-row--high {
  border-left: 3px solid #d97706;
}

.todo-row__main {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: baseline;
}

.todo-row__no {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--yz-text, #111827);
}

.todo-row__title {
  font-size: 0.82rem;
  color: var(--yz-muted, #4b5563);
}

.todo-row__meta {
  margin-top: 0.2rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  font-size: 0.75rem;
  color: var(--yz-muted, #6b7280);
}

.todo-row__summary {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-empty {
  padding: 1.75rem 0.5rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--yz-muted, #9ca3af);
}
</style>
