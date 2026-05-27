<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { TrackingFreshnessBucket, TrackingFreshnessStats } from '@/utils/trackingFreshness'
import { FRESHNESS_LABEL } from '@/utils/trackingFreshness'

const props = defineProps<{
  stats: TrackingFreshnessStats | null
  internalActive: TrackingFreshnessBucket | null
  carrierActive: TrackingFreshnessBucket | null
  carrierAheadActive: boolean
  /** 已启用「承新于内」筛选时，用列表 total 与分页一致 */
  filteredCarrierAheadCount?: number | null
  carrierSyncHint?: string | null
}>()

const emit = defineEmits<{
  apply: [source: 'internal' | 'carrier', bucket: TrackingFreshnessBucket]
  clear: [source: 'internal' | 'carrier']
  toggleCarrierAhead: []
}>()

const expanded = ref(false)

type CapsuleMeta = {
  bucket: TrackingFreshnessBucket
  label: string
  hint: string
  warn?: boolean
  danger?: boolean
  icon?: string
}

const capsules: CapsuleMeta[] = [
  { bucket: 'today', label: FRESHNESS_LABEL.today, hint: '最新节点为今日' },
  { bucket: 'within3d', label: FRESHNESS_LABEL.within3d, hint: '三日内（含今日）' },
  {
    bucket: 'older',
    label: FRESHNESS_LABEL.older,
    hint: '最新节点早于三日内',
    warn: true,
    icon: '⏳',
  },
  {
    bucket: 'none',
    label: FRESHNESS_LABEL.none,
    hint: '无有效最新节点',
    danger: true,
    icon: '🚨',
  },
]

const rows = [
  { source: 'internal' as const, label: '内部轨迹', dotClass: 'bg-sky-400 shadow-[0_0_6px_rgba(56,189,248,0.45)]' },
  {
    source: 'carrier' as const,
    label: '承运商轨迹',
    dotClass: 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.4)]',
  },
]

/** 全库统计为运单数（非轨迹节点条数） */
const globalCarrierAheadCount = computed(
  () => props.stats?.carrierAheadOfInternal ?? 0,
)

const displayCarrierAheadCount = computed(() => {
  if (props.carrierAheadActive && props.filteredCarrierAheadCount != null) {
    return props.filteredCarrierAheadCount
  }
  return globalCarrierAheadCount.value
})

const carrierAheadTitle = computed(() => {
  if (props.carrierAheadActive) {
    return `当前列表 ${displayCarrierAheadCount.value} 单（承运最新时间晚于内部）；再点取消筛选`
  }
  return `全库 ${globalCarrierAheadCount.value} 单：承运最新时间晚于内部（按运单计，非轨迹节点数）；再点筛选`
})

const summaryLine = computed(() => {
  const s = props.stats
  if (!s) return '统计加载中…'
  return [
    `内部今日 ${s.internal.today}单`,
    `承运今日 ${s.carrier.today}单`,
    `承新于内 ${displayCarrierAheadCount.value}单`,
  ].join(' · ')
})

const activeFilterHint = computed(() => {
  const bits: string[] = []
  if (props.internalActive) bits.push(`内部·${FRESHNESS_LABEL[props.internalActive]}`)
  if (props.carrierActive) bits.push(`承运·${FRESHNESS_LABEL[props.carrierActive]}`)
  if (props.carrierAheadActive) bits.push('承新于内')
  return bits.length ? bits.join('、') : ''
})

const hasActiveFilter = computed(
  () =>
    Boolean(props.internalActive) ||
    Boolean(props.carrierActive) ||
    props.carrierAheadActive,
)

watch(hasActiveFilter, (on) => {
  if (on) expanded.value = true
})

function countFor(source: 'internal' | 'carrier', bucket: TrackingFreshnessBucket): number {
  if (!props.stats) return 0
  return props.stats[source][bucket]
}

function isActive(source: 'internal' | 'carrier', bucket: TrackingFreshnessBucket): boolean {
  return source === 'internal'
    ? props.internalActive === bucket
    : props.carrierActive === bucket
}

function onCapsule(source: 'internal' | 'carrier', bucket: TrackingFreshnessBucket) {
  if (countFor(source, bucket) === 0) return
  if (isActive(source, bucket)) emit('clear', source)
  else emit('apply', source, bucket)
}

function badgeClass(
  source: 'internal' | 'carrier',
  meta: CapsuleMeta,
): string {
  const count = countFor(source, meta.bucket)
  const active = isActive(source, meta.bucket)
  const base =
    'group inline-flex min-w-[4.25rem] items-center justify-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium tabular-nums transition-all duration-150 ease-out select-none'

  if (count === 0) {
    return `${base} cursor-not-allowed border-slate-800/80 bg-slate-900/30 text-zinc-600 opacity-40`
  }

  const interactive =
    'cursor-pointer hover:-translate-y-px active:scale-[0.98] active:translate-y-0 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-500/40'

  if (meta.danger) {
    if (active) {
      return `${base} ${interactive} border-red-400/35 bg-red-500/15 text-red-300 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ring-1 ring-red-500/25`
    }
    return `${base} ${interactive} border-red-500/20 bg-red-500/10 text-red-400 hover:border-red-500/35 hover:bg-red-500/15 hover:text-red-300`
  }

  if (meta.warn) {
    if (active) {
      return `${base} ${interactive} border-amber-400/35 bg-amber-500/15 text-amber-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] ring-1 ring-amber-500/25`
    }
    return `${base} ${interactive} border-amber-500/20 bg-amber-500/10 text-amber-400 hover:border-amber-500/35 hover:bg-amber-500/15 hover:text-amber-200`
  }

  if (active) {
    return source === 'internal'
      ? `${base} ${interactive} border-sky-500/30 bg-sky-500/12 text-sky-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] ring-1 ring-sky-500/25`
      : `${base} ${interactive} border-violet-500/25 bg-violet-500/10 text-violet-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] ring-1 ring-violet-500/20`
  }

  return `${base} ${interactive} border-slate-800 bg-slate-900/50 text-zinc-400 hover:border-zinc-700 hover:bg-slate-800/70 hover:text-zinc-200`
}

