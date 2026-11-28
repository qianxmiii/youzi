<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { NButton, NTag } from 'naive-ui'
import { ICON_STROKE } from '@/constants/icons'
import type { VoyagePortCall } from '@/types/vesselSchedule'

const props = defineProps<{ ports: VoyagePortCall[]; disabled?: boolean }>()
const originId = defineModel<string | null>('originId', { required: true })
const destinationId = defineModel<string | null>('destinationId', { required: true })
const mode = ref<'origin' | 'destination'>('origin')
const expandedId = ref<string | null>(null)
const portsBySequence = computed(() => props.ports.filter(port => port.id).sort((a, b) => a.sequence - b.sequence))
const origin = computed(() => portsBySequence.value.find(port => port.id === originId.value))
const destination = computed(() => portsBySequence.value.find(port => port.id === destinationId.value))
const hasRoute = computed(() => new Set(portsBySequence.value.map(port => port.sequence)).size > 1)

const dateText = (value?: string | null) => value?.slice(0, 10) || '—'
const portName = (port: VoyagePortCall) => port.portCnname || port.portName

function selectable(port: VoyagePortCall) {
  if (props.disabled || !port.id) return false
  if (mode.value === 'destination') return !!origin.value && port.sequence > origin.value.sequence
  return portsBySequence.value.some(next => next.sequence > port.sequence)
}

function rangePosition(port: VoyagePortCall) {
  if (port.id === originId.value) return 'origin'
  if (port.id === destinationId.value) return 'destination'
  if (origin.value && destination.value && port.sequence > origin.value.sequence && port.sequence < destination.value.sequence) {
    return 'inside'
  }
  return 'outside'
}

function selectPort(port: VoyagePortCall) {
  if (!port.id || !selectable(port)) return
  if (mode.value === 'destination') {
    destinationId.value = port.id
    mode.value = 'origin'
    return
  }
  originId.value = port.id
  destinationId.value = null
  mode.value = 'destination'
}
</script>

