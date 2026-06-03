<script setup lang="ts">
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
  { theme: string; spark: string; icon: 'calendar' | 'ship' | 'truck' | 'anchor' | 'depart' | 'check' }
> = {
  arriving_soon: { theme: 'indigo', spark: 'flat', icon: 'calendar' },
  departing_soon: { theme: 'indigo', spark: 'flat', icon: 'ship' },
  in_transit: { theme: 'blue', spark: 'up', icon: 'truck' },
  port_arriving: { theme: 'amber', spark: 'peak', icon: 'anchor' },
  port_departing: { theme: 'slate', spark: 'flat', icon: 'depart' },
  arrived: { theme: 'green', spark: 'up', icon: 'check' },
}
</script>

<template>
  <div class="stat-cards">
    <template v-if="loading">
      <div v-for="i in 6" :key="i" class="stat-card stat-card--skeleton" />
    </template>
    <button
      v-for="card in cards"
      v-else
      :key="card.key"
      type="button"
      class="stat-card"
      :class="'stat-card--' + (cardMeta[card.key]?.theme || 'indigo')"
      @click="emit('navigate', card.query)"
    >
      <div class="stat-card__head">
        <span class="stat-card__label">{{ card.label }}</span>
        <span class="stat-card__icon" aria-hidden="true">
          <svg v-if="cardMeta[card.key]?.icon === 'calendar'" viewBox="0 0 20 20" fill="none">
            <rect x="3.5" y="4.5" width="13" height="12" rx="1.5" stroke="currentColor" stroke-width="1.25" />
            <path d="M3.5 8h13M7 3v3M13 3v3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
          </svg>
          <svg v-else-if="cardMeta[card.key]?.icon === 'ship'" viewBox="0 0 20 20" fill="none">
            <path
              d="M3 14h14l-1.5-6H4.5L3 14ZM6 8V5h8v3"
              stroke="currentColor"
              stroke-width="1.25"
              stroke-linejoin="round"
            />
            <path d="M8 14v2M12 14v2" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" />
          </svg>
          <svg v-else-if="cardMeta[card.key]?.icon === 'truck'" viewBox="0 0 20 20" fill="none">
            <path
              d="M3 13h1.5l1.5-5h7l1.5 3H16v2h-1M6 13h7"
              stroke="currentColor"
              stroke-width="1.25"
              stroke-linejoin="round"
            />
            <circle cx="7" cy="14.5" r="1.25" stroke="currentColor" stroke-width="1.1" />
            <circle cx="14" cy="14.5" r="1.25" stroke="currentColor" stroke-width="1.1" />
          </svg>
          <svg v-else-if="cardMeta[card.key]?.icon === 'anchor'" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="6" r="2.25" stroke="currentColor" stroke-width="1.25" />
            <path
              d="M10 8v8M6 12c1.5 2 7.5 2 8 0M14 12c-1.5 2-7.5 2-8 0"
              stroke="currentColor"
              stroke-width="1.25"
              stroke-linecap="round"
            />
          </svg>
          <svg v-else-if="cardMeta[card.key]?.icon === 'depart'" viewBox="0 0 20 20" fill="none">
            <path
              d="M5 10h8M11 7l3 3-3 3M15 5v10"
              stroke="currentColor"
              stroke-width="1.25"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          <svg v-else viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="6.5" stroke="currentColor" stroke-width="1.25" />
            <path d="M7 10.2 9.2 12.5 13.5 8" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
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
    grid-template-columns: repeat(6, minmax(0, 1fr));
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
  outline: 2px solid rgb(139 92 246 / 0.5);
  outline-offset: 2px;
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

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
</style>