function toggleExpanded() {
  expanded.value = !expanded.value
}
</script>

<template>
  <div
    class="freshness-panel shrink-0 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)]"
  >
    <!-- 顶栏：摘要 / 展开 -->
    <div
      class="flex cursor-pointer items-start gap-2.5 px-3 py-2.5 transition-colors hover:bg-[var(--color-nav-hover)]"
      role="button"
      tabindex="0"
      :aria-expanded="expanded"
      @click="toggleExpanded"
      @keydown.enter.prevent="toggleExpanded"
      @keydown.space.prevent="toggleExpanded"
    >
      <svg
        class="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-muted)] transition-transform duration-200 ease-out"
        :class="expanded ? 'rotate-90' : ''"
        viewBox="0 0 16 16"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M6 4l4 4-4 4"
          stroke="currentColor"
          stroke-width="1.25"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>

      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
          <span class="text-xs font-semibold tracking-tight text-[var(--color-fg-emphasis)]">轨迹新鲜度</span>
          <span v-if="!expanded" class="text-[11px] leading-relaxed text-[var(--color-muted)]">
            {{ summaryLine }}
          </span>
          <span v-else class="text-[11px] text-[var(--color-muted)]">点击胶囊筛选 · 自然日</span>
        </div>
        <p v-if="activeFilterHint" class="mt-0.5 text-[11px] font-medium text-[var(--color-fg-secondary)]">
          已选 {{ activeFilterHint }}
        </p>
        <p
          v-if="carrierSyncHint && !expanded"
          class="mt-0.5 truncate text-[10px] text-[var(--color-muted)]"
          :title="carrierSyncHint"
        >
          {{ carrierSyncHint }}
        </p>
      </div>

      <button
        type="button"
        class="freshness-ahead-btn"
        :class="{
          'freshness-ahead-btn--active': carrierAheadActive,
          'freshness-ahead-btn--disabled': displayCarrierAheadCount === 0 && !carrierAheadActive,
        }"
        :disabled="displayCarrierAheadCount === 0 && !carrierAheadActive"
        :title="carrierAheadTitle"
        @click.stop="emit('toggleCarrierAhead')"
      >
        <span>承新于内</span>
        <span class="freshness-ahead-btn-num">{{ displayCarrierAheadCount }}</span>
        <span class="freshness-ahead-btn-unit">单</span>
      </button>

      <span class="shrink-0 pt-0.5 text-[10px] text-[var(--color-muted)]">
        {{ expanded ? '收起' : '展开' }}
      </span>
    </div>

    <!-- 胶囊组 -->
    <div
      v-show="expanded"
      class="border-t border-[var(--color-border-subtle)] px-3 pb-3 pt-2.5"
    >
      <div class="flex flex-col gap-2.5">
        <div
          v-for="row in rows"
          :key="row.source"
          class="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3"
        >
          <div
            class="flex w-full shrink-0 items-center gap-2 sm:w-[6.5rem]"
          >
            <span
              class="h-1.5 w-1.5 shrink-0 rounded-full"
              :class="row.dotClass"
              aria-hidden="true"
            />
            <span class="text-[11px] font-semibold tracking-tight text-[var(--color-fg-secondary)]">
              {{ row.label }}
            </span>
          </div>

          <div class="flex min-w-0 flex-1 flex-wrap gap-1.5">
            <button
              v-for="cap in capsules"
              :key="row.source + cap.bucket"
              type="button"
              :class="badgeClass(row.source, cap)"
              :title="`${row.label} · ${cap.label}`"
              :aria-pressed="isActive(row.source, cap.bucket)"
              :disabled="countFor(row.source, cap.bucket) === 0"
              @click.stop="onCapsule(row.source, cap.bucket)"
            >
              <span class="text-zinc-500 group-hover:text-inherit">{{ cap.label }}</span>
              <span class="font-semibold">{{ countFor(row.source, cap.bucket) }}</span>
              <span
                v-if="cap.icon && countFor(row.source, cap.bucket) > 0"
                class="text-[10px] leading-none opacity-90"
                aria-hidden="true"
              >{{ cap.icon }}</span>
            </button>
          </div>
        </div>
      </div>

      <p
        v-if="carrierSyncHint"
        class="mt-2.5 truncate text-[10px] text-[var(--color-muted)]"
        :title="carrierSyncHint"
      >
        {{ carrierSyncHint }}
      </p>
    </div>
  </div>
</template>
