<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { WorkbenchRouteStatusModule } from '@/api/workbench'
import { ROUTE_STATUS_BADGE_TONE } from '@/constants/shipmentRouteStatus'

const props = defineProps<{
  module: WorkbenchRouteStatusModule | null
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

type Tone =
  | 'sky'
  | 'teal'
  | 'indigo'
  | 'violet'
  | 'cyan'
  | 'orange'
  | 'success'
  | 'error'
  | 'rose'
  | 'slate'
  | 'default'

type Chip = {
  key: string
  label: string
  count: number
  href: string
  tone: Tone
  emphasis: boolean
}

function toneOf(code: string | null | undefined): Tone {
  const key = (code || '').trim().toUpperCase()
  return (ROUTE_STATUS_BADGE_TONE[key] as Tone) || 'default'
}

const allChips = computed<Chip[]>(() => {
  const items = props.module?.items ?? []
  const exceptions = items
    .filter((item) => item.isException)
    .map((item) => ({
      key: item.code,
      label: item.nameZh,
      count: item.count,
      href: item.href,
      tone: toneOf(item.code),
      emphasis: true,
    }))
  const pipeline = items
    .filter((item) => !item.isException)
    .map((item) => ({
      key: item.code,
      label: item.nameZh,
      count: item.count,
      href: item.href,
      tone: toneOf(item.code),
      emphasis: false,
    }))
  const m = props.module
  const missing: Chip[] = m
    ? [
        {
          key: 'missing',
          label: '无明细状态',
          count: m.missingCount,
          href: m.missingHref,
          tone: 'slate',
          emphasis: false,
        },
      ]
    : []
  return [...exceptions, ...pipeline, ...missing]
})

const TODAY_ROUTE_CODE: Record<string, string> = {
  TODAY_DEPARTED: 'DEPARTED_POL',
  TODAY_ARRIVED: 'ARRIVED_POD',
  TODAY_INTERNAL_DELIVERED: 'TRACK_SIGNED',
  TODAY_DEST_TRANSIT: 'DEST_TRANSIT_WAREHOUSE',
  TODAY_LAST_MILE: 'LAST_MILE_HANDOVER',
  TODAY_ROUTE_SIGNED: 'TRACK_SIGNED',
}

const todayChips = computed<Chip[]>(() => {
  const items = props.module?.todayItems ?? []
  return items.map((item) => ({
    key: item.code,
    label: item.nameZh,
    count: item.count,
    href: item.href,
    tone: item.isException ? 'error' : toneOf(TODAY_ROUTE_CODE[item.code] || ''),
    emphasis: item.isException,
  }))
})

function go(href: string) {
  if (!href) return
  void router.push(href)
}

function goAll() {
  const href = props.module?.viewAllHref || '/shipments?notDelivered=true&routeStatus=_ALL'
  void router.push(href)
}
</script>

<template>
  <section>
    <div class="mb-2.5 flex items-center justify-between gap-2">
      <h2 class="section-h2">
        明细状态
        <span v-if="module && !loading" class="rs-sub">未签收 {{ module.unsignedTotal }}</span>
      </h2>
      <div class="flex items-center gap-3">
        <button
          v-if="error && !loading"
          type="button"
          class="cursor-pointer border-0 bg-transparent text-xs text-[var(--color-accent-text)] hover:underline"
          @click="emit('retry')"
        >
          重试
        </button>
        <button
          type="button"
          class="cursor-pointer border-0 bg-transparent text-xs text-[var(--color-accent-text)] hover:underline"
          @click="goAll"
        >
          查看全部
        </button>
      </div>
    </div>
    <p v-if="error && !module" class="mb-2 text-xs text-red-500">{{ error }}</p>

    <div v-if="loading && !module" class="rs-grid">
      <div v-for="i in 10" :key="i" class="rs-skel" />
    </div>

    <div v-else class="rs-stack">
      <div class="rs-grid">
        <button
          v-for="chip in allChips"
          :key="chip.key"
          type="button"
          class="rs-tile"
          :class="[
            `rs-tile--${chip.tone}`,
            {
              'rs-tile--emphasis': chip.emphasis,
              'rs-tile--zero': chip.count === 0,
            },
          ]"
          :title="`${chip.label} ${chip.count}`"
          :aria-label="`${chip.label} ${chip.count}，点击查看运单`"
          @click="go(chip.href)"
        >
          <span class="rs-tile__bar" aria-hidden="true" />
          <span class="rs-tile__label">{{ chip.label }}</span>
          <span class="rs-tile__count">{{ chip.count }}</span>
        </button>
      </div>

      <div v-if="todayChips.length" class="rs-today-block">
        <p class="rs-today-heading">今日动态</p>
        <div class="rs-grid rs-grid--today">
          <button
            v-for="chip in todayChips"
            :key="chip.key"
            type="button"
            class="rs-tile rs-tile--today"
            :class="[
              `rs-tile--${chip.tone}`,
              {
                'rs-tile--emphasis': chip.emphasis,
                'rs-tile--zero': chip.count === 0,
              },
            ]"
            :title="`${chip.label} ${chip.count}（按本地自然日）`"
            :aria-label="`${chip.label} ${chip.count}，点击查看运单`"
            @click="go(chip.href)"
          >
            <span class="rs-tile__bar" aria-hidden="true" />
            <span class="rs-tile__label">{{ chip.label }}</span>
            <span class="rs-tile__count">{{ chip.count }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.rs-sub {
  margin-left: 0.45rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-muted);
}

