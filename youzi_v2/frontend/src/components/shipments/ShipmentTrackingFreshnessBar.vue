<script setup lang="ts">
import { computed } from 'vue'
import type { TrackingFreshnessStats } from '@/utils/trackingFreshness'

const props = defineProps<{
  stats: TrackingFreshnessStats | null
  noInternalActive: boolean
  noCarrierActive: boolean
  carrierAheadActive: boolean
  pendingReviewActive: boolean
  stale7Active: boolean
  stale14Active: boolean
  filteredNoInternalCount?: number | null
  filteredNoCarrierCount?: number | null
  filteredPendingReviewCount?: number | null
  filteredCarrierAheadCount?: number | null
  filteredStale7Count?: number | null
  filteredStale14Count?: number | null
  carrierSyncHint?: string | null
}>()

const emit = defineEmits<{
  toggleNoInternal: []
  toggleNoCarrier: []
  toggleCarrierAhead: []
  togglePendingReview: []
  toggleStale7: []
  toggleStale14: []
}>()

type QuickFilter = {
  key: 'pendingReview' | 'carrierAhead' | 'stale7' | 'stale14' | 'noInternal' | 'noCarrier'
  label: string
  active: boolean
  count: number
  titleActive: string
  titleIdle: string
  tone?: 'pending' | 'stale7' | 'stale14'
}

const globalNoInternalCount = computed(() => props.stats?.internal.none ?? 0)
const globalNoCarrierCount = computed(() => props.stats?.carrier.none ?? 0)
const globalCarrierAheadCount = computed(() => props.stats?.carrierAheadOfInternal ?? 0)
const globalPendingReviewCount = computed(() => props.stats?.pendingTrackingTimeReview ?? 0)
const globalStale7Count = computed(() => props.stats?.internalStale7d ?? 0)
const globalStale14Count = computed(() => props.stats?.internalStale14d ?? 0)

function displayCount(
  active: boolean,
  filtered: number | null | undefined,
  global: number,
): number {
  if (active && filtered != null) return filtered
  return global
}

const quickFilters = computed((): QuickFilter[] => [
  {
    key: 'pendingReview',
    label: '待轨迹审批',
    active: props.pendingReviewActive,
    count: displayCount(
      props.pendingReviewActive,
      props.filteredPendingReviewCount,
      globalPendingReviewCount.value,
    ),
    titleActive: `当前列表 ${displayCount(props.pendingReviewActive, props.filteredPendingReviewCount, globalPendingReviewCount.value)} 单待轨迹审批；再点取消`,
    titleIdle: `全库 ${globalPendingReviewCount.value} 单签收时间待确认；再点筛选`,
    tone: 'pending',
  },
  {
    key: 'carrierAhead',
    label: '承新于内',
    active: props.carrierAheadActive,
    count: displayCount(
      props.carrierAheadActive,
      props.filteredCarrierAheadCount,
      globalCarrierAheadCount.value,
    ),
    titleActive: `当前列表 ${displayCount(props.carrierAheadActive, props.filteredCarrierAheadCount, globalCarrierAheadCount.value)} 单（承运最新时间晚于内部）；再点取消`,
    titleIdle: `全库 ${globalCarrierAheadCount.value} 单：承运最新时间晚于内部；再点筛选`,
  },
  {
    key: 'stale7',
    label: '≥7天未更新',
    active: props.stale7Active,
    count: displayCount(props.stale7Active, props.filteredStale7Count, globalStale7Count.value),
    titleActive: `当前列表 ${displayCount(props.stale7Active, props.filteredStale7Count, globalStale7Count.value)} 单转运中且内部轨迹 ≥7 天未更新；再点取消`,
    titleIdle: `全库 ${globalStale7Count.value} 单转运中且内部轨迹 ≥7 天未更新；再点筛选`,
    tone: 'stale7',
  },
  {
    key: 'stale14',
    label: '≥14天未更新',
    active: props.stale14Active,
    count: displayCount(props.stale14Active, props.filteredStale14Count, globalStale14Count.value),
    titleActive: `当前列表 ${displayCount(props.stale14Active, props.filteredStale14Count, globalStale14Count.value)} 单转运中且内部轨迹 ≥14 天未更新；再点取消`,
    titleIdle: `全库 ${globalStale14Count.value} 单转运中且内部轨迹 ≥14 天未更新；再点筛选`,
    tone: 'stale14',
  },
  {
    key: 'noInternal',
    label: '内部无轨迹',
    active: props.noInternalActive,
    count: displayCount(
      props.noInternalActive,
      props.filteredNoInternalCount,
      globalNoInternalCount.value,
    ),
    titleActive: `当前列表 ${displayCount(props.noInternalActive, props.filteredNoInternalCount, globalNoInternalCount.value)} 单无有效内部轨迹；再点取消`,
    titleIdle: `全库 ${globalNoInternalCount.value} 单无有效内部轨迹；再点筛选`,
  },
  {
    key: 'noCarrier',
    label: '承运商无轨迹',
    active: props.noCarrierActive,
    count: displayCount(
      props.noCarrierActive,
      props.filteredNoCarrierCount,
      globalNoCarrierCount.value,
    ),
    titleActive: `当前列表 ${displayCount(props.noCarrierActive, props.filteredNoCarrierCount, globalNoCarrierCount.value)} 单无承运商轨迹（不含整柜）；再点取消`,
    titleIdle: `全库 ${globalNoCarrierCount.value} 单无承运商轨迹（不含整柜）；再点筛选`,
  },
])

