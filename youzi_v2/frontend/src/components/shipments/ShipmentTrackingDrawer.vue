<script setup lang="ts">
import { NDrawer } from 'naive-ui'
import { computed } from 'vue'
import ShipmentExceptionHistory from '@/components/shipments/ShipmentExceptionHistory.vue'
import ShipmentTrackingPanel from '@/components/shipments/ShipmentTrackingPanel.vue'
import VipStarBadge from '@/components/common/VipStarBadge.vue'
import type { Shipment } from '@/types/shipment'
import { resolveLastMileTracking } from '@/utils/lastMileTracking'

const props = defineProps<{
  show: boolean
  shipment: Shipment | null
  initialTab?: 'internal' | 'carrier'
  exceptionLabelByCode?: Record<string, string>
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
}>()

const showModel = computed({
  get: () => props.show,
  set: (v: boolean) => emit('update:show', v),
})

const statusLabel: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

const statusBadgeClass: Record<string, string> = {
  IN_TRANSIT: 'status-badge--transit',
  DELIVERED: 'status-badge--delivered',
  INSPECTION: 'status-badge--inspection',
  UNKNOWN: 'status-badge--unknown',
}

const lastMile = computed(() =>
  props.shipment ? resolveLastMileTracking(props.shipment) : null,
)

const transferNumber = computed(() => {
  const s = props.shipment
  if (!s) return null
  const fromLastMile = lastMile.value?.number?.trim()
  if (fromLastMile) return { number: fromLastMile, url: lastMile.value?.url ?? null }
  const tn = s.trackingNumber?.trim()
  if (tn) return { number: tn, url: null }
  return null
})

const packageCountText = computed(() => {
  const n = props.shipment?.ctns
  if (n == null) return '—'
  return n === 1 ? '1 Package' : String(n) + ' Packages'
})

const carrierText = computed(() => {
  const code = props.shipment?.carrierCode?.trim()
  return code || '—'
})

const statusCode = computed(() => props.shipment?.statusCode?.trim().toUpperCase() || '')

