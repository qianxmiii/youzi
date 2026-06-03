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
  return [`内部今日 ${s.internal.today}单`, `承运今日 ${s.carrier.today}单`].join(' · ')
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

function capsuleVariant(meta: CapsuleMeta): string {
  if (meta.danger) return 'none'
  if (meta.warn) return 'older'
  return meta.bucket
}

function badgeClass(
  _source: 'internal' | 'carrier',
  meta: CapsuleMeta,
): string {
  const count = countFor(_source, meta.bucket)
  const active = isActive(_source, meta.bucket)
  const base =
    'freshness-capsule group inline-flex min-w-[4.25rem] items-center justify-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all duration-150 ease-out select-none'
  const variant = capsuleVariant(meta)

  if (count === 0) {
    return `${base} freshness-capsule--disabled cursor-not-allowed`
  }

  const interactive =
    'cursor-pointer hover:-translate-y-px active:scale-[0.98] active:translate-y-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-border)]'

  return `${base} ${interactive} freshness-capsule--${variant}${active ? ' freshness-capsule--active' : ''}`
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
            <template v-if="activeFilterHint">已选 {{ activeFilterHint }}</template>
            <template v-else>{{ summaryLine }}</template>
          </span>
          <span v-else class="text-[11px] text-[var(--color-muted)]">点击胶囊筛选 · 自然日</span>
        </div>
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
        :aria-pressed="carrierAheadActive"
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
              <span class="freshness-capsule__label">{{ cap.label }}</span>
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

<style scoped>
.freshness-capsule__label {
  opacity: 0.9;
}

.freshness-capsule--active .freshness-capsule__label {
  opacity: 1;
  color: inherit;
}

.freshness-capsule--disabled {
  border-color: var(--color-border);
  background: var(--color-btn-ghost-bg);
  color: var(--color-muted);
  opacity: 0.45;
}

/* —— 未选中：浅色模式 —— */
[data-theme='light'] .freshness-capsule--today:not(.freshness-capsule--active) {
  border-color: rgb(16 185 129 / 0.35);
  background: rgb(16 185 129 / 0.12);
  color: rgb(21 128 61);
}

[data-theme='light'] .freshness-capsule--within3d:not(.freshness-capsule--active) {
  border-color: rgb(59 130 246 / 0.35);
  background: rgb(59 130 246 / 0.12);
  color: rgb(29 78 216);
}

[data-theme='light'] .freshness-capsule--older:not(.freshness-capsule--active) {
  border-color: rgb(245 158 11 / 0.35);
  background: rgb(245 158 11 / 0.12);
  color: rgb(180 83 9);
}

[data-theme='light'] .freshness-capsule--none:not(.freshness-capsule--active) {
  border-color: rgb(239 68 68 / 0.3);
  background: rgb(239 68 68 / 0.1);
  color: rgb(220 38 38);
}

/* —— 选中：浅色模式 · 实心底 + 白字 —— */
[data-theme='light'] .freshness-capsule--today.freshness-capsule--active {
  border-color: rgb(16 185 129);
  background: rgb(16 185 129);
  color: #fff;
  box-shadow: 0 1px 2px rgb(16 185 129 / 0.35);
}

[data-theme='light'] .freshness-capsule--within3d.freshness-capsule--active {
  border-color: rgb(59 130 246);
  background: rgb(59 130 246);
  color: #fff;
  box-shadow: 0 1px 2px rgb(59 130 246 / 0.35);
}

[data-theme='light'] .freshness-capsule--older.freshness-capsule--active {
  border-color: rgb(245 158 11);
  background: rgb(245 158 11);
  color: #fff;
  box-shadow: 0 1px 2px rgb(245 158 11 / 0.35);
}

[data-theme='light'] .freshness-capsule--none.freshness-capsule--active {
  border-color: rgb(239 68 68);
  background: rgb(239 68 68);
  color: #fff;
  box-shadow: 0 1px 2px rgb(239 68 68 / 0.35);
}

[data-theme='light'] .freshness-capsule--active:hover:not(:disabled) {
  filter: brightness(0.94);
  color: #fff;
}

/* —— 未选中：深色模式 —— */
[data-theme='dark'] .freshness-capsule--today:not(.freshness-capsule--active) {
  border-color: rgb(52 211 153 / 0.35);
  background: rgb(16 185 129 / 0.15);
  color: rgb(110 231 183);
}

[data-theme='dark'] .freshness-capsule--within3d:not(.freshness-capsule--active) {
  border-color: rgb(96 165 250 / 0.35);
  background: rgb(59 130 246 / 0.15);
  color: rgb(147 197 253);
}

[data-theme='dark'] .freshness-capsule--older:not(.freshness-capsule--active) {
  border-color: rgb(251 191 36 / 0.35);
  background: rgb(245 158 11 / 0.12);
  color: rgb(253 230 138);
}

[data-theme='dark'] .freshness-capsule--none:not(.freshness-capsule--active) {
  border-color: rgb(248 113 113 / 0.35);
  background: rgb(239 68 68 / 0.12);
  color: rgb(252 165 165);
}

/* —— 选中：深色模式 · 略提亮实心 + 白字 —— */
[data-theme='dark'] .freshness-capsule--today.freshness-capsule--active {
  border-color: rgb(52 211 153);
  background: rgb(5 150 105);
  color: #fff;
  box-shadow: 0 0 0 1px rgb(16 185 129 / 0.4);
}

[data-theme='dark'] .freshness-capsule--within3d.freshness-capsule--active {
  border-color: rgb(96 165 250);
  background: rgb(37 99 235);
  color: #fff;
  box-shadow: 0 0 0 1px rgb(59 130 246 / 0.4);
}

[data-theme='dark'] .freshness-capsule--older.freshness-capsule--active {
  border-color: rgb(251 191 36);
  background: rgb(217 119 6);
  color: #fff;
  box-shadow: 0 0 0 1px rgb(245 158 11 / 0.4);
}

[data-theme='dark'] .freshness-capsule--none.freshness-capsule--active {
  border-color: rgb(248 113 113);
  background: rgb(220 38 38);
  color: #fff;
  box-shadow: 0 0 0 1px rgb(239 68 68 / 0.4);
}

[data-theme='dark'] .freshness-capsule--active:hover:not(:disabled) {
  filter: brightness(1.08);
  color: #fff;
}

/* 未选中 hover */
[data-theme='light'] .freshness-capsule:not(.freshness-capsule--active):not(.freshness-capsule--disabled):hover {
  filter: brightness(0.97);
}

[data-theme='dark'] .freshness-capsule:not(.freshness-capsule--active):not(.freshness-capsule--disabled):hover {
  filter: brightness(1.12);
}
</style>
