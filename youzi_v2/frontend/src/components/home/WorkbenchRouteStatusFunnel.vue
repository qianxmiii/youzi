<script setup lang="ts">
import { AlertTriangle, ChevronRight } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { WorkbenchRouteStatusModule } from '@/api/workbench'
import { ICON_STROKE } from '@/constants/icons'
import { ROUTE_STATUS_BADGE_TONE } from '@/constants/shipmentRouteStatus'

const props = defineProps<{
  module: WorkbenchRouteStatusModule | null
  loading?: boolean
  error?: string | null
  /** 异常跟踪待处理，用于摘要「异常滞留」 */
  exceptionStuck?: number
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

const PIPELINE_SHORT: Record<string, string> = {
  WAREHOUSE_IN: '入库',
  EXPORT_CUSTOMS_RELEASE: '出口放行',
  DEPARTED_POL: '离起运港',
  ARRIVED_POD: '到目的港',
  DEST_TRANSIT_WAREHOUSE: '目的中转仓',
  TRUCK_DISPATCH_APPOINTED: '卡派约仓',
  LAST_MILE_HANDOVER: '快递交仓',
  TRACK_SIGNED: '轨迹签收',
}

const TODAY_ROUTE_CODE: Record<string, string> = {
  TODAY_DEPARTED: 'DEPARTED_POL',
  TODAY_ARRIVED: 'ARRIVED_POD',
  TODAY_INTERNAL_DELIVERED: 'TRACK_SIGNED',
  TODAY_DEST_TRANSIT: 'DEST_TRANSIT_WAREHOUSE',
  TODAY_LAST_MILE: 'LAST_MILE_HANDOVER',
  TODAY_ROUTE_SIGNED: 'TRACK_SIGNED',
}

function toneOf(code: string | null | undefined): Tone {
  const key = (code || '').trim().toUpperCase()
  return (ROUTE_STATUS_BADGE_TONE[key] as Tone) || 'default'
}

const exceptionItems = computed(() =>
  (props.module?.items ?? []).filter((item) => item.isException),
)

const pipelineItems = computed(() =>
  (props.module?.items ?? []).filter((item) => !item.isException),
)

const customsExceptionTotal = computed(() =>
  exceptionItems.value.reduce((sum, item) => sum + item.count, 0),
)

const healthRate = computed(() => {
  const total = props.module?.unsignedTotal ?? 0
  if (total <= 0) return 100
  const missing = props.module?.missingCount ?? 0
  const exc = customsExceptionTotal.value
  const healthy = Math.max(0, total - missing - exc)
  return Math.round((healthy / total) * 1000) / 10
})

const todayChips = computed(() => {
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

function goExceptions() {
  void router.push({ path: '/shipment-exceptions', query: { status: 'open' } })
}

function pipelineLabel(code: string, fallback: string) {
  return PIPELINE_SHORT[code] || fallback
}
</script>

<template>
  <div class="wb-route-stack">
    <section class="panel wb-detail">
      <div class="wb-detail__head">
        <div class="min-w-0">
          <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">明细状态</h2>
          <p class="page-subtitle mt-1">未签收运单在 DPS 明细节点上的分布与清关风险</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <button
            v-if="error && !loading"
            type="button"
            class="wb-link-btn"
            @click="emit('retry')"
          >
            重试
          </button>
          <button type="button" class="wb-link-btn" @click="goAll">
            查看全部明细
            <ChevronRight class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" aria-hidden="true" />
          </button>
        </div>
      </div>

      <p v-if="error && !module" class="mt-2 text-xs text-red-500">{{ error }}</p>

      <div v-if="loading && !module" class="mt-4 space-y-3">
        <div class="wb-summary wb-summary--skel h-14" />
        <div class="grid gap-2 md:grid-cols-3">
          <div v-for="i in 3" :key="i" class="h-24 rounded-xl border border-[var(--color-border)] wb-shimmer" />
        </div>
        <div class="h-20 rounded-xl border border-[var(--color-border)] wb-shimmer" />
      </div>

      <template v-else-if="module">
        <div class="wb-summary" role="status">
          <span class="wb-summary__item">
            全网在途未签收
            <strong class="wb-summary__num">{{ module.unsignedTotal }}</strong>
            单
          </span>
          <span v-if="customsExceptionTotal > 0" class="wb-summary__sep" aria-hidden="true">·</span>
          <span v-if="customsExceptionTotal > 0" class="wb-summary__item wb-summary__item--warn">
            清关异常明细
            <strong class="wb-summary__num">{{ customsExceptionTotal }}</strong>
            单
          </span>
          <span v-if="(exceptionStuck ?? 0) > 0" class="wb-summary__sep" aria-hidden="true">·</span>
          <button
            v-if="(exceptionStuck ?? 0) > 0"
            type="button"
            class="wb-summary__item wb-summary__link"
            @click="goExceptions"
          >
            异常滞留
            <strong class="wb-summary__num">{{ exceptionStuck }}</strong>
            单
          </button>
        </div>

        <div class="wb-alert-grid">
          <button
            v-for="item in exceptionItems"
            :key="item.code"
            type="button"
            class="wb-alert-card wb-alert-card--danger"
            @click="go(item.href)"
          >
            <span class="wb-alert-card__icon wb-alert-card__icon--danger" aria-hidden="true">
              <AlertTriangle class="h-[1.15rem] w-[1.15rem]" :stroke-width="ICON_STROKE" />
            </span>
            <span class="wb-alert-card__title">{{ item.nameZh }}</span>
            <span class="wb-alert-card__count">{{ item.count }}</span>
          </button>

          <div class="wb-alert-card wb-alert-card--health" role="presentation">
            <span class="wb-alert-card__title">全链路正向履约流转中</span>
            <span class="wb-alert-card__health-rate">{{ healthRate }}%</span>
            <span class="wb-alert-card__hint">
              {{ pipelineItems.length }} 大节点正常推进；无明细状态
              <button
                type="button"
                class="wb-inline-link"
                @click="go(module.missingHref)"
              >
                {{ module.missingCount }} 单
              </button>
            </span>
          </div>
        </div>

        <div class="wb-process">
          <div class="wb-process__head">
            <p class="wb-process__title">标准干线物流进程（按节点顺序流转）</p>
            <p class="wb-process__hint">点击单卡可按节点筛选运单</p>
          </div>
          <div class="wb-process__grid" role="list">
            <button
              v-for="(step, idx) in pipelineItems"
              :key="step.code"
              type="button"
              class="wb-process__card"
              :class="[
                `wb-process__card--${toneOf(step.code)}`,
                {
                  'wb-process__card--signed': step.code === 'TRACK_SIGNED',
                  'wb-process__card--zero': step.count === 0,
                },
              ]"
              role="listitem"
              :aria-label="`${pipelineLabel(step.code, step.nameZh)} ${step.count} 单`"
              @click="go(step.href)"
            >
              <span class="wb-process__card-top">
                <span class="wb-process__seq">{{
                  String(idx + 1).padStart(2, '0')
                }}</span>
                <span class="wb-process__dot" aria-hidden="true" />
              </span>
              <span class="wb-process__name">{{
                pipelineLabel(step.code, step.nameZh)
              }}</span>
              <span class="wb-process__count">{{ step.count }}</span>
            </button>
          </div>
        </div>
      </template>
    </section>

    <section v-if="todayChips.length || (loading && !module)" class="panel wb-today">
      <div class="wb-today__head">
        <div>
          <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">今日动态</h2>
          <p class="page-subtitle mt-1">按本地自然日统计，截止当日 23:59（北京时间）</p>
        </div>
      </div>

      <div v-if="loading && !module" class="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-7">
        <div v-for="i in 7" :key="i" class="h-16 rounded-lg border border-[var(--color-border)] wb-shimmer" />
      </div>

      <div v-else class="wb-today-grid">
        <button
          v-for="chip in todayChips"
          :key="chip.key"
          type="button"
          class="wb-today-tile"
          :class="[
            `wb-today-tile--${chip.tone}`,
            { 'wb-today-tile--emphasis': chip.emphasis, 'wb-today-tile--zero': chip.count === 0 },
          ]"
          @click="go(chip.href)"
        >
          <span class="wb-today-tile__label">{{ chip.label }}</span>
          <span class="wb-today-tile__count">{{ chip.count }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.wb-route-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.wb-detail,
.wb-today {
  padding: 1rem 1.05rem 1.1rem;
}

.wb-detail__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.65rem 1rem;
}

.wb-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  padding: 0;
  border: none;
  background: transparent;
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-accent-text);
  cursor: pointer;
}

