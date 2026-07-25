<script setup lang="ts">
import { Anchor, ChevronRight } from 'lucide-vue-next'
import { NButton } from 'naive-ui'
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ICON_STROKE } from '@/constants/icons'
import type { WorkbenchArrivalDayGroup, WorkbenchArrivalItem } from '@/api/workbench'

const props = defineProps<{
  items: WorkbenchArrivalItem[]
  loading?: boolean
  error?: string | null
  available?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const router = useRouter()

const GROUP_LABEL: Record<WorkbenchArrivalDayGroup, string> = {
  today: '今天',
  tomorrow: '明天',
  later: '后天及以后',
}

const grouped = computed(() => {
  const order: WorkbenchArrivalDayGroup[] = ['today', 'tomorrow', 'later']
  return order
    .map((key) => ({
      key,
      label: GROUP_LABEL[key],
      items: props.items.filter((item) => item.dayGroup === key),
    }))
    .filter((g) => g.items.length > 0)
})

function formatEta(eta: string | null) {
  const raw = (eta || '').trim()
  if (!raw) return '—'
  const m = raw.match(/(\d{2})-(\d{2})[ T](\d{2}:\d{2})/)
  if (m) return `${m[1]}-${m[2]} ${m[3]}`
  return raw.slice(5, 16)
}

function openItem(item: WorkbenchArrivalItem) {
  if (item.href) {
    void router.push(item.href)
    return
  }
  void router.push({ path: '/vessel-schedules', query: { maritimeStatus: 'arriving_soon' } })
}

function openAll() {
  void router.push({ path: '/vessel-schedules', query: { maritimeStatus: 'arriving_soon' } })
}
</script>

<template>
  <section class="panel flex min-h-[16rem] flex-col p-4">
    <div class="mb-2.5 flex items-center justify-between gap-2">
      <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">近期到港</h2>
      <NButton text size="tiny" type="primary" class="cursor-pointer" @click="openAll">
        查看全部
      </NButton>
    </div>

    <div
      v-if="error && available === false"
      class="mb-2 flex items-center justify-between gap-2 text-xs text-red-500"
    >
      <span>{{ error }}</span>
      <button
        type="button"
        class="cursor-pointer border-0 bg-transparent text-[var(--color-accent-text)] hover:underline"
        @click="emit('retry')"
      >
        重试
      </button>
    </div>

    <div v-if="loading && !items.length" class="arrival-empty">加载中…</div>
    <div v-else-if="!items.length" class="arrival-empty">未来三天暂无到港</div>
    <div v-else class="flex flex-col gap-3">
      <div v-for="group in grouped" :key="group.key">
        <h3 class="mb-1.5 text-[0.72rem] font-semibold tracking-wide text-[var(--color-muted)]">
          {{ group.label }}
        </h3>
        <ul class="flex flex-col gap-1">
          <li v-for="(item, idx) in group.items" :key="`${item.vesselVoyage}-${item.eta}-${idx}`">
            <button type="button" class="arrival-row" @click="openItem(item)">
              <span class="arrival-row__icon" aria-hidden="true">
                <Anchor class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-[0.85rem] font-semibold text-[var(--color-fg-emphasis)]">
                  {{ item.vesselVoyage || '—' }}
                </span>
                <span class="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[0.72rem] text-[var(--color-muted)]">
                  <span>{{ item.destinationPortCode || '目的港待定' }}</span>
                  <span
                    v-if="item.isSubscribedPort"
                    class="rounded px-1 py-px text-[0.68rem] font-semibold text-sky-600 dark:text-sky-400"
                  >
                    订阅港
                  </span>
                  <span>· ETA {{ formatEta(item.eta) }}</span>
                  <span class="font-medium text-[var(--color-fg-secondary)]">
                    · {{ item.shipmentCount }} 票
                  </span>
                </span>
              </span>
              <ChevronRight
                class="arrival-row__chevron h-4 w-4 shrink-0 text-[var(--color-muted)]"
                :stroke-width="ICON_STROKE"
                aria-hidden="true"
              />
            </button>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.arrival-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.55rem;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  background: transparent;
  padding: 0.45rem 0.4rem;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.arrival-row:hover {
  border-color: var(--color-border);
  background: var(--color-btn-ghost-bg);
}

.arrival-row:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.arrival-row__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  flex-shrink: 0;
  border-radius: 0.45rem;
  color: #0284c7;
  background: color-mix(in srgb, #0284c7 12%, transparent);
}

.arrival-row:hover .arrival-row__chevron {
  color: var(--color-fg-secondary);
  transform: translateX(1px);
}

.arrival-row__chevron {
  transition:
    color 0.15s ease,
    transform 0.15s ease;
}

.arrival-empty {
  padding: 2rem 0.5rem;
  text-align: center;
  font-size: 0.85rem;
  color: var(--color-muted);
}

@media (prefers-reduced-motion: reduce) {
  .arrival-row,
  .arrival-row__chevron {
    transition: none;
  }
}
</style>
