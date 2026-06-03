<script setup lang="ts">
import { useMessage } from 'naive-ui'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import TableActionIcon from '@/components/common/TableActionIcon.vue'
import { subscribePortCall, unsubscribePortCall } from '@/api/vesselSchedules'
import type { MaritimeStatus, VoyagePortCall } from '@/types/vesselSchedule'
import { formatDateYmd } from '@/utils/formatDateTime'
import { formatPortDisplay } from '@/utils/portDisplay'

const props = defineProps<{
  vesselVoyage: string
  shippingCompany?: string | null
  portCalls: VoyagePortCall[]
  tableFilter?: string
}>()

const emit = defineEmits<{
  refresh: []
}>()

const message = useMessage()
const router = useRouter()
const togglingId = ref<string | null>(null)

type TimeField = 'eta' | 'ata' | 'etd' | 'atd'

const STATUS_EN: Partial<Record<MaritimeStatus, string>> = {
  departed: 'Departed',
  arrived: 'Arrived',
  arriving_soon: 'Arriving soon',
  departing_soon: 'Departing soon',
  in_transit: 'In transit',
  planned: 'Planned',
  unknown: 'Pending',
}

const filteredPortCalls = computed(() => {
  const q = (props.tableFilter ?? '').trim().toLowerCase()
  const sorted = [...props.portCalls].sort((a, b) => a.sequence - b.sequence)
  if (!q) return sorted
  const carrier = (props.shippingCompany ?? '').trim().toLowerCase()
  if (carrier && carrier.includes(q)) return sorted
  return sorted.filter((pc) => {
    const port = formatPortDisplay(pc).toLowerCase()
    const status = (pc.statusLabel || pc.status || '').toLowerCase()
    const code = (pc.portCode || '').toLowerCase()
    return port.includes(q) || status.includes(q) || code.includes(q)
  })
})

const totalPorts = computed(() => filteredPortCalls.value.length)

const rangeLabel = computed(() => {
  if (!totalPorts.value) return '共 0 个挂靠港'
  return `共 ${totalPorts.value} 个挂靠港，可在列表内滚动查看`
})

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
  return formatDateYmd(value)
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
  if (!prev) return null
  return formatDateYmd(prev)
}

function statusLabel(pc: VoyagePortCall): string {
  if (pc.status && STATUS_EN[pc.status]) return STATUS_EN[pc.status]!
  return pc.statusLabel || '—'
}

function statusClass(status?: MaritimeStatus): string {
  const base = 'voyage-status'
  switch (status) {
    case 'arriving_soon':
    case 'departing_soon':
      return `${base} voyage-status--warning`
    case 'arrived':
    case 'departed':
      return `${base} voyage-status--success`
    case 'planned':
      return `${base} voyage-status--planned`
    default:
      return `${base} voyage-status--muted`
  }
}

function isPortCompleted(pc: VoyagePortCall): boolean {
  return pc.status === 'departed' || pc.status === 'arrived' || !!pc.atd || !!pc.ata
}

function portPrimaryName(pc: VoyagePortCall): string {
  const en = (pc.portNameEn || '').trim()
  const cn = (pc.portCnname || '').trim()
  return en || cn || (pc.portName || '').trim() || '—'
}