.wb-link-btn:hover {
  text-decoration: underline;
}

.wb-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.35rem 0.5rem;
  margin-top: 0.85rem;
  padding: 0.65rem 0.85rem;
  border-radius: 0.65rem;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-accent-text) 5%, var(--color-elevated));
  font-size: 0.8rem;
  color: var(--color-fg-secondary);
}

.wb-summary--skel {
  background: var(--color-btn-ghost-bg);
}

.wb-summary__num {
  margin: 0 0.15rem;
  font-size: 1.05rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.wb-summary__item--warn .wb-summary__num {
  color: var(--tag-error-fg);
}

.wb-summary__sep {
  color: var(--color-muted);
}

.wb-summary__link {
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.wb-summary__link:hover .wb-summary__num {
  text-decoration: underline;
}

.wb-alert-grid {
  display: grid;
  gap: 0.65rem;
  margin-top: 0.75rem;
}

@media (min-width: 900px) {
  .wb-alert-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.wb-alert-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.35rem;
  min-height: 4.75rem;
  padding: 0.85rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    transform 0.12s ease;
}

.wb-alert-card--danger {
  background: color-mix(in srgb, var(--tag-error-fg) 8%, var(--color-elevated));
  border-color: color-mix(in srgb, var(--tag-error-fg) 35%, var(--color-border));
}

.wb-alert-card--danger:hover {
  border-color: color-mix(in srgb, var(--tag-error-fg) 55%, var(--color-border));
}

.wb-alert-card--health {
  cursor: default;
  background: color-mix(in srgb, var(--tag-sky-fg) 10%, var(--color-elevated));
  border-color: color-mix(in srgb, var(--tag-sky-fg) 35%, var(--color-border));
}

.wb-alert-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.5rem;
}

.wb-alert-card__icon--danger {
  color: var(--tag-error-fg);
  background: color-mix(in srgb, var(--tag-error-fg) 14%, transparent);
}

.wb-alert-card__title {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
  line-height: 1.3;
}

.wb-alert-card__count {
  font-size: 1.75rem;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--tag-error-fg);
}

