<script setup lang="ts">
import { AlertTriangle, Banknote, Clock3, Ship } from 'lucide-vue-next'
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
  const items: FocusCard[] = [
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
      icon: Banknote,
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
  return items
})

function displayCount(n: number) {
  return n >= 100 ? '99+' : String(n)
}

function go(card: FocusCard) {
  void router.push(card.to)
}
</script>

<template>
  <section class="panel px-4 py-3.5">
    <div class="mb-2.5 flex items-center justify-between gap-2">
      <div>
        <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">今日重点</h2>
        <p class="page-subtitle mt-1 hidden sm:block">待办审批、催款与到港预警</p>
      </div>
      <button
        v-if="error && !loading"
        type="button"
        class="cursor-pointer border-0 bg-transparent text-xs text-[var(--color-accent-text)] hover:underline"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>
    <p v-if="error && !focus" class="mb-2 text-xs text-red-500">{{ error }}</p>
    <div class="grid grid-cols-2 gap-2.5 md:grid-cols-4">
      <template v-if="loading && !focus">
        <div
          v-for="i in 4"
          :key="i"
          class="focus-skel h-[4.75rem] rounded-xl border border-[var(--color-border)]"
        />
      </template>
      <button
        v-for="card in cards"
        v-else
        :key="card.key"
        type="button"
        class="focus-card group"
        :class="[`focus-card--${card.theme}`, { 'focus-card--zero': card.count === 0 }]"
        :title="String(card.count)"
        :aria-label="`${card.label} ${card.count}，点击查看`"
        @click="go(card)"
      >
        <span class="focus-card__icon" aria-hidden="true">
          <component :is="card.icon" class="h-4 w-4" :stroke-width="ICON_STROKE" />
        </span>
        <span class="focus-card__body">
          <span class="focus-card__label">{{ card.label }}</span>
          <span class="focus-card__value">{{ displayCount(card.count) }}</span>
        </span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.focus-card {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  min-height: 4.75rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  background: var(--color-elevated);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    transform 0.15s ease;
}

.focus-card:hover {
  border-color: color-mix(in srgb, var(--card-accent) 40%, var(--color-border));
  background: color-mix(in srgb, var(--card-accent) 6%, var(--color-elevated));
}

.focus-card:focus-visible {
  outline: 2px solid var(--card-accent);
  outline-offset: 2px;
}

.focus-card:active {
  transform: scale(0.985);
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
  opacity: 0.72;
}

.focus-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.15rem;
  height: 2.15rem;
  flex-shrink: 0;
  border-radius: 0.55rem;
  color: var(--card-accent);
  background: color-mix(in srgb, var(--card-accent) 14%, transparent);
  transition: transform 0.15s ease;
}

.focus-card:hover .focus-card__icon {
  transform: translateY(-1px);
}

.focus-card__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.15rem;
}

.focus-card__label {
  font-size: 0.78rem;
  line-height: 1.2;
  color: var(--color-muted);
}

.focus-card__value {
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  color: var(--card-accent);
}

.focus-skel {
  background: linear-gradient(
    90deg,
    var(--color-btn-ghost-bg) 25%,
    var(--color-border-subtle) 50%,
    var(--color-btn-ghost-bg) 75%
  );
  background-size: 200% 100%;
  animation: wb-shimmer 1.2s infinite;
}

@keyframes wb-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .focus-card,
  .focus-card__icon {
    transition: none;
  }
  .focus-card:active {
    transform: none;
  }
  .focus-skel {
    animation: none;
  }
}
</style>