.rs-stack {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.rs-today-block {
  padding-top: 0.15rem;
}

.rs-today-heading {
  margin: 0 0 0.4rem;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--color-muted);
}

.rs-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

@media (min-width: 640px) {
  .rs-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (min-width: 1100px) {
  .rs-grid {
    grid-template-columns: repeat(10, minmax(0, 1fr));
  }
}

.rs-grid--today {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (min-width: 640px) {
  .rs-grid--today {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1100px) {
  .rs-grid--today {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }
}

.rs-tile {
  --tile-accent: var(--color-muted);
  position: relative;
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
  align-items: flex-start;
  padding: 0.65rem 0.7rem 0.55rem;
  border: 1px solid var(--color-border);
  border-radius: 0.65rem;
  background: var(--color-elevated);
  text-align: left;
  cursor: pointer;
  overflow: hidden;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    transform 0.12s ease;
}

.rs-tile:hover {
  border-color: color-mix(in srgb, var(--tile-accent) 45%, var(--color-border));
  background: color-mix(in srgb, var(--tile-accent) 8%, var(--color-elevated));
}

.rs-tile:focus-visible {
  outline: 2px solid var(--tile-accent);
  outline-offset: 2px;
}

.rs-tile:active {
  transform: scale(0.985);
}

.rs-tile__bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--tile-accent);
  opacity: 0.9;
}

.rs-tile__label {
  max-width: 100%;
  margin-top: 0.15rem;
  font-size: 0.72rem;
  line-height: 1.25;
  color: var(--color-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rs-tile__count {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  color: var(--tile-accent);
}

.rs-tile--zero {
  opacity: 0.55;
}

.rs-tile--zero .rs-tile__count {
  color: var(--color-fg-secondary);
}

.rs-tile--emphasis {
  background: color-mix(in srgb, var(--tile-accent) 10%, var(--color-elevated));
  border-color: color-mix(in srgb, var(--tile-accent) 40%, var(--color-border));
}

.rs-tile--sky {
  --tile-accent: var(--tag-sky-fg);
}
.rs-tile--teal {
  --tile-accent: var(--tag-teal-fg);
}
.rs-tile--indigo {
  --tile-accent: var(--tag-indigo-fg);
}
.rs-tile--violet {
  --tile-accent: var(--tag-violet-fg);
}
.rs-tile--cyan {
  --tile-accent: var(--tag-cyan-fg);
}
.rs-tile--orange {
  --tile-accent: var(--tag-orange-fg);
}
.rs-tile--success {
  --tile-accent: var(--tag-success-fg);
}
.rs-tile--error {
  --tile-accent: var(--tag-error-fg);
}
.rs-tile--rose {
  --tile-accent: var(--tag-rose-fg);
}
.rs-tile--slate {
  --tile-accent: var(--tag-slate-fg);
}
.rs-tile--default {
  --tile-accent: var(--tag-default-fg);
}

.rs-skel {
  height: 3.6rem;
  border-radius: 0.65rem;
  border: 1px solid var(--color-border);
  background: linear-gradient(
    90deg,
    var(--color-btn-ghost-bg) 25%,
    var(--color-border-subtle) 50%,
    var(--color-btn-ghost-bg) 75%
  );
  background-size: 200% 100%;
  animation: rs-shimmer 1.2s infinite;
}

@keyframes rs-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rs-tile,
  .rs-tile:active {
    transition: none;
    transform: none;
  }
  .rs-skel {
    animation: none;
  }
}
</style>