.wb-alert-card__health-rate {
  font-size: 1.75rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--tag-sky-fg);
}

.wb-alert-card__hint {
  font-size: 0.72rem;
  line-height: 1.45;
  color: var(--color-muted);
}

.wb-inline-link {
  padding: 0;
  border: none;
  background: none;
  font: inherit;
  color: var(--color-accent-text);
  cursor: pointer;
  text-decoration: underline;
}

.wb-process {
  --node-accent: var(--color-muted);
  margin-top: 1rem;
  padding: 0.85rem 0.9rem 1rem;
  border-radius: 0.75rem;
  border: 1px solid var(--color-border);
  background: color-mix(in srgb, var(--color-border-subtle) 55%, var(--color-elevated));
}

.wb-process__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem 1rem;
  margin-bottom: 0.65rem;
}

.wb-process__title {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-fg-secondary);
}

.wb-process__hint {
  margin: 0;
  font-size: 0.68rem;
  color: var(--color-muted);
}

.wb-process__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

@media (min-width: 640px) {
  .wb-process__grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1024px) {
  .wb-process__grid {
    grid-template-columns: repeat(8, minmax(0, 1fr));
  }
}

.wb-process__card {
  --node-accent: var(--color-muted);
  display: flex;
  min-height: 6.75rem;
  flex-direction: column;
  align-items: stretch;
  padding: 0.55rem 0.65rem 0.6rem;
  border: 1px solid color-mix(in srgb, var(--color-border) 90%, transparent);
  border-radius: 0.65rem;
  background: var(--color-elevated);
  text-align: left;
  cursor: pointer;
  box-shadow: 0 1px 0 color-mix(in srgb, var(--color-border) 40%, transparent);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    transform 0.12s ease;
}

