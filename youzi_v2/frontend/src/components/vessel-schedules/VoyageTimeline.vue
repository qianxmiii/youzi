<script setup lang="ts">
import { NButton, useMessage } from 'naive-ui'
import { computed, ref } from 'vue'
import { subscribePortCall, unsubscribePortCall } from '@/api/vesselSchedules'
import type { VoyagePortCall } from '@/types/vesselSchedule'
import { formatPortDisplay } from '@/utils/portDisplay'

const props = defineProps<{
  vesselVoyage: string
  vesselName?: string | null
  voyageNo?: string | null
  vesselCode?: string | null
  shippingCompany?: string | null
  portCalls: VoyagePortCall[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

const message = useMessage()
const togglingId = ref<string | null>(null)

const portCount = computed(() => props.portCalls.length)

const hasUpdatedTimes = computed(() =>
  props.portCalls.some((pc) =>
    (['eta', 'ata', 'etd', 'atd'] as TimeField[]).some((field) => shouldHighlightTimeField(pc, field)),
  ),
)

type TimeField = 'eta' | 'ata' | 'etd' | 'atd'

function timeFieldValue(pc: VoyagePortCall, field: TimeField): string | null | undefined {
  return pc[field]
}

function isTimeFieldUpdated(pc: VoyagePortCall, field: TimeField): boolean {
  return (pc.timeFieldsUpdated ?? []).includes(field)
}

function shouldHighlightTimeField(pc: VoyagePortCall, field: TimeField): boolean {
  return isTimeFieldUpdated(pc, field) && !!timeFieldValue(pc, field)
}

function displayTime(value: string | null | undefined): string {
  if (value) return value.slice(0, 16)
  return '—'
}

function previousTimeText(pc: VoyagePortCall, field: TimeField): string | null {
  if (!shouldHighlightTimeField(pc, field)) return null
  let prev: string | null | undefined
  if (field === 'ata') {
    prev = pc.timePreviousValues?.ata ?? pc.eta
  } else if (field === 'atd') {
    prev = pc.timePreviousValues?.atd ?? pc.etd
  } else {
    prev = pc.timePreviousValues?.[field]
  }
  if (prev === undefined) return null
  if (!prev) return null
  return prev.slice(0, 16)
}

function timeCellClass(pc: VoyagePortCall, field: TimeField): string {
  const base = 'px-1.5 py-0.5'
  if (!timeFieldValue(pc, field)) {
    return `${base} text-[var(--color-muted)]`
  }
  if (!shouldHighlightTimeField(pc, field)) {
    return `${base} text-[var(--color-fg)]`
  }
  return `${base} rounded-md bg-amber-500/15 font-medium text-amber-800 dark:bg-amber-500/20 dark:text-amber-200`
}

function statusClass(status?: string): string {
  const base = 'inline-flex rounded-md px-2 py-0.5 text-xs font-medium'
  switch (status) {
    case 'arriving_soon':
    case 'departing_soon':
      return `${base} bg-amber-500/15 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200`
    case 'arrived':
    case 'departed':
      return `${base} bg-emerald-500/15 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-200`
    case 'planned':
      return `${base} bg-sky-500/15 text-sky-800 dark:bg-sky-500/20 dark:text-sky-200`
    default:
      return `${base} bg-zinc-500/10 text-[var(--color-fg-secondary)]`
  }
}

async function toggleSubscribe(pc: VoyagePortCall) {
  const id = pc.id
  if (!id) {
    message.warning('请先保存航次后再订阅')
    return
  }
  togglingId.value = id
  try {
    if (pc.subscribed) {
      await unsubscribePortCall(id)
      message.success('已取消订阅')
    } else {
      await subscribePortCall(id)
      message.success('已订阅到港通知')
    }
    emit('refresh')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    togglingId.value = null
  }
}
</script>

<template>
  <div
    class="shrink-0 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] shadow-sm"
  >
    <div
      class="border-b border-[var(--color-border)] bg-[var(--color-elevated)] px-4 py-3"
    >
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-[var(--color-fg)]">
          <span class="font-semibold text-[var(--color-fg-emphasis)]">{{ vesselVoyage }}</span>
          <span v-if="vesselName" class="text-[var(--color-fg-secondary)]">船名 {{ vesselName }}</span>
          <span v-if="voyageNo" class="text-[var(--color-fg-secondary)]">航次 {{ voyageNo }}</span>
          <span v-if="vesselCode" class="text-[var(--color-fg-secondary)]">代码 {{ vesselCode }}</span>
          <span v-if="shippingCompany" class="text-[var(--color-fg-secondary)]">
            船公司 {{ shippingCompany }}
          </span>
        </div>
        <span class="shrink-0 text-xs font-medium text-[var(--color-fg-secondary)]">
          共 {{ portCount }} 个挂靠港
          <span
            v-if="hasUpdatedTimes"
            class="ml-2 rounded-md bg-amber-500/15 px-1.5 py-0.5 text-amber-800 dark:bg-amber-500/20 dark:text-amber-200"
          >
            琥珀色为最近更新 · 灰字为原时间
          </span>
        </span>
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="min-w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-[var(--color-border)] bg-[var(--color-surface)]">
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">挂港</th>
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">预计到港</th>
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">实际到港</th>
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">预计离港</th>
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">实际离港</th>
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">状态</th>
            <th class="px-4 py-2.5 text-left font-medium text-[var(--color-fg-secondary)]">到港通知</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(pc, idx) in portCalls"
            :key="pc.id || `${pc.sequence}-${pc.portName}`"
            class="border-b border-[var(--color-border-subtle)]"
            :class="idx % 2 === 0 ? 'bg-[var(--color-panel)]' : 'bg-[var(--color-surface)]'"
          >
            <td class="relative px-4 py-3 pl-10 text-[var(--color-fg-emphasis)]">
              <span
                class="absolute left-4 top-0 bottom-0 w-px bg-[var(--color-border)]"
                :class="idx === portCalls.length - 1 ? 'h-1/2' : ''"
                aria-hidden="true"
              />
              <span
                v-if="idx > 0"
                class="absolute left-4 top-0 h-1/2 w-px bg-[var(--color-border)]"
                aria-hidden="true"
              />
              <span
                class="absolute left-[13px] top-1/2 z-10 h-2.5 w-2.5 -translate-y-1/2 rounded-full border-2 border-[var(--color-panel)] bg-[var(--color-accent)]"
                aria-hidden="true"
              />
              <span class="font-medium">{{ formatPortDisplay(pc) }}</span>
              <span class="ml-2 text-xs text-[var(--color-muted)]">#{{ pc.sequence }}</span>
            </td>
            <td class="px-4 py-3">
              <div :class="timeCellClass(pc, 'eta')">{{ displayTime(pc.eta) }}</div>
              <p v-if="previousTimeText(pc, 'eta')" class="mt-0.5 text-[10px] text-[var(--color-muted)]">
                原 {{ previousTimeText(pc, 'eta') }}
              </p>
            </td>
            <td class="px-4 py-3">
              <div :class="timeCellClass(pc, 'ata')">{{ displayTime(pc.ata) }}</div>
              <p v-if="previousTimeText(pc, 'ata')" class="mt-0.5 text-[10px] text-[var(--color-muted)]">
                原 {{ previousTimeText(pc, 'ata') }}
              </p>
            </td>
            <td class="px-4 py-3">
              <div :class="timeCellClass(pc, 'etd')">{{ displayTime(pc.etd) }}</div>
              <p v-if="previousTimeText(pc, 'etd')" class="mt-0.5 text-[10px] text-[var(--color-muted)]">
                原 {{ previousTimeText(pc, 'etd') }}
              </p>
            </td>
            <td class="px-4 py-3">
              <div :class="timeCellClass(pc, 'atd')">{{ displayTime(pc.atd) }}</div>
              <p v-if="previousTimeText(pc, 'atd')" class="mt-0.5 text-[10px] text-[var(--color-muted)]">
                原 {{ previousTimeText(pc, 'atd') }}
              </p>
            </td>
            <td class="px-4 py-3">
              <span v-if="pc.statusLabel" :class="statusClass(pc.status)">
                {{ pc.statusLabel }}
              </span>
              <span v-else class="text-[var(--color-muted)]">—</span>
            </td>
            <td class="px-4 py-3">
              <NButton
                size="tiny"
                :type="pc.subscribed ? 'primary' : 'default'"
                :quaternary="!pc.subscribed"
                :loading="togglingId === pc.id"
                :disabled="!pc.id"
                @click="toggleSubscribe(pc)"
              >
                {{ pc.subscribed ? '已订阅' : '订阅' }}
              </NButton>
            </td>
          </tr>
          <tr v-if="!portCalls.length">
            <td colspan="7" class="px-4 py-8 text-center text-[var(--color-muted)]">
              暂无挂靠港口，请编辑航次或从船公司同步船期
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
