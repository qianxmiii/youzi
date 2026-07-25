<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'
import { NButton, NTabs, NTabPane } from 'naive-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ICON_STROKE } from '@/constants/icons'
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
  <section class="panel flex min-h-[16rem] flex-col p-4">
    <div class="mb-2.5 flex items-center justify-between gap-2">
      <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">待处理事项</h2>
      <NButton text size="tiny" type="primary" class="cursor-pointer" @click="openAll">
        查看全部
      </NButton>
    </div>

    <div
      v-if="error && available === false"
      class="mb-2 flex items-center justify-between gap-2 text-xs text-red-500"
    >
      <span>{{ error }}</span>
      <button
        type="button"
        class="cursor-pointer border-0 bg-transparent text-[var(--color-accent-text)] hover:underline"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>

    <NTabs v-model:value="tab" type="segment" size="small" class="mb-2.5">
      <NTabPane name="all" tab="全部" />
      <NTabPane name="exception" tab="异常" />
      <NTabPane name="payment" tab="催款" />
      <NTabPane name="tracking_review" tab="审批" />
    </NTabs>

    <div v-if="loading && !items.length" class="todo-empty">加载中…</div>
    <div v-else-if="!filtered.length" class="todo-empty">暂无待处理事项</div>
    <ul v-else class="flex flex-col gap-1">
      <li v-for="item in filtered" :key="item.id">
        <button
          type="button"
          class="todo-row"
          :class="severityClass(item.severity)"
          @click="openItem(item)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <span class="text-[0.85rem] font-semibold text-[var(--color-fg-emphasis)]">
                {{ item.shipmentNo || '—' }}
              </span>
              <span class="text-[0.8rem] text-[var(--color-fg-secondary)]">{{ item.title }}</span>
            </div>
            <div class="mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[0.72rem] text-[var(--color-muted)]">
              <span v-if="item.customer">{{ item.customer }}</span>
              <span v-if="item.summary" class="max-w-full truncate">{{ item.summary }}</span>
              <span v-if="item.overdueDays > 0" class="font-medium text-amber-600 dark:text-amber-400">
                逾期 {{ item.overdueDays }} 天
              </span>
            </div>
          </div>
          <ChevronRight
            class="todo-row__chevron h-4 w-4 shrink-0 text-[var(--color-muted)]"
            :stroke-width="ICON_STROKE"
            aria-hidden="true"
          />
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.todo-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  background: var(--color-btn-ghost-bg);
  padding: 0.55rem 0.65rem;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.todo-row:hover {
  border-color: var(--color-border);
  background: var(--color-btn-ghost-hover);
}

.todo-row:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.todo-row:hover .todo-row__chevron {
  color: var(--color-fg-secondary);
  transform: translateX(1px);
}

.todo-row__chevron {
  transition:
    color 0.15s ease,
    transform 0.15s ease;
}

.todo-row--severe {
  border-left: 3px solid #e11d48;
}

.todo-row--high {
  border-left: 3px solid #d97706;
}

.todo-empty {
  padding: 2rem 0.5rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-muted);
}

@media (prefers-reduced-motion: reduce) {
  .todo-row,
  .todo-row__chevron {
    transition: none;
  }
}
</style>
