<script setup lang="ts">
import { computed } from 'vue'
import type { TrackingFreshnessStats } from '@/utils/trackingFreshness'

const props = defineProps<{
  stats: TrackingFreshnessStats | null
  noInternalActive: boolean
  noCarrierActive: boolean
  carrierAheadActive: boolean
  pendingReviewActive: boolean
  filteredNoInternalCount?: number | null
  filteredNoCarrierCount?: number | null
  filteredPendingReviewCount?: number | null
  filteredCarrierAheadCount?: number | null
  carrierSyncHint?: string | null
}>()

const emit = defineEmits<{
  toggleNoInternal: []
  toggleNoCarrier: []
  toggleCarrierAhead: []
  togglePendingReview: []
}>()

type QuickFilter = {
  key: 'pendingReview' | 'carrierAhead' | 'noInternal' | 'noCarrier'
  label: string
  active: boolean
  count: number
  titleActive: string
  titleIdle: string
  pendingStyle?: boolean
}

const globalNoInternalCount = computed(() => props.stats?.internal.none ?? 0)
const globalNoCarrierCount = computed(() => props.stats?.carrier.none ?? 0)
const globalCarrierAheadCount = computed(() => props.stats?.carrierAheadOfInternal ?? 0)
const globalPendingReviewCount = computed(() => props.stats?.pendingTrackingTimeReview ?? 0)

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
    pendingStyle: true,
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
  else if (key === 'noInternal') emit('toggleNoInternal')
  else emit('toggleNoCarrier')
}
</script>

<template>
  <div
    class="freshness-panel shrink-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] px-3 py-2.5"
  >
    <div class="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
      <span class="text-xs font-semibold tracking-tight text-[var(--color-fg-emphasis)]">轨迹筛选</span>

      <div class="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <button
          v-for="item in quickFilters"
          :key="item.key"
          type="button"
          class="freshness-ahead-btn"
          :class="{
            'freshness-pending-btn': item.pendingStyle,
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
      </div>

      <p
        v-if="carrierSyncHint"
        class="min-w-0 flex-basis-full truncate text-[10px] text-[var(--color-muted)] sm:flex-1 sm:basis-auto sm:text-right"
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
</style>
