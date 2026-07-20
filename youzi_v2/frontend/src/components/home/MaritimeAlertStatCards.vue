<script setup lang="ts">
import type { FunctionalComponent } from 'vue'
import {
  Anchor,
  ArrowRight,
  Calendar,
  CheckCircle2,
  Search,
  Ship,
  Truck,
} from 'lucide-vue-next'
import type { LucideProps } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'

export interface MaritimeStatCard {
  key: string
  label: string
  count: number
  query: Record<string, string>
}

defineProps<{
  cards: MaritimeStatCard[]
  loading?: boolean
}>()

const emit = defineEmits<{
  navigate: [query: Record<string, string>]
}>()

function sparklinePoints(count: number, variant: string): string {
  if (count <= 0) return 'M2 14 L38 14'
  if (variant === 'peak') return 'M2 14 L12 14 L20 6 L28 14 L38 10'
  if (variant === 'up') return 'M2 16 L10 12 L22 8 L38 4'
  return 'M2 14 L38 10'
}

const cardMeta: Record<
  string,
  {
    theme: string
    spark: string
    icon: 'calendar' | 'ship' | 'truck' | 'anchor' | 'depart' | 'check' | 'search'
  }
> = {
  arriving_soon: { theme: 'indigo', spark: 'flat', icon: 'calendar' },
  departing_soon: { theme: 'indigo', spark: 'flat', icon: 'ship' },
  in_transit: { theme: 'blue', spark: 'up', icon: 'truck' },
  inspection: { theme: 'rose', spark: 'peak', icon: 'search' },
  port_arriving: { theme: 'amber', spark: 'peak', icon: 'anchor' },
  port_departing: { theme: 'slate', spark: 'flat', icon: 'depart' },
  arrived: { theme: 'green', spark: 'up', icon: 'check' },
}

const statIcons: Record<string, FunctionalComponent<LucideProps>> = {
  calendar: Calendar,
  ship: Ship,
  truck: Truck,
  anchor: Anchor,
  depart: ArrowRight,
  check: CheckCircle2,
  search: Search,
}
</script>

<template>
  <div class="stat-cards">
    <template v-if="loading">
      <div v-for="i in 7" :key="i" class="stat-card stat-card--skeleton" />
    </template>
    <button
      v-for="card in cards"
      v-else
      :key="card.key"
      type="button"
      class="stat-card"
      :class="[
        'stat-card--' + (cardMeta[card.key]?.theme || 'indigo'),
        { 'stat-card--zero': card.count === 0 },
      ]"
      :aria-label="`${card.label} ${card.count} 票，点击查看详情`"
      @click="emit('navigate', card.query)"
    >
      <div class="stat-card__head">
        <span class="stat-card__label">{{ card.label }}</span>
        <span class="stat-card__icon" aria-hidden="true">
          <component
            :is="statIcons[cardMeta[card.key]?.icon || 'check']"
            class="h-full w-full"
            :stroke-width="ICON_STROKE"
          />
        </span>
      </div>
      <div class="stat-card__foot">
        <span class="stat-card__value">{{ card.count }}</span>
        <svg
          class="stat-card__sparkline"
          viewBox="0 0 40 18"
          fill="none"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <path
            :d="sparklinePoints(card.count, cardMeta[card.key]?.spark || 'flat')"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    </button>
  </div>
</template>

<style scoped>
.stat-cards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

@media (min-width: 640px) {
  .stat-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .stat-cards {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .stat-cards {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }
}

.stat-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 5.5rem;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: var(--color-panel);
  padding: 0.875rem 1rem;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.15s ease;
}

.stat-card:hover:not(.stat-card--skeleton) {
  box-shadow:
    0 4px 6px rgb(24 24 27 / 0.04),
    0 10px 24px rgb(24 24 27 / 0.1);
  transform: translateY(-2px);
}

.stat-card:active:not(.stat-card--skeleton) {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgb(24 24 27 / 0.06);
}

.stat-card:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--color-accent) 50%, transparent);
  outline-offset: 2px;
}

.stat-card--zero {
  opacity: 0.72;
}

.stat-card--zero .stat-card__value {
  color: var(--color-muted);
}

.stat-card--zero .stat-card__icon,
.stat-card--zero .stat-card__sparkline {
  color: var(--color-muted);
}

.stat-card--zero:hover {
  opacity: 1;
}

[data-theme='dark'] .stat-card:hover:not(.stat-card--skeleton) {
  box-shadow:
    0 4px 8px rgb(0 0 0 / 0.2),
    0 12px 28px rgb(0 0 0 / 0.35);
}

.stat-card--skeleton {
  cursor: default;
  animation: pulse 1.5s ease-in-out infinite;
  background: var(--color-btn-ghost-bg);
  pointer-events: none;
}

.stat-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}

.stat-card__label {
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.3;
  color: var(--color-fg-secondary);
}

.stat-card__icon {
  display: inline-flex;
  flex-shrink: 0;
  width: 1.25rem;
  height: 1.25rem;
}

.stat-card__icon svg {
  width: 100%;
  height: 100%;
}

.stat-card__foot {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.stat-card__value {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.stat-card__sparkline {
  width: 2.75rem;
  height: 1.125rem;
  flex-shrink: 0;
  opacity: 0.85;
}

.stat-card--indigo .stat-card__icon,
.stat-card--indigo .stat-card__sparkline {
  color: rgb(99 102 241);
}

.stat-card--indigo .stat-card__value {
  color: rgb(67 56 202);
}

.stat-card--blue .stat-card__icon,
.stat-card--blue .stat-card__sparkline {
  color: rgb(59 130 246);
}

.stat-card--blue .stat-card__value {
  color: rgb(37 99 235);
}

.stat-card--amber .stat-card__icon,
.stat-card--amber .stat-card__sparkline {
  color: rgb(180 132 60);
}

.stat-card--amber .stat-card__value {
  color: rgb(161 98 7);
}

.stat-card--slate .stat-card__icon,
.stat-card--slate .stat-card__sparkline {
  color: rgb(100 116 139);
}

.stat-card--slate .stat-card__value {
  color: rgb(51 65 85);
}

.stat-card--green .stat-card__icon,
.stat-card--green .stat-card__sparkline {
  color: rgb(34 197 94);
}

.stat-card--green .stat-card__value {
  color: rgb(22 163 74);
}

.stat-card--rose .stat-card__icon,
.stat-card--rose .stat-card__sparkline {
  color: rgb(244 63 94);
}

.stat-card--rose .stat-card__value {
  color: rgb(225 29 72);
}

[data-theme='dark'] .stat-card--indigo .stat-card__value {
  color: rgb(165 180 252);
}

[data-theme='dark'] .stat-card--blue .stat-card__value {
  color: rgb(147 197 253);
}

[data-theme='dark'] .stat-card--amber .stat-card__value {
  color: rgb(253 230 138);
}

[data-theme='dark'] .stat-card--slate .stat-card__value {
  color: rgb(203 213 225);
}

[data-theme='dark'] .stat-card--green .stat-card__value {
  color: rgb(134 239 172);
}

[data-theme='dark'] .stat-card--rose .stat-card__value {
  color: rgb(253 164 175);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stat-card {
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .stat-card:hover:not(.stat-card--skeleton) {
    transform: none;
  }

  .stat-card--skeleton {
    animation: none;
    opacity: 0.65;
  }
}
</style>
