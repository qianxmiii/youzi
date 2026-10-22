<script setup lang="ts">
import { Anchor, ChevronRight, Ship } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ICON_STROKE } from '@/constants/icons'
import type { WorkbenchArrivalDayGroup, WorkbenchArrivalItem } from '@/api/workbench'

const props = defineProps<{
  items: WorkbenchArrivalItem[]
  loading?: boolean
  error?: string | null
  available?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

const GROUP_LABEL: Record<WorkbenchArrivalDayGroup, string> = {
  past: '往前三天内',
  today: '今天',
  forward: '往后三天内',
}

const grouped = computed(() => {
  const order: WorkbenchArrivalDayGroup[] = ['past', 'today', 'forward']
  return order.map((key) => ({
    key,
    label: GROUP_LABEL[key],
    items: props.items.filter((item) => item.dayGroup === key),
  }))
})

const hasAnyItems = computed(() => props.items.length > 0)

function formatEta(eta: string | null) {
  const raw = (eta || '').trim()
  if (!raw) return '时间待定'
  const m = raw.match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
  if (m) {
    const [, , mm, dd, hh, min] = m
    if (hh === '00' && min === '00') return `${mm}-${dd}`
    return `${mm}-${dd} ${hh}:${min}`
  }
  return raw.slice(5, 16) || raw
}

function rowTitle(item: WorkbenchArrivalItem): string {
  const vessel = (item.vesselVoyage || '').trim()
  if (vessel && vessel !== '—') return vessel
  const port = (item.destinationPortCode || '').trim()
  if (port) return `${port} 到港批次`
  return `共 ${item.shipmentCount} 票`
}

function rowSubtitle(item: WorkbenchArrivalItem): string {
  const parts: string[] = []
  const vessel = (item.vesselVoyage || '').trim()
  const port = (item.destinationPortCode || '').trim() || '目的港待定'
  if (!vessel || vessel === '—') {
    parts.push(port)
  } else if (port) {
    parts.push(port)
  }
  parts.push(`ETA ${formatEta(item.eta)}`)
  parts.push(`${item.shipmentCount} 票`)
  return parts.join(' · ')
}

function openItem(item: WorkbenchArrivalItem) {
  if (item.href) {
    void router.push(item.href)
    return
  }
  void router.push({ path: '/vessel-schedules', query: { maritimeStatus: 'arriving_soon' } })
}

function openAll() {
  void router.push({
    path: '/shipments',
    query: { notDelivered: 'true' },
  })
}
</script>

<template>
  <section class="panel arrival-panel">
    <div class="arrival-panel__head">
      <div class="min-w-0">
        <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">近期到港</h2>
        <p class="page-subtitle mt-1">前后各三天 ETA、按船名/目的港聚合</p>
      </div>
      <button type="button" class="arrival-panel__all" @click="openAll">
        查看全部
        <ChevronRight class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" aria-hidden="true" />
      </button>
    </div>

    <div
      v-if="error && available === false"
      class="mb-2 flex items-center justify-between gap-2 text-xs text-red-500"
    >
      <span>{{ error }}</span>
      <button type="button" class="arrival-panel__all" @click="emit('retry')">重试</button>
    </div>

    <div v-if="loading && !items.length" class="arrival-empty">
      <span class="arrival-empty__icon wb-shimmer inline-block h-10 w-10 rounded-full" />
      <span>加载中…</span>
    </div>
    <div v-else-if="!hasAnyItems" class="arrival-empty">
      <Ship class="arrival-empty__icon h-9 w-9" :stroke-width="1.25" aria-hidden="true" />
      <span>前后三天暂无到港</span>
    </div>

    <div v-else class="arrival-columns">
      <div
        v-for="group in grouped"
        :key="group.key"
        class="arrival-group"
        :class="{ 'arrival-group--empty': !group.items.length }"
      >
        <div class="arrival-group__head">
          <span class="arrival-group__label">{{ group.label }}</span>
          <span class="arrival-group__count">{{ group.items.length }}</span>
        </div>

        <ul v-if="group.items.length" class="arrival-list">
          <li v-for="(item, idx) in group.items" :key="`${group.key}-${item.eta}-${idx}`">
            <button type="button" class="arrival-row" @click="openItem(item)">
              <span class="arrival-row__icon" aria-hidden="true">
                <Anchor class="h-[1.05rem] w-[1.05rem]" :stroke-width="ICON_STROKE" />
              </span>
              <span class="arrival-row__body">
                <span class="arrival-row__title">{{ rowTitle(item) }}</span>
                <span class="arrival-row__meta">
                  <span>{{ rowSubtitle(item) }}</span>
                  <span
                    v-if="item.isSubscribedPort"
                    class="arrival-row__badge"
                  >
                    订阅港
                  </span>
                </span>
              </span>
              <ChevronRight
                class="arrival-row__chevron h-4 w-4 shrink-0"
                :stroke-width="ICON_STROKE"
                aria-hidden="true"
              />
            </button>
          </li>
        </ul>
        <p v-else class="arrival-group__empty">暂无</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.arrival-panel {
  display: flex;
  flex-direction: column;
  padding: 1rem 1.05rem 1.1rem;
}

.arrival-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}