<template>
  <section class="space-y-2" aria-label="选择挂靠港">
    <div class="flex gap-2" role="group" aria-label="选择港口用途">
      <NButton size="small" secondary :type="mode === 'origin' ? 'primary' : 'default'" :aria-pressed="mode === 'origin'" :disabled="disabled" @click="mode = 'origin'">起运港</NButton>
      <NButton size="small" secondary :type="mode === 'destination' ? 'primary' : 'default'" :aria-pressed="mode === 'destination'" :disabled="disabled || !origin" @click="mode = 'destination'">目的港</NButton>
    </div>
    <div class="max-h-[min(42vh,22rem)] overflow-auto rounded-lg border border-[var(--color-border)]">
      <table class="w-full text-left text-sm">
        <thead class="sticky top-0 z-10 bg-[var(--color-panel)] text-xs text-[var(--color-muted)]">
          <tr><th scope="col" class="px-3 py-2">挂靠港</th><th scope="col" class="px-2 py-2">到港</th><th scope="col" class="px-2 py-2">离港</th><th scope="col" class="w-10"><span class="sr-only">日期明细</span></th></tr>
        </thead>
        <tbody>
          <template v-for="port in portsBySequence" :key="port.id">
            <tr class="port-row border-t border-[var(--color-border)]"
              :class="[
                `port-row--${rangePosition(port)}`,
                selectable(port) ? 'port-row--selectable cursor-pointer' : 'port-row--inactive',
              ]"
              @click="selectPort(port)">
              <td class="px-3 py-1.5">
                <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                  <button type="button" class="text-left enabled:font-medium focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]"
                    :disabled="!selectable(port)" :aria-label="`选择 ${port.sequence} · ${portName(port)} 为${mode === 'origin' ? '起运港' : '目的港'}`"
                    :aria-pressed="port.id === (mode === 'origin' ? originId : destinationId)"
                    @click.stop="selectPort(port)">
                    <span class="port-sequence mr-1.5 inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-xs tabular-nums">{{ port.sequence }}</span>{{ portName(port) }}
                  </button>
                  <NTag v-if="port.id === originId" size="small" type="info" :bordered="false">起运</NTag>
                  <NTag v-if="port.id === destinationId" size="small" type="success" :bordered="false">目的</NTag>
                </div>
              </td>
              <td class="px-2 py-1.5 tabular-nums">
                <span class="whitespace-nowrap">{{ dateText(port.ata || port.eta) }}</span>
                <span v-if="!port.ata && port.eta" class="ml-1 whitespace-nowrap text-xs text-[var(--color-muted)]">预计</span>
              </td>
              <td class="px-2 py-1.5 tabular-nums">
                <span class="whitespace-nowrap">{{ dateText(port.atd || port.etd) }}</span>
                <span v-if="!port.atd && port.etd" class="ml-1 whitespace-nowrap text-xs text-[var(--color-muted)]">预计</span>
              </td>
              <td class="px-1 py-1.5">
                <NButton size="tiny" quaternary circle :aria-expanded="expandedId === port.id"
                  :title="`${portName(port)}日期明细`" :aria-label="`${portName(port)}日期明细`"
                  @click.stop="expandedId = expandedId === port.id ? null : port.id ?? null">
                  <template #icon><ChevronDown :size="14" :stroke-width="ICON_STROKE" :class="{ 'rotate-180': expandedId === port.id }" aria-hidden="true" /></template>
                </NButton>
              </td>
            </tr>
            <tr v-if="expandedId === port.id" class="port-details" :class="`port-row--${rangePosition(port)}`">
              <td colspan="4" class="border-t border-[var(--color-border)] px-3 py-2">
                <dl class="grid grid-cols-2 gap-x-3 gap-y-1 text-xs tabular-nums sm:grid-cols-4">
                  <div><dt class="text-[var(--color-muted)]">实际到港</dt><dd>{{ dateText(port.ata) }}</dd></div>
                  <div><dt class="text-[var(--color-muted)]">预计到港</dt><dd>{{ dateText(port.eta) }}</dd></div>
                  <div><dt class="text-[var(--color-muted)]">实际离港</dt><dd>{{ dateText(port.atd) }}</dd></div>
                  <div><dt class="text-[var(--color-muted)]">预计离港</dt><dd>{{ dateText(port.etd) }}</dd></div>
                </dl>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <p v-if="!hasRoute" role="alert" class="text-xs text-[var(--color-muted)]">该航次需要至少两个有先后顺序的挂靠港。</p>
    <p v-if="origin" aria-live="polite" class="flex flex-wrap items-center gap-x-2 text-sm">
      <span class="font-medium">{{ portName(origin) }}</span>
      <span class="text-[var(--color-muted)]">{{ dateText(origin.atd || origin.etd) }} {{ !origin.atd && origin.etd ? '预计离港' : '离港' }}</span>
      <span aria-hidden="true">→</span>
      <template v-if="destination">
        <span class="font-medium">{{ portName(destination) }}</span>
        <span class="text-[var(--color-muted)]">{{ dateText(destination.ata || destination.eta) }} {{ !destination.ata && destination.eta ? '预计到港' : '到港' }}</span>
      </template>
      <span v-else class="text-[var(--color-muted)]">选择目的港</span>
    </p>
  </section>
</template>

<style scoped>
.port-row--outside.port-row--selectable:hover,
.port-details.port-row--outside {
  background: var(--color-border-subtle);
}

.port-row--outside.port-row--inactive,
.port-sequence {
  color: var(--color-muted);
}

.port-row--inside {
  background: color-mix(in srgb, var(--tag-indigo-bg) 65%, var(--color-panel));
  border-top-color: transparent;
}

.port-row--origin,
.port-row--destination {
  background: color-mix(in srgb, var(--tag-indigo-fg) 11%, var(--color-panel));
  border-top-color: transparent;
}

.port-row--origin .port-sequence,
.port-row--destination .port-sequence {
  background: color-mix(in srgb, var(--tag-indigo-fg) 85%, var(--color-panel));
  color: var(--color-panel);
  font-weight: 700;
}
</style>