function portMetaLine(pc: VoyagePortCall): string {
  const code = (pc.portCode || '').trim()
  return code ? `${code} · #${pc.sequence}` : `#${pc.sequence}`
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

function openRelatedShipments() {
  router.push({
    path: '/shipments',
    query: { shipmentNo: props.vesselVoyage },
  })
}
</script>

<template>
  <article class="voyage-timeline panel">
    <header class="voyage-timeline__head">
      <h2 class="voyage-timeline__title">PORT SCHEDULE TIMELINE</h2>
      <span class="voyage-timeline__legend">
        <span class="voyage-timeline__legend-dot" aria-hidden="true" />
        Delayed/Updated
      </span>
    </header>

    <div class="voyage-timeline__table-wrap scrollbar-visible">
      <table class="voyage-timeline__table">
        <thead>
          <tr>
            <th>PORT <span class="voyage-timeline__th-sub">挂港</span></th>
            <th>ETA <span class="voyage-timeline__th-sub">预计到港</span></th>
            <th>ATA <span class="voyage-timeline__th-sub">实际到港</span></th>
            <th>ETD <span class="voyage-timeline__th-sub">预计离港</span></th>
            <th>ATD <span class="voyage-timeline__th-sub">实际离港</span></th>
            <th>STATUS</th>
            <th class="voyage-timeline__th-actions">ACTIONS</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="pc in filteredPortCalls"
            :key="pc.id || `${pc.sequence}-${pc.portName}`"
            class="voyage-timeline__row"
          >
            <td class="voyage-timeline__port">
              <div class="voyage-timeline__port-inner">
                <div class="voyage-timeline__rail-col" aria-hidden="true">
                  <span
                    class="voyage-timeline__rail-dot"
                    :class="{ 'voyage-timeline__rail-dot--done': isPortCompleted(pc) }"
                  />
                </div>
                <div class="voyage-timeline__port-text">
                  <p class="voyage-timeline__port-name">{{ portPrimaryName(pc) }}</p>
                  <p class="voyage-timeline__port-meta">{{ portMetaLine(pc) }}</p>
                </div>
              </div>
            </td>
            <td>
              <div
                class="voyage-time"
                :class="{ 'voyage-time--updated': shouldHighlightTimeField(pc, 'eta') }"
              >
                <span class="voyage-time__current">{{ displayTime(pc.eta) }}</span>
                <span v-if="previousTimeText(pc, 'eta')" class="voyage-time__prev">
                  {{ previousTimeText(pc, 'eta') }}
                </span>
              </div>
            </td>
            <td>
              <div
                class="voyage-time"
                :class="{ 'voyage-time--updated': shouldHighlightTimeField(pc, 'ata') }"
              >
                <span class="voyage-time__current">{{ displayTime(pc.ata) }}</span>
                <span v-if="previousTimeText(pc, 'ata')" class="voyage-time__prev">
                  {{ previousTimeText(pc, 'ata') }}
                </span>
              </div>
            </td>
            <td>
              <div
                class="voyage-time"
                :class="{ 'voyage-time--updated': shouldHighlightTimeField(pc, 'etd') }"
              >
                <span class="voyage-time__current">{{ displayTime(pc.etd) }}</span>
                <span v-if="previousTimeText(pc, 'etd')" class="voyage-time__prev">
                  {{ previousTimeText(pc, 'etd') }}
                </span>
              </div>
            </td>
            <td>
              <div
                class="voyage-time"
                :class="{ 'voyage-time--updated': shouldHighlightTimeField(pc, 'atd') }"
              >
                <span class="voyage-time__current">{{ displayTime(pc.atd) }}</span>
                <span v-if="previousTimeText(pc, 'atd')" class="voyage-time__prev">
                  {{ previousTimeText(pc, 'atd') }}
                </span>
              </div>
            </td>
            <td>
              <span v-if="pc.status || pc.statusLabel" :class="statusClass(pc.status)">
                {{ statusLabel(pc) }}
              </span>
              <span v-else class="voyage-time__current text-[var(--color-muted)]">—</span>
            </td>
            <td>
              <div class="voyage-timeline__actions">
                <TableActionIcon
                  kind="subscribe"
                  :title="pc.subscribed ? '已订阅，点击取消' : '订阅到港通知'"
                  :active="!!pc.subscribed"
                  :loading="togglingId === pc.id"
                  @click="toggleSubscribe(pc)"
                />
                <button
                  type="button"
                  class="voyage-timeline__link-btn"
                  title="查看关联运单"
                  @click="openRelatedShipments"
                >
                  <svg viewBox="0 0 20 20" fill="none" class="voyage-timeline__link-icon" aria-hidden="true">
                    <path
                      d="M7 11.5 12.5 6M12.5 6H8.8M12.5 6v3.7"
                      stroke="currentColor"
                      stroke-width="1.35"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M5.5 5.5h3.2v3.2H5.5V5.5ZM11.3 11.3h3.2v3.2h-3.2v-3.2Z"
                      stroke="currentColor"
                      stroke-width="1.35"
                      stroke-linejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredPortCalls.length">
            <td colspan="7" class="voyage-timeline__empty">
              {{ portCalls.length ? '无匹配挂靠港' : '暂无挂靠港口，请编辑航次或从船公司同步船期' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="totalPorts > 0" class="voyage-timeline__foot">
      <p class="voyage-timeline__range">{{ rangeLabel }}</p>
    </footer>
  </article>
</template>

<style scoped>
.voyage-timeline {
  padding: 0;
  overflow: visible;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.voyage-timeline:hover {
  border-color: var(--color-border);
  box-shadow: 0 2px 12px rgb(24 24 27 / 0.06);
}

[data-theme='dark'] .voyage-timeline:hover {
  box-shadow: 0 2px 14px rgb(0 0 0 / 0.22);
}

.voyage-timeline__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-list-divider);
}

.voyage-timeline__title {
  margin: 0;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-fg-secondary);
}

.voyage-timeline__legend {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: var(--color-muted);
}

.voyage-timeline__legend-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  background: rgb(251 146 60);
}

.voyage-timeline__table-wrap {
  max-height: min(28rem, calc(100vh - 16rem));
  overflow: auto;
  scrollbar-gutter: stable;
}

.voyage-timeline__table {
  width: 100%;
  min-width: 56rem;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.voyage-timeline__table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 0.625rem 1rem;
  text-align: left;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--color-muted);
  background: var(--color-panel);
  border-bottom: 1px solid var(--color-list-divider);
  box-shadow: 0 1px 0 var(--color-list-divider);
  white-space: nowrap;
}