.arrival-panel__all {
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

.arrival-panel__all:hover {
  text-decoration: underline;
}

.arrival-columns {
  display: grid;
  gap: 0.65rem;
}

@media (min-width: 768px) {
  .arrival-columns {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    align-items: start;
  }
}

.arrival-group {
  display: flex;
  flex-direction: column;
  min-height: 5rem;
  padding: 0.65rem 0.7rem 0.75rem;
  border-radius: 0.65rem;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-border-subtle) 35%, var(--color-elevated));
}

.arrival-group--empty {
  opacity: 0.72;
}

.arrival-group__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.55rem;
  padding-bottom: 0.45rem;
  border-bottom: 1px solid color-mix(in srgb, var(--color-border) 70%, transparent);
}

.arrival-group__label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: var(--color-fg-secondary);
}

.arrival-group__count {
  min-width: 1.25rem;
  padding: 0.08rem 0.4rem;
  border-radius: 999px;
  font-size: 0.65rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: center;
  color: var(--color-accent-text);
  background: color-mix(in srgb, var(--color-accent-text) 10%, transparent);
}

.arrival-group__empty {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  color: var(--color-muted);
}

.arrival-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.arrival-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.55rem;
  padding: 0.55rem 0.5rem;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  background: var(--color-elevated);
  text-align: left;
  cursor: pointer;
  box-shadow: 0 1px 0 color-mix(in srgb, var(--color-border) 30%, transparent);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.arrival-row:hover {
  border-color: color-mix(in srgb, #0284c7 30%, var(--color-border));
  box-shadow: 0 2px 8px color-mix(in srgb, #0284c7 8%, transparent);
}

.arrival-row:focus-visible {
  outline: 2px solid #0284c7;
  outline-offset: 2px;
}

.arrival-row__icon {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
  color: #0284c7;
  background: color-mix(in srgb, #0284c7 14%, transparent);
}

.arrival-row__body {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.arrival-row__title {
  font-size: 0.82rem;
  font-weight: 600;
  line-height: 1.35;
  color: var(--color-fg-emphasis);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrival-row__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.68rem;
  line-height: 1.35;
  color: var(--color-muted);
}

.arrival-row__badge {
  font-size: 0.62rem;
  font-weight: 600;
  padding: 0.06rem 0.35rem;
  border-radius: 999px;
  color: #0284c7;
  background: color-mix(in srgb, #0284c7 12%, transparent);
  border: 1px solid color-mix(in srgb, #0284c7 22%, var(--color-border));
}

.arrival-row__chevron {
  color: var(--color-muted);
  transition:
    color 0.15s ease,
    transform 0.15s ease;
}

.arrival-row:hover .arrival-row__chevron {
  color: #0284c7;
  transform: translateX(2px);
}

.arrival-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  padding: 2.25rem 0.75rem;
  font-size: 0.85rem;
  color: var(--color-muted);
}

.arrival-empty__icon {
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
  animation: arrival-shimmer 1.2s infinite;
}

@keyframes arrival-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .arrival-row,
  .arrival-row__chevron,
  .wb-shimmer {
    transition: none;
    animation: none;
  }
}
</style>
