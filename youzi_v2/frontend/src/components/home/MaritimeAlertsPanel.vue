<script setup lang="ts">
import { NButton, NSpin, NSpace, NTag, useMessage } from 'naive-ui'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  getMaritimeAlertsOverview,
  markPortArrivalNotificationRead,
  type MaritimeAlertsOverview,
  type PortArrivalNotification,
} from '@/api/maritimeAlerts'
import type { MaritimeStatus } from '@/types/vesselSchedule'
import { maritimeStatusTagType } from '@/types/vesselSchedule'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const data = ref<MaritimeAlertsOverview | null>(null)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await getMaritimeAlertsOverview()
  } catch (e) {
    data.value = null
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const alertCards = computed(() => {
  const c = data.value?.counts
  if (!c) return []
  return [
    {
      key: 'arriving_soon',
      label: '三天内到港',
      sub: '运单',
      count: c.arrivingSoon,
      type: 'warning' as const,
      to: '/vessel-schedules',
      query: { maritimeStatus: 'arriving_soon' },
    },
    {
      key: 'departing_soon',
      label: '三天内离港',
      sub: '运单',
      count: c.departingSoon,
      type: 'warning' as const,
      to: '/vessel-schedules',
      query: { maritimeStatus: 'departing_soon' },
    },
    {
      key: 'in_transit',
      label: '在途',
      sub: '运单',
      count: c.inTransit,
      type: 'info' as const,
      to: '/vessel-schedules',
      query: { maritimeStatus: 'in_transit' },
    },
    {
      key: 'port_arriving',
      label: '挂靠将到港',
      sub: '船期',
      count: c.portArrivingSoon,
      type: 'warning' as const,
      to: '/vessel-schedules',
      query: {},
    },
    {
      key: 'port_departing',
      label: '挂靠将离港',
      sub: '船期',
      count: c.portDepartingSoon,
      type: 'warning' as const,
      to: '/vessel-schedules',
      query: {},
    },
    {
      key: 'arrived',
      label: '已到港',
      sub: '运单',
      count: c.arrived,
      type: 'success' as const,
      to: '/vessel-schedules',
      query: { maritimeStatus: 'arrived' },
    },
  ]
})

const hasAlerts = computed(() => {
  const c = data.value?.counts
  const portArrivals = data.value?.portArrivalNotifications?.length ?? 0
  if (portArrivals > 0) return true
  if (!c) return false
  return (
    c.arrivingSoon +
      c.departingSoon +
      c.inTransit +
      c.portArrivingSoon +
      c.portDepartingSoon >
    0
  )
})

const portArrivalNotifications = computed(
  () => data.value?.portArrivalNotifications ?? [],
)

async function dismissPortArrival(n: PortArrivalNotification) {
  try {
    await markPortArrivalNotificationRead(n.id)
    if (data.value) {
      data.value = {
        ...data.value,
        portArrivalNotifications: data.value.portArrivalNotifications.filter((x) => x.id !== n.id),
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

function goVesselSchedules(query?: Record<string, string>) {
  router.push({ path: '/vessel-schedules', query })
}

function goVoyage(voyageId: string) {
  router.push({ path: '/vessel-schedules', query: { voyageId } })
}

function formatTime(raw: string | null | undefined) {
  return raw ? raw.slice(0, 16) : '—'
}
</script>

<template>
  <section class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <div>
        <h3 class="text-sm font-medium text-[var(--color-fg-emphasis)]">海运预警</h3>
        <p v-if="data" class="mt-0.5 text-xs text-[var(--color-muted)]">
          扫描 {{ data.totalScanned }} 票含船期字段运单 · 更新于 {{ data.generatedAt?.slice(0, 16) }}
        </p>
      </div>
      <NSpace size="small">
        <NButton size="small" quaternary @click="goVesselSchedules()">船期监控</NButton>
        <NButton size="small" :loading="loading" @click="load">刷新</NButton>
      </NSpace>
    </div>

    <NSpin :show="loading">
      <div v-if="error" class="panel px-4 py-3 text-sm text-red-400">{{ error }}</div>
      <template v-else-if="data">
        <article
          v-if="portArrivalNotifications.length"
          class="panel border-emerald-500/30 p-4"
        >
          <h4 class="mb-3 text-xs font-medium uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
            港口到港通知
          </h4>
          <ul class="space-y-2">
            <li
              v-for="n in portArrivalNotifications"
              :key="n.id"
              class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-emerald-500/10 px-3 py-2"
            >
              <button
                type="button"
                class="min-w-0 flex-1 text-left"
                @click="goVoyage(n.voyageId)"
              >
                <p class="truncate text-sm font-medium text-[var(--color-fg-emphasis)]">
                  {{ n.portName }} 已到港
                </p>
                <p class="truncate text-xs text-[var(--color-muted)]">{{ n.vesselVoyage }}</p>
                <p class="text-[11px] text-[var(--color-fg-secondary)]">
                  ATA {{ formatTime(n.ata) }} · {{ n.createdAt?.slice(0, 16) }}
                </p>
              </button>
              <NButton size="tiny" quaternary @click="dismissPortArrival(n)">知道了</NButton>
            </li>
          </ul>
        </article>

        <div class="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
          <button
            v-for="card in alertCards"
            :key="card.key"
            type="button"
            class="panel p-3 text-left transition hover:border-[var(--color-border)] hover:bg-[var(--color-nav-hover)]"
            :class="card.count > 0 ? 'border-amber-500/30' : ''"
            @click="goVesselSchedules(card.query as Record<string, string>)"
          >
            <p class="text-[10px] uppercase tracking-wide text-[var(--color-muted)]">{{ card.sub }}</p>
            <p class="mt-0.5 text-xs text-[var(--color-fg-secondary)]">{{ card.label }}</p>
            <p
              class="mt-1 text-2xl font-semibold tabular-nums"
              :class="card.count > 0 ? 'text-[var(--tracking-ahead-fg)]' : 'text-[var(--color-fg-secondary)]'"
            >
              {{ card.count }}
            </p>
          </button>
        </div>

        <div
          v-if="!hasAlerts"
          class="panel border-dashed px-4 py-6 text-center text-sm text-[var(--color-muted)]"
        >
          当前无三天内到/离港或在途预警。可在
          <button type="button" class="text-violet-400 hover:underline" @click="goVesselSchedules()">
            船期监控
          </button>
          订阅挂靠港到港通知，并为运单填写 vessel_voyage 与 ETA/ETD。
        </div>

        <div v-else class="grid gap-4 lg:grid-cols-2">
          <article v-if="data.urgentShipments.length" class="panel p-4">
            <h4 class="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-muted)]">
              关注运单
            </h4>
            <ul class="space-y-2">
              <li
                v-for="s in data.urgentShipments"
                :key="s.shipmentNo"
                class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--color-btn-ghost-bg)] px-3 py-2"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-[var(--color-fg-emphasis)]">{{ s.shipmentNo }}</p>
                  <p class="truncate text-xs text-[var(--color-muted)]">
                    {{ s.vesselVoyage || '未填船名航次' }}
                    <span v-if="s.destinationPortCode"> · {{ s.destinationPortCode }}</span>
                  </p>
                  <p class="text-[11px] text-[var(--color-fg-secondary)]">
                    ETA {{ formatTime(s.eta) }} · ETD {{ formatTime(s.etd) }}
                  </p>
                </div>
                <NTag
                  size="small"
                  :type="maritimeStatusTagType(s.maritimeStatus)"
                  :bordered="false"
                >
                  {{ s.maritimeStatusLabel }}
                </NTag>
              </li>
            </ul>
          </article>

          <article v-if="data.urgentPortCalls.length" class="panel p-4">
            <h4 class="mb-3 text-xs font-medium uppercase tracking-wider text-[var(--color-muted)]">
              挂靠预警
            </h4>
            <ul class="space-y-2">
              <li
                v-for="p in data.urgentPortCalls"
                :key="`${p.voyageId}-${p.sequence}`"
                class="flex cursor-pointer flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--color-btn-ghost-bg)] px-3 py-2 transition hover:bg-[var(--color-nav-hover)]"
                @click="goVoyage(p.voyageId)"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-[var(--color-fg-emphasis)]">{{ p.portName }}</p>
                  <p class="truncate text-xs text-[var(--color-muted)]">{{ p.vesselVoyage }}</p>
                  <p class="text-[11px] text-[var(--color-fg-secondary)]">
                    ETA {{ formatTime(p.eta) }} · ETD {{ formatTime(p.etd) }}
                  </p>
                </div>
                <NTag size="small" :type="maritimeStatusTagType(p.status)" :bordered="false">
                  {{ p.statusLabel }}
                </NTag>
              </li>
            </ul>
          </article>
        </div>

        <div
          v-if="data.unconfiguredVesselVoyages.length"
          class="panel border-amber-500/20 bg-amber-500/5 px-4 py-3"
        >
          <p class="text-xs font-medium text-[var(--tracking-ahead-desc)]">运单有船名航次但未配置航次主数据</p>
          <ul class="mt-2 flex flex-wrap gap-2">
            <li
              v-for="u in data.unconfiguredVesselVoyages"
              :key="u.vesselVoyage"
              class="rounded-md bg-[var(--color-btn-ghost-bg)] px-2 py-1 text-xs text-[var(--color-fg-secondary)]"
            >
              {{ u.vesselVoyage }}（{{ u.shipmentCount }} 票）
            </li>
          </ul>
        </div>
      </template>
    </NSpin>
  </section>
</template>
