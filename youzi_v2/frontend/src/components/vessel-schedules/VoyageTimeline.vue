<script setup lang="ts">
import type { VoyagePortCall } from '@/types/vesselSchedule'

defineProps<{
  vesselVoyage: string
  portCalls: VoyagePortCall[]
}>()

function displayTime(value: string | null | undefined, isPast: boolean): string {
  if (value) return value.slice(0, 16)
  return isPast ? '—' : ''
}

function rowIsPast(pc: VoyagePortCall): boolean {
  return Boolean(pc.ata || pc.atd)
}
</script>

<template>
  <div class="overflow-hidden rounded-lg border border-sky-700/40 shadow-sm">
    <div class="overflow-x-auto">
      <table class="min-w-full border-collapse text-sm">
        <thead>
          <tr class="bg-sky-600 text-white">
            <th class="px-4 py-2.5 text-left font-medium">挂港</th>
            <th class="px-4 py-2.5 text-left font-medium">预计到港</th>
            <th class="px-4 py-2.5 text-left font-medium">实际到港</th>
            <th class="px-4 py-2.5 text-left font-medium">预计离港</th>
            <th class="px-4 py-2.5 text-left font-medium">实际离港</th>
            <th class="px-4 py-2.5 text-left font-medium">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr class="bg-sky-700/90 text-white">
            <td colspan="6" class="px-4 py-1.5 text-xs font-medium tracking-wide">
              航次 {{ vesselVoyage }}
            </td>
          </tr>
          <tr
            v-for="(pc, idx) in portCalls"
            :key="pc.id || `${pc.sequence}-${pc.portName}`"
            class="border-t border-sky-100/10"
            :class="idx % 2 === 0 ? 'bg-sky-50/5' : 'bg-sky-100/10'"
          >
            <td class="relative px-4 py-3 pl-10 text-zinc-100">
              <span
                class="absolute left-4 top-0 bottom-0 w-px bg-zinc-500/60"
                :class="idx === portCalls.length - 1 ? 'h-1/2' : ''"
                aria-hidden="true"
              />
              <span
                v-if="idx > 0"
                class="absolute left-4 top-0 h-1/2 w-px bg-zinc-500/60"
                aria-hidden="true"
              />
              <span
                class="absolute left-[13px] top-1/2 z-10 h-2.5 w-2.5 -translate-y-1/2 rounded-full border-2 border-zinc-900 bg-zinc-300"
                aria-hidden="true"
              />
              <span class="font-medium">{{ pc.portName }}</span>
            </td>
            <td class="px-4 py-3 text-zinc-300">
              {{ rowIsPast(pc) ? '' : displayTime(pc.eta, false) }}
            </td>
            <td class="px-4 py-3 text-zinc-200">
              {{ displayTime(pc.ata, true) }}
            </td>
            <td class="px-4 py-3 text-zinc-300">
              {{ rowIsPast(pc) ? '' : displayTime(pc.etd, false) }}
            </td>
            <td class="px-4 py-3 text-zinc-200">
              {{ displayTime(pc.atd, true) }}
            </td>
            <td class="px-4 py-3">
              <span
                v-if="pc.statusLabel"
                class="inline-flex rounded-md px-2 py-0.5 text-xs font-medium"
                :class="{
                  'bg-amber-500/20 text-amber-200':
                    pc.status === 'arriving_soon' || pc.status === 'departing_soon',
                  'bg-emerald-500/20 text-emerald-200': pc.status === 'arrived' || pc.status === 'departed',
                  'bg-sky-500/20 text-sky-200': pc.status === 'planned',
                  'bg-zinc-500/20 text-zinc-300': pc.status === 'unknown',
                }"
              >
                {{ pc.statusLabel }}
              </span>
            </td>
          </tr>
          <tr v-if="!portCalls.length">
            <td colspan="6" class="px-4 py-8 text-center text-zinc-500">暂无挂靠港口，请编辑航次添加</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
