<script setup lang="ts">
import {
  AlertTriangle,
  Banknote,
  ChevronRight,
  ClipboardList,
  Clock3,
} from 'lucide-vue-next'
import type { FunctionalComponent } from 'vue'
import type { LucideProps } from 'lucide-vue-next'
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

type TabKey = 'all' | WorkbenchTodoKind

const TAB_OPTIONS: { key: TabKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'exception', label: '异常' },
  { key: 'payment', label: '催款' },
  { key: 'tracking_review', label: '审批' },
]

const KIND_META: Record<
  WorkbenchTodoKind,
  { label: string; icon: FunctionalComponent<LucideProps>; tone: string }
> = {
  exception: { label: '异常', icon: AlertTriangle, tone: 'rose' },
  payment: { label: '催款', icon: Banknote, tone: 'amber' },
  tracking_review: { label: '审批', icon: Clock3, tone: 'violet' },
}

const filtered = computed(() => {
  if (tab.value === 'all') return props.items
  return props.items.filter((item) => item.kinds.includes(tab.value as WorkbenchTodoKind))
})

function tabCount(key: TabKey) {
  if (key === 'all') return props.items.length
  return props.items.filter((item) => item.kinds.includes(key)).length
}

function primaryKind(item: WorkbenchTodoItem): WorkbenchTodoKind {
  for (const k of item.kinds) {
    if (k in KIND_META) return k
  }
  return 'exception'
}

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
  <section class="panel todo-panel flex min-h-[16rem] flex-col p-4">
    <div class="todo-panel__head">
      <div class="min-w-0">
        <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">待处理事项</h2>
        <p class="page-subtitle mt-1">异常、催款与轨迹审批，按运单合并</p>
      </div>
      <button type="button" class="todo-panel__all" @click="openAll">
        查看全部
        <ChevronRight class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" aria-hidden="true" />
      </button>
    </div>

    <div
      v-if="error && available === false"
      class="mb-2 flex items-center justify-between gap-2 text-xs text-red-500"
    >
      <span>{{ error }}</span>
      <button type="button" class="todo-panel__all !text-[var(--color-accent-text)]" @click="emit('retry')">
        重试
      </button>
    </div>

    <div class="todo-tabs" role="tablist" aria-label="待办分类">
      <button
        v-for="opt in TAB_OPTIONS"
        :key="opt.key"
        type="button"
        role="tab"
        class="todo-tabs__btn"
        :class="{ 'todo-tabs__btn--active': tab === opt.key }"
        :aria-selected="tab === opt.key"
        @click="tab = opt.key"
      >
        {{ opt.label }}
        <span class="todo-tabs__count">{{ tabCount(opt.key) }}</span>
      </button>
    </div>

    <div class="todo-list-wrap scrollbar-subtle">
      <div v-if="loading && !items.length" class="todo-empty">
        <span class="todo-empty__icon wb-shimmer inline-block h-10 w-10 rounded-full" />
        <span>加载中…</span>
      </div>
      <div v-else-if="!filtered.length" class="todo-empty">
        <span class="todo-empty__icon" aria-hidden="true">
          <ClipboardList class="h-9 w-9" :stroke-width="1.25" />
        </span>
        <span>暂无待处理事项</span>
      </div>
      <ul v-else class="todo-list">
        <li v-for="item in filtered" :key="item.id">
          <button
            type="button"
            class="todo-row"
            :class="[
              severityClass(item.severity),
              `todo-row--${KIND_META[primaryKind(item)].tone}`,
            ]"
            @click="openItem(item)"
          >
            <span class="todo-row__bar" aria-hidden="true" />
            <span
              class="todo-row__icon"
              :class="`todo-row__icon--${KIND_META[primaryKind(item)].tone}`"
              aria-hidden="true"
            >
              <component
                :is="KIND_META[primaryKind(item)].icon"
                class="h-[1.05rem] w-[1.05rem]"
                :stroke-width="ICON_STROKE"
              />
            </span>
            <span class="todo-row__body">
              <span class="todo-row__top">
                <span class="todo-row__no">{{ item.shipmentNo || '—' }}</span>
                <span
                  v-for="kind in item.kinds"
                  :key="kind"
                  class="todo-row__tag"
                  :class="`todo-row__tag--${KIND_META[kind].tone}`"
                >
                  {{ KIND_META[kind].label }}
                </span>
              </span>
              <span class="todo-row__title">{{ item.title }}</span>
              <span class="todo-row__meta">
                <span v-if="item.customer" class="todo-row__customer">{{ item.customer }}</span>
                <span v-if="item.summary" class="todo-row__summary">{{ item.summary }}</span>
                <span v-if="item.overdueDays > 0" class="todo-row__overdue">
                  逾期 {{ item.overdueDays }} 天
                </span>
              </span>
            </span>
            <ChevronRight
              class="todo-row__chevron h-4 w-4 shrink-0"
              :stroke-width="ICON_STROKE"
              aria-hidden="true"
            />
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.todo-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.todo-panel__all {
  display: inline-flex;
  shrink: 0;
  align-items: center;
  gap: 0.1rem;
  padding: 0;
  border: none;
  background: transparent;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-accent-text);
  cursor: pointer;
  white-space: nowrap;
}

.todo-panel__all:hover {
  text-decoration: underline;
}