function onToggle(key: QuickFilter['key']) {
  if (key === 'pendingReview') emit('togglePendingReview')
  else if (key === 'carrierAhead') emit('toggleCarrierAhead')
  else if (key === 'stale7') emit('toggleStale7')
  else if (key === 'stale14') emit('toggleStale14')
  else if (key === 'noInternal') emit('toggleNoInternal')
  else emit('toggleNoCarrier')
}
</script>

<template>
  <div
    class="freshness-panel shrink-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2"
  >
    <div class="scrollbar-subtle flex min-w-0 items-center gap-2 overflow-x-auto whitespace-nowrap">
      <span class="shrink-0 text-xs font-semibold tracking-tight text-[var(--color-fg-emphasis)]">
        轨迹筛选
      </span>

      <button
        v-for="item in quickFilters"
        :key="item.key"
        type="button"
        class="freshness-ahead-btn shrink-0"
        :class="{
          'freshness-pending-btn': item.tone === 'pending',
          'freshness-stale7-btn': item.tone === 'stale7',
          'freshness-stale14-btn': item.tone === 'stale14',
          'freshness-ahead-btn--active': item.active,
          'freshness-ahead-btn--disabled': item.count === 0 && !item.active,
        }"
        :disabled="item.count === 0 && !item.active"
        :aria-pressed="item.active"
        :title="item.active ? item.titleActive : item.titleIdle"
        @click="onToggle(item.key)"
      >
        <span>{{ item.label }}</span>
        <span class="freshness-ahead-btn-num">{{ item.count }}</span>
        <span class="freshness-ahead-btn-unit">单</span>
      </button>

      <p
        v-if="carrierSyncHint"
        class="ml-auto min-w-0 shrink truncate pl-2 text-[10px] text-[var(--color-muted)]"
        :title="carrierSyncHint"
      >
        {{ carrierSyncHint }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.freshness-pending-btn:not(.freshness-ahead-btn--active):not(.freshness-ahead-btn--disabled) {
  border-color: rgb(251 191 36 / 0.45);
  color: rgb(180 83 9);
}

[data-theme='dark'] .freshness-pending-btn:not(.freshness-ahead-btn--active):not(.freshness-ahead-btn--disabled) {
  border-color: rgb(245 158 11 / 0.35);
  color: rgb(253 230 138);
}

.freshness-stale7-btn:not(.freshness-ahead-btn--active):not(.freshness-ahead-btn--disabled) {
  border-color: rgb(56 189 248 / 0.45);
  color: rgb(3 105 161);
  background: rgb(56 189 248 / 0.08);
}

[data-theme='dark'] .freshness-stale7-btn:not(.freshness-ahead-btn--active):not(.freshness-ahead-btn--disabled) {
  border-color: rgb(56 189 248 / 0.35);
  color: rgb(186 230 253);
  background: rgb(14 116 144 / 0.2);
}

.freshness-stale7-btn.freshness-ahead-btn--active {
  border-color: rgb(14 165 233);
  background: rgb(14 165 233);
  color: #fff;
  box-shadow: 0 1px 2px rgb(14 165 233 / 0.35);
}

.freshness-stale14-btn:not(.freshness-ahead-btn--active):not(.freshness-ahead-btn--disabled) {
  border-color: rgb(251 113 133 / 0.45);
  color: rgb(190 18 60);
  background: rgb(251 113 133 / 0.08);
}

[data-theme='dark'] .freshness-stale14-btn:not(.freshness-ahead-btn--active):not(.freshness-ahead-btn--disabled) {
  border-color: rgb(251 113 133 / 0.35);
  color: rgb(254 205 211);
  background: rgb(190 18 60 / 0.22);
}

.freshness-stale14-btn.freshness-ahead-btn--active {
  border-color: rgb(244 63 94);
  background: rgb(244 63 94);
  color: #fff;
  box-shadow: 0 1px 2px rgb(244 63 94 / 0.35);
}
</style>