function openTrackUrl() {
  const url = transferNumber.value?.url
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <NDrawer
    v-model:show="showModel"
    :width="520"
    placement="right"
    :auto-focus="false"
    class="shipment-tracking-drawer"
  >
    <template #header>
      <div v-if="shipment" class="drawer-header min-w-0 pr-8">
        <div class="header-title-row">
          <h2 class="shipment-no">
            {{ shipment.shipmentNo }}
          </h2>
          <VipStarBadge v-if="shipment.isVip" size="md" />
        </div>

        <div v-if="transferNumber" class="transfer-row">
          <span class="transfer-label">转单号:</span>
          <button
            v-if="transferNumber.url"
            type="button"
            class="tracking-link tracking-link--clickable inline-flex items-center gap-1"
            @click="openTrackUrl"
          >
            {{ transferNumber.number }}
            <svg viewBox="0 0 16 16" fill="none" class="link-icon" aria-hidden="true">
              <path
                d="M6.5 3.5H12.5V9.5M12.5 3.5 3.5 12.5"
                stroke="currentColor"
                stroke-width="1.25"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
          <span v-else class="transfer-value">{{ transferNumber.number }}</span>
        </div>

        <div v-if="statusCode" class="status-row">
          <span
            class="status-badge"
            :class="statusBadgeClass[statusCode] || 'status-badge--unknown'"
          >
            {{ statusLabel[statusCode] || shipment.statusCode }}
          </span>
        </div>
      </div>
    </template>

    <div v-if="shipment" class="drawer-body">
      <section class="drawer-section meta-section">
        <dl class="meta-list">
          <div class="meta-item">
            <dt class="section-label">Shipment No</dt>
            <dd class="section-value meta-mono">{{ shipment.shipmentNo || '—' }}</dd>
          </div>
          <div class="meta-item">
            <dt class="section-label">Tracking Number</dt>
            <dd class="section-value">
              <button
                v-if="transferNumber?.url"
                type="button"
                class="tracking-link tracking-link--clickable inline-flex items-center gap-1"
                @click="openTrackUrl"
              >
                {{ transferNumber.number }}
                <svg viewBox="0 0 16 16" fill="none" class="link-icon" aria-hidden="true">
                  <path
                    d="M6.5 3.5H12.5V9.5M12.5 3.5 3.5 12.5"
                    stroke="currentColor"
                    stroke-width="1.25"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
              <span v-else-if="transferNumber" class="meta-mono">{{ transferNumber.number }}</span>
              <span v-else class="meta-empty">—</span>
            </dd>
          </div>
          <div class="meta-item meta-item--split">
            <div class="meta-split-cell">
              <dt class="section-label">Package Count</dt>
              <dd class="section-value">{{ packageCountText }}</dd>
            </div>
            <div class="meta-split-cell">
              <dt class="section-label">承运商</dt>
              <dd class="section-value meta-carrier">{{ carrierText }}</dd>
            </div>
          </div>
        </dl>
      </section>

      <section class="drawer-section timeline-section">
        <ShipmentTrackingPanel
          :key="shipment.id + '-' + (initialTab || 'internal')"
          :shipment-id="shipment.id"
          :shipment="shipment"
          mode="drawer"
          :initial-tab="initialTab || 'internal'"
        />
      </section>

      <ShipmentExceptionHistory
        :shipment-id="shipment.id"
        :shipment="shipment"
        :label-by-code="exceptionLabelByCode"
        mode="drawer"
      />
    </div>
  </NDrawer>
</template>

<style scoped>
.shipment-tracking-drawer :deep(.n-drawer-header) {
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid var(--color-border);
}

.shipment-tracking-drawer :deep(.n-drawer-body-content-wrapper) {
  padding: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.shipment-tracking-drawer :deep(.n-drawer-header__close) {
  top: 1.25rem;
  right: 1rem;
}

.drawer-header {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.header-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.shipment-no {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: var(--color-fg-emphasis);
}

.transfer-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.875rem;
  line-height: 1.4;
}

.transfer-label {
  color: var(--color-muted);
}

.transfer-value {
  font-weight: 500;
  color: var(--color-fg);
}

.status-row {
  display: flex;
  align-items: center;
  padding-top: 0.125rem;
}

.link-icon {
  height: 0.875rem;
  width: 0.875rem;
  flex-shrink: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  padding: 0.1875rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.25;
}

.status-badge--transit {
  background: rgb(219 234 254);
  color: rgb(29 78 216);
}

.status-badge--delivered {
  background: rgb(220 252 231);
  color: rgb(21 128 61);
}

.status-badge--inspection {
  background: rgb(254 243 199);
  color: rgb(180 83 9);
}

.status-badge--unknown {
  background: var(--color-btn-ghost-bg);
  color: var(--color-muted);
}

[data-theme='dark'] .status-badge--transit {
  background: rgb(30 58 138 / 0.45);
  color: rgb(147 197 253);
}

[data-theme='dark'] .status-badge--delivered {
  background: rgb(20 83 45 / 0.4);
  color: rgb(134 239 172);
}

[data-theme='dark'] .status-badge--inspection {
  background: rgb(120 53 15 / 0.4);
  color: rgb(253 230 138);
}

.tracking-link {
  font-weight: 500;
  color: rgb(37 99 235);
}

[data-theme='dark'] .tracking-link {
  color: rgb(96 165 250);
}

.tracking-link--clickable {
  cursor: pointer;
}

.tracking-link--clickable:hover {
  text-decoration: underline;
}

.tracking-link:disabled {
  cursor: default;
  opacity: 0.85;
}

.drawer-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 1.25rem 1.5rem;
}

.drawer-section {
  border-bottom: 1px solid var(--color-border);
  padding: 1.125rem 0 1.25rem;
}

.section-label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.meta-list {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.meta-item {
  margin: 0;
}

.meta-item dd {
  margin: 0;
}

.meta-item--split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.5rem;
}

.meta-split-cell {
  min-width: 0;
}

.meta-carrier {
  word-break: break-word;
}

.section-value {
  margin-top: 0.375rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-fg-emphasis);
}

.meta-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  letter-spacing: -0.01em;
}

.meta-empty {
  color: var(--color-muted);
  font-weight: 500;
}

.timeline-section {
  padding-bottom: 1rem;
  border-bottom: none;
}
</style>