.wb-process__card:hover {
  border-color: color-mix(in srgb, var(--node-accent) 35%, var(--color-border));
  box-shadow: 0 2px 8px color-mix(in srgb, var(--node-accent) 12%, transparent);
}

.wb-process__card:active {
  transform: scale(0.985);
}

.wb-process__card--signed {
  background: color-mix(in srgb, var(--tag-success-fg) 9%, var(--color-elevated));
  border-color: color-mix(in srgb, var(--tag-success-fg) 28%, var(--color-border));
}

.wb-process__card--zero {
  opacity: 0.58;
}

.wb-process__card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.35rem;
}

.wb-process__seq {
  font-size: 0.62rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.06em;
  color: var(--color-muted);
}

.wb-process__dot {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 999px;
  background: var(--node-accent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--node-accent) 22%, transparent);
}

.wb-process__name {
  flex: 1;
  font-size: 0.72rem;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-fg-secondary);
}

.wb-process__count {
  margin-top: 0.35rem;
  font-size: 1.65rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  color: var(--node-accent);
}

.wb-process__card--sky {
  --node-accent: var(--tag-sky-fg);
}
.wb-process__card--teal {
  --node-accent: var(--tag-teal-fg);
}
.wb-process__card--indigo {
  --node-accent: var(--tag-indigo-fg);
}
.wb-process__card--violet {
  --node-accent: var(--tag-violet-fg);
}
.wb-process__card--cyan {
  --node-accent: var(--tag-cyan-fg);
}
.wb-process__card--warning {
  --node-accent: var(--tag-slate-fg);
}
.wb-process__card--orange {
  --node-accent: var(--tag-orange-fg);
}
.wb-process__card--success {
  --node-accent: var(--tag-success-fg);
}
.wb-process__card--default {
  --node-accent: var(--tag-default-fg);
}

.wb-today__head {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.wb-today-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.75rem;
}

@media (min-width: 640px) {
  .wb-today-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (min-width: 1100px) {
  .wb-today-grid {
    grid-template-columns: repeat(7, minmax(0, 1fr));
  }
}

.wb-today-tile {
  --tile-accent: var(--color-muted);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.65rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 0.65rem;
  background: var(--color-elevated);
  text-align: left;
  cursor: pointer;
}

.wb-today-tile--error {
  --tile-accent: var(--tag-error-fg);
}
.wb-today-tile--success {
  --tile-accent: var(--tag-success-fg);
}
.wb-today-tile--indigo {
  --tile-accent: var(--tag-indigo-fg);
}
.wb-today-tile--sky {
  --tile-accent: var(--tag-sky-fg);
}
.wb-today-tile--default {
  --tile-accent: var(--tag-default-fg);
}

.wb-today-tile--emphasis {
  border-color: color-mix(in srgb, var(--tile-accent) 40%, var(--color-border));
  background: color-mix(in srgb, var(--tile-accent) 8%, var(--color-elevated));
}

.wb-today-tile__label {
  font-size: 0.72rem;
  color: var(--color-muted);
}

.wb-today-tile__count {
  font-size: 1.25rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--tile-accent);
}

.wb-today-tile--zero {
  opacity: 0.55;
}

.wb-shimmer {
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
  .wb-shimmer {
    animation: none;
  }
}
</style>
