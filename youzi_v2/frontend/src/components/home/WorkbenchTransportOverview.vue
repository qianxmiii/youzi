<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { WorkbenchTransportOverview } from '@/api/workbench'
import { formatDateEndOfDayForApi, formatDateOnlyForApi } from '@/utils/formatDateTime'

const props = defineProps<{
  overview: WorkbenchTransportOverview | null
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

function weekBounds() {
  const now = new Date()
  const day = now.getDay()
  const mondayOffset = day === 0 ? -6 : 1 - day
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() + mondayOffset)
  const sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6)
  return {
    from: formatDateOnlyForApi(monday.getTime()),
    to: formatDateEndOfDayForApi(sunday.getTime()),
  }
}

const cards = computed(() => {
  const o = props.overview
  const week = weekBounds()
  return [
    {
      key: 'inTransit',
      label: '在途',
      count: o?.inTransit ?? 0,
      to: { path: '/shipments', query: { statusCode: 'IN_TRANSIT' } },
    },
    {
      key: 'inspection',
      label: '查验中',
      count: o?.inspection ?? 0,
      to: { path: '/shipments', query: { exceptionCode: 'INSPECTION' } },
    },
    {
      key: 'arrivedUnsigned',
      label: '已到港未签收',
      count: o?.arrivedUnsigned ?? 0,
      to: { path: '/shipments', query: { hasAta: 'true', notDelivered: 'true' } },
    },
    {
      key: 'deliveredThisWeek',
      label: '本周签收',
      count: o?.deliveredThisWeek ?? 0,
      to: {
        path: '/shipments',
        query: { deliveredFrom: week.from, deliveredTo: week.to },
      },
    },
  ]
})

function go(to: { path: string; query?: Record<string, string> }) {
  void router.push(to)
}
</script>

<template>
  <section>
    <div class="mb-2.5 flex items-center justify-between gap-2">
      <h2 class="section-h2">运输概览</h2>
      <button
        v-if="error && !loading"
        type="button"
        class="cursor-pointer border-0 bg-transparent text-xs text-[var(--color-accent-text)] hover:underline"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>
    <p v-if="error && !overview" class="mb-2 text-xs text-red-500">{{ error }}</p>
    <div class="grid grid-cols-2 gap-2 md:grid-cols-4">
      <template v-if="loading && !overview">
        <div
          v-for="i in 4"
          :key="i"
          class="h-11 rounded-lg border border-[var(--color-border)] bg-[var(--color-btn-ghost-bg)]"
        />
      </template>
      <button
        v-for="card in cards"
        v-else
        :key="card.key"
        type="button"
        class="overview-item"
        @click="go(card.to)"
      >
        <span class="text-[0.8rem] text-[var(--color-muted)]">{{ card.label }}</span>
        <span class="overview-item__value">{{ card.count }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.overview-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.7rem 0.85rem;
  border: 1px solid var(--color-border);
  border-radius: 0.55rem;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.overview-item:hover {
  border-color: var(--color-border);
  background: var(--color-btn-ghost-bg);
}

.overview-item:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.overview-item__value {
  font-size: 1.05rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-secondary);
}

@media (prefers-reduced-motion: reduce) {
  .overview-item {
    transition: none;
  }
}
</style>