.todo-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.65rem;
  padding: 0.2rem;
  border-radius: 0.6rem;
  background: color-mix(in srgb, var(--color-border-subtle) 45%, var(--color-btn-ghost-bg));
  border: 1px solid var(--color-border);
}

.todo-tabs__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.65rem;
  border: 1px solid transparent;
  border-radius: 0.45rem;
  background: transparent;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--color-muted);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
}

.todo-tabs__btn:hover {
  color: var(--color-fg-secondary);
  background: var(--color-elevated);
}

.todo-tabs__btn--active {
  color: var(--color-fg-emphasis);
  background: var(--color-elevated);
  border-color: var(--color-border);
  box-shadow: 0 1px 2px color-mix(in srgb, var(--color-border) 60%, transparent);
}

.todo-tabs__count {
  min-width: 1.15rem;
  padding: 0 0.3rem;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: center;
  color: var(--color-fg-secondary);
  background: color-mix(in srgb, var(--color-border) 40%, transparent);
}

.todo-tabs__btn--active .todo-tabs__count {
  color: var(--color-accent-text);
  background: color-mix(in srgb, var(--color-accent-text) 12%, transparent);
}

.todo-list-wrap {
  flex: 1;
  min-height: 0;
  max-height: 22rem;
  overflow-y: auto;
}

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.todo-row {
  --todo-accent: var(--color-muted);
  position: relative;
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 0.7rem 0.65rem 0.55rem;
  border: 1px solid var(--color-border);
  border-radius: 0.65rem;
  background: var(--color-elevated);
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 1px 0 color-mix(in srgb, var(--color-border) 35%, transparent);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.12s ease;
}

.todo-row:hover {
  border-color: color-mix(in srgb, var(--todo-accent) 35%, var(--color-border));
  box-shadow: 0 3px 10px color-mix(in srgb, var(--todo-accent) 8%, transparent);
}

.todo-row:active {
  transform: scale(0.995);
}

.todo-row:focus-visible {
  outline: 2px solid var(--todo-accent);
  outline-offset: 2px;
}

.todo-row__bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--todo-accent);
  opacity: 0.85;
}

.todo-row--rose {
  --todo-accent: #e11d48;
}
.todo-row--amber {
  --todo-accent: #d97706;
}
.todo-row--violet {
  --todo-accent: #7c3aed;
}

.todo-row--severe .todo-row__bar {
  width: 4px;
}

.todo-row--high .todo-row__bar {
  opacity: 1;
}

.todo-row__icon {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 2.1rem;
  height: 2.1rem;
  margin-left: 0.2rem;
  border-radius: 0.5rem;
}

.todo-row__icon--rose {
  color: #e11d48;
  background: color-mix(in srgb, #e11d48 14%, transparent);
}
.todo-row__icon--amber {
  color: #d97706;
  background: color-mix(in srgb, #d97706 14%, transparent);
}
.todo-row__icon--violet {
  color: #7c3aed;
  background: color-mix(in srgb, #7c3aed 14%, transparent);
}

.todo-row__body {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.todo-row__top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}

.todo-row__no {
  font-size: 0.82rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--color-fg-emphasis);
}

.todo-row__tag {
  font-size: 0.62rem;
  font-weight: 600;
  line-height: 1.2;
  padding: 0.1rem 0.38rem;
  border-radius: 999px;
  border: 1px solid transparent;
}

.todo-row__tag--rose {
  color: #e11d48;
  background: color-mix(in srgb, #e11d48 10%, transparent);
  border-color: color-mix(in srgb, #e11d48 22%, var(--color-border));
}
.todo-row__tag--amber {
  color: #d97706;
  background: color-mix(in srgb, #d97706 10%, transparent);
  border-color: color-mix(in srgb, #d97706 22%, var(--color-border));
}
.todo-row__tag--violet {
  color: #7c3aed;
  background: color-mix(in srgb, #7c3aed 10%, transparent);
  border-color: color-mix(in srgb, #7c3aed 22%, var(--color-border));
}

.todo-row__title {
  font-size: 0.78rem;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-fg-secondary);
}

.todo-row__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.5rem;
  font-size: 0.68rem;
  line-height: 1.35;
  color: var(--color-muted);
}

.todo-row__summary {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.todo-row__overdue {
  font-weight: 600;
  color: #d97706;
}

.todo-row__chevron {
  color: var(--color-muted);
  transition:
    color 0.15s ease,
    transform 0.15s ease;
}

.todo-row:hover .todo-row__chevron {
  color: var(--todo-accent);
  transform: translateX(2px);
}

.todo-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  padding: 2.25rem 0.75rem;
  font-size: 0.85rem;
  color: var(--color-muted);
}

.todo-empty__icon {
  color: color-mix(in srgb, var(--color-muted) 55%, transparent);
}

.wb-shimmer {
  background: linear-gradient(
    90deg,
    var(--color-btn-ghost-bg) 25%,
    var(--color-border-subtle) 50%,
    var(--color-btn-ghost-bg) 75%
  );
  background-size: 200% 100%;
  animation: todo-shimmer 1.2s infinite;
}

@keyframes todo-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .todo-row,
  .todo-row__chevron,
  .todo-row:active {
    transition: none;
    transform: none;
  }
  .wb-shimmer {
    animation: none;
  }
}
</style>
