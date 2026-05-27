<script setup lang="ts">
import { computed } from 'vue'
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

const portCount = computed(() => props.portCalls.length)

function displayTime(value: string | null | undefined): string {
  if (value) return value.slice(0, 16)
  return '—'
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
            <td class="px-4 py-3 text-[var(--color-fg)]">{{ displayTime(pc.eta) }}</td>
            <td class="px-4 py-3 text-[var(--color-fg)]">{{ displayTime(pc.ata) }}</td>
            <td class="px-4 py-3 text-[var(--color-fg)]">{{ displayTime(pc.etd) }}</td>
            <td class="px-4 py-3 text-[var(--color-fg)]">{{ displayTime(pc.atd) }}</td>
            <td class="px-4 py-3">
              <span v-if="pc.statusLabel" :class="statusClass(pc.status)">
                {{ pc.statusLabel }}
              </span>
              <span v-else class="text-[var(--color-muted)]">—</span>
            </td>
          </tr>
          <tr v-if="!portCalls.length">
            <td colspan="6" class="px-4 py-8 text-center text-[var(--color-muted)]">
              暂无挂靠港口，请编辑航次或从船公司同步船期
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
