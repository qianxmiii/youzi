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
  const day = now.getDay() // 0 Sun
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
  <section class="overview-section">
    <div class="overview-section__head">
      <h2 class="overview-section__title">运输概览</h2>
      <button
        v-if="error && !loading"
        type="button"
        class="overview-section__retry"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>
    <p v-if="error && !overview" class="overview-section__error">{{ error }}</p>
    <div class="overview-row">
      <template v-if="loading && !overview">
        <div v-for="i in 4" :key="i" class="overview-item overview-item--skeleton" />
      </template>
      <button
        v-for="card in cards"
        v-else
        :key="card.key"
        type="button"
        class="overview-item"
        @click="go(card.to)"
      >
        <span class="overview-item__label">{{ card.label }}</span>
        <span class="overview-item__value">{{ card.count }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.overview-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.55rem;
}

.overview-section__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--yz-muted, #4b5563);
}

.overview-section__retry {
  border: 0;
  background: transparent;
  color: var(--yz-primary, #2563eb);
  font-size: 0.8rem;
  cursor: pointer;
}

.overview-section__error {
  margin: 0 0 0.45rem;
  font-size: 0.8rem;
  color: #e11d48;
}

.overview-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

@media (min-width: 768px) {
  .overview-row {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.overview-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--yz-border, #e5e7eb);
  border-radius: 0.5rem;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.overview-item:hover {
  background: #fff;
}

.overview-item--skeleton {
  min-height: 2.6rem;
  background: #f3f4f6;
  border: 0;
  cursor: default;
}

.overview-item__label {
  font-size: 0.8rem;
  color: var(--yz-muted, #6b7280);
}

.overview-item__value {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--yz-text, #374151);
}
</style>
