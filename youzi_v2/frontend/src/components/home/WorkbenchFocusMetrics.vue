<script setup lang="ts">
import { AlertTriangle, BadgeCheck, Clock3, Ship } from 'lucide-vue-next'
import type { FunctionalComponent } from 'vue'
import type { LucideProps } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ICON_STROKE } from '@/constants/icons'
import type { WorkbenchFocusMetrics } from '@/api/workbench'

const props = defineProps<{
  focus: WorkbenchFocusMetrics | null
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

type FocusCard = {
  key: string
  label: string
  count: number
  theme: 'rose' | 'amber' | 'violet' | 'sky'
  icon: FunctionalComponent<LucideProps>
  to: { path: string; query?: Record<string, string> }
}

const cards = computed<FocusCard[]>(() => {
  const f = props.focus
  return [
    {
      key: 'exceptions',
      label: '待处理异常',
      count: f?.pendingExceptions ?? 0,
      theme: 'rose',
      icon: AlertTriangle,
      to: { path: '/shipment-exceptions', query: { status: 'open' } },
    },
    {
      key: 'collections',
      label: '待催收款项',
      count: f?.pendingCollections ?? 0,
      theme: 'amber',
      icon: BadgeCheck,
      to: { path: '/shipments/payment-reminders', query: { scope: 'todo' } },
    },
    {
      key: 'reviews',
      label: '轨迹审批',
      count: f?.pendingTrackingReviews ?? 0,
      theme: 'violet',
      icon: Clock3,
      to: { path: '/approvals/tracking-time', query: { status: 'pending_review' } },
    },
    {
      key: 'arriving',
      label: '三天内到港',
      count: f?.arrivingSoon ?? 0,
      theme: 'sky',
      icon: Ship,
      to: { path: '/vessel-schedules', query: { maritimeStatus: 'arriving_soon' } },
    },
  ]
})

function displayCount(n: number) {
  return n >= 100 ? '99+' : String(n)
}

function go(card: FocusCard) {
  void router.push(card.to)
}
</script>

<template>
  <section class="focus-section">
    <div class="focus-section__head">
      <h2 class="focus-section__title">今日重点</h2>
      <button
        v-if="error && !loading"
        type="button"
        class="focus-section__retry"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>
    <p v-if="error && !focus" class="focus-section__error">{{ error }}</p>
    <div class="focus-grid">
      <template v-if="loading && !focus">
        <div v-for="i in 4" :key="i" class="focus-card focus-card--skeleton" />
      </template>
      <button
        v-for="card in cards"
        v-else
        :key="card.key"
        type="button"
        class="focus-card"
        :class="[`focus-card--${card.theme}`, { 'focus-card--zero': card.count === 0 }]"
        :title="String(card.count)"
        :aria-label="`${card.label} ${card.count}，点击查看`"
        @click="go(card)"
      >
        <span class="focus-card__icon" aria-hidden="true">
          <component :is="card.icon" class="h-4 w-4" :stroke-width="ICON_STROKE" />
        </span>
        <span class="focus-card__label">{{ card.label }}</span>
        <span class="focus-card__value">{{ displayCount(card.count) }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.focus-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.65rem;
}

.focus-section__title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--yz-text, #1f2937);
}

.focus-section__retry {
  border: 0;
  background: transparent;
  color: var(--yz-primary, #2563eb);
  font-size: 0.8rem;
  cursor: pointer;
}

.focus-section__error {
  margin: 0 0 0.5rem;
  font-size: 0.8rem;
  color: #e11d48;
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

@media (min-width: 768px) {
  .focus-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.focus-card {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 0.55rem;
  row-gap: 0.15rem;
  align-items: center;
  padding: 0.85rem 0.95rem;
  border: 1px solid var(--yz-border, #e5e7eb);
  border-radius: 0.65rem;
  background: var(--yz-panel, #fff);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.focus-card:hover {
  border-color: color-mix(in srgb, var(--card-accent) 45%, var(--yz-border, #e5e7eb));
  box-shadow: 0 1px 0 color-mix(in srgb, var(--card-accent) 12%, transparent);
}

.focus-card--skeleton {
  min-height: 4.5rem;
  background: linear-gradient(90deg, #f3f4f6 25%, #eceff3 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: shimmer 1.2s infinite;
  border: 0;
  cursor: default;
}

.focus-card--rose {
  --card-accent: #e11d48;
}
.focus-card--amber {
  --card-accent: #d97706;
}
.focus-card--violet {
  --card-accent: #7c3aed;
}
.focus-card--sky {
  --card-accent: #0284c7;
}

.focus-card--zero {
  opacity: 0.78;
}

.focus-card__icon {
  grid-row: 1 / span 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 0.45rem;
  color: var(--card-accent);
  background: color-mix(in srgb, var(--card-accent) 12%, transparent);
}

.focus-card__label {
  font-size: 0.78rem;
  color: var(--yz-muted, #6b7280);
}

.focus-card__value {
  font-size: 1.45rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--card-accent);
  letter-spacing: -0.02em;
}

@keyframes shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