.voyage-timeline__th-sub {
  font-weight: 500;
  letter-spacing: 0;
  opacity: 0.85;
}

.voyage-timeline__th-actions {
  text-align: right;
}

.voyage-timeline__row {
  border-bottom: 1px solid var(--color-list-divider);
}

.voyage-timeline__row:last-child {
  border-bottom: none;
}

.voyage-timeline__port {
  padding: 0.875rem 1rem;
  vertical-align: top;
}

.voyage-timeline__port-inner {
  display: flex;
  align-items: stretch;
  gap: 0.75rem;
  min-height: 3rem;
}

.voyage-timeline__rail-col {
  position: relative;
  width: 1.25rem;
  flex-shrink: 0;
  align-self: stretch;
}

/* 竖线贯穿整行，与上下行在单元格边界处衔接成连续时间轴 */
.voyage-timeline__rail-col::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-50%);
  background: var(--color-list-divider);
}

.voyage-timeline__row:first-child .voyage-timeline__rail-col::before {
  top: 1rem;
}

.voyage-timeline__row:last-child .voyage-timeline__rail-col::before {
  bottom: calc(100% - 1rem);
}

.voyage-timeline__row:not(:last-child) .voyage-timeline__rail-col::before {
  bottom: -1px;
}

.voyage-timeline__row:only-child .voyage-timeline__rail-col::before {
  display: none;
}

.voyage-timeline__rail-dot {
  position: absolute;
  left: 50%;
  top: 1rem;
  z-index: 1;
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 9999px;
  border: 2px solid var(--color-panel);
  background: var(--color-muted);
  transform: translate(-50%, -50%);
  flex-shrink: 0;
}

.voyage-timeline__port-text {
  flex: 1;
  min-width: 0;
  padding-top: 0.375rem;
  padding-bottom: 0.375rem;
}

.voyage-timeline__rail-dot--done {
  background: var(--color-accent-text);
  box-shadow: 0 0 0 2px rgb(70 72 212 / 0.2);
}

.voyage-timeline__port-name {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.voyage-timeline__port-meta {
  margin: 0.125rem 0 0;
  font-size: 0.6875rem;
  color: var(--color-muted);
}

.voyage-timeline__table tbody td {
  padding: 0.875rem 1rem;
  vertical-align: top;
  color: var(--color-fg);
}

.voyage-time__current {
  display: block;
  color: var(--color-fg);
}

.voyage-time--updated .voyage-time__current {
  display: inline-block;
  border-radius: 0.375rem;
  background: rgb(251 146 60 / 0.14);
  padding: 0.125rem 0.375rem;
  font-weight: 600;
  color: rgb(194 65 12);
}

.voyage-time__prev {
  display: block;
  margin-top: 0.125rem;
  font-size: 0.625rem;
  color: rgb(234 88 12 / 0.85);
  text-decoration: line-through;
}

.voyage-time:not(.voyage-time--updated) .voyage-time__current:only-child {
  color: var(--color-fg-secondary);
}

.voyage-status {
  display: inline-flex;
  border-radius: 9999px;
  padding: 0.125rem 0.5rem;
  font-size: 0.6875rem;
  font-weight: 600;
}

.voyage-status--success {
  background: rgb(16 185 129 / 0.12);
  color: rgb(21 128 61);
}

.voyage-status--planned {
  background: rgb(59 130 246 / 0.12);
  color: rgb(29 78 216);
}

.voyage-status--warning {
  background: rgb(251 146 60 / 0.14);
  color: rgb(194 65 12);
}

.voyage-status--muted {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg-secondary);
}

.voyage-timeline__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
}

.voyage-timeline__link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.voyage-timeline__link-btn:hover {
  background: var(--color-btn-ghost-hover);
  color: var(--color-accent-text);
}

.voyage-timeline__link-icon {
  width: 1.125rem;
  height: 1.125rem;
}

.voyage-timeline :deep(.table-action-icon--subscribe-active) {
  color: var(--color-accent-text);
}

.voyage-timeline :deep(.table-action-icon--subscribe-active:hover:not(:disabled)) {
  background: rgb(70 72 212 / 0.1);
  color: var(--color-accent-text);
}

.voyage-timeline__empty {
  padding: 2.5rem 1rem;
  text-align: center;
  color: var(--color-muted);
}

.voyage-timeline__foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 1.25rem;
  background: rgb(70 72 212 / 0.04);
  border-top: 1px solid var(--color-list-divider);
}

.voyage-timeline__range {
  margin: 0;
  font-size: 0.75rem;
  color: var(--color-fg-secondary);
}

[data-theme='dark'] .voyage-status--success {
  color: rgb(110 231 183);
}

[data-theme='dark'] .voyage-status--planned {
  color: rgb(147 197 253);
}

[data-theme='dark'] .voyage-time--updated .voyage-time__current {
  color: rgb(253 186 116);
}
</style>
