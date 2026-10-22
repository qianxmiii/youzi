<script setup lang="ts">
import { ExternalLink, RefreshCw } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NDrawer, NDrawerContent, useMessage } from 'naive-ui'
import { computed, ref } from 'vue'
import { getShipment, syncShipmentsRouteStatusFromDps } from '@/api/shipments'
import ShipmentExceptionHistory from '@/components/shipments/ShipmentExceptionHistory.vue'
import ShipmentTrackingPanel from '@/components/shipments/ShipmentTrackingPanel.vue'
import ShipmentTrackingTimeReview from '@/components/shipments/ShipmentTrackingTimeReview.vue'
import VipStarBadge from '@/components/common/VipStarBadge.vue'
import {
  resolveShipmentListStatusDisplay,
  routeStatusLabelZh,
} from '@/constants/shipmentRouteStatus'
import {
  SHIPMENT_STATUS_LABEL_ZH,
  dpsPreportStatusBadgeClass,
  shipmentStatusLabel,
} from '@/constants/shipmentWorkspace'
import type { Shipment } from '@/types/shipment'
import { resolveLastMileTracking } from '@/utils/lastMileTracking'

const props = defineProps<{
  show: boolean
  shipment: Shipment | null
  initialTab?: 'internal' | 'carrier'
  exceptionLabelByCode?: Record<string, string>
  /** 码表中文名覆盖（如运单列表筛选项） */
  routeStatusLabelByCode?: Record<string, string>
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  'shipment-updated': [shipment: Shipment]
}>()

const message = useMessage()
const syncingRouteStatus = ref(false)

const showModel = computed({
  get: () => props.show,
  set: (v: boolean) => emit('update:show', v),
})

const coarseStatusLabel: Record<string, string> = { ...SHIPMENT_STATUS_LABEL_ZH }

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
  const s = props.shipment
  if (!s) return '—'
  const zh = s.carrierNameZh?.trim()
  if (zh) return zh
  return s.carrierCode?.trim() || '—'
})

/** 与运单列表状态列一致：粗状态已签收时不被「轨迹签收」顶替 */
const headerStatusDisplay = computed(() => {
  const s = props.shipment
  if (!s) return null
  return resolveShipmentListStatusDisplay({
    statusCode: s.statusCode,
    routeStatus: s.routeStatus,
    routeStatusLabelByCode: props.routeStatusLabelByCode,
    coarseStatusLabel,
  })
})

const headerStatusTitle = computed(() => {
  const s = props.shipment
  if (!s) return ''
  const tip = headerStatusDisplay.value?.tipExtra || ''
  const waybillHint = s.waybillId?.trim()
    ? `${tip}点击更新明细状态`
    : `${tip}无 DPS 运单 ID，需先更新运单`
  return syncingRouteStatus.value ? '正在更新明细状态…' : waybillHint
})

function openTrackUrl() {
  const url = transferNumber.value?.url
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function copyShipmentNo() {
  const sn = props.shipment?.shipmentNo?.trim()
  if (!sn) return
  try {
    await navigator.clipboard.writeText(sn)
    message.success('已复制运单号')
  } catch {
    message.error('复制失败')
  }
}

async function syncRouteStatus() {
  const s = props.shipment
  if (!s?.shipmentNo || syncingRouteStatus.value) return
  if (!s.waybillId?.trim()) {
    message.warning('无 DPS 运单 ID，请先在运单管理「更新选中运单」补全')
    return
  }
  syncingRouteStatus.value = true
  try {
    const res = await syncShipmentsRouteStatusFromDps([s.shipmentNo])
    const next = await getShipment(s.id)
    emit('shipment-updated', next)
    if (res.failed) {
      message.warning(res.errors?.[0] || '明细状态更新失败')
    } else if (res.missingWaybillId) {
      message.warning('无 DPS 运单 ID，请先更新运单')
    } else if (res.empty) {
      message.info('接口无轨迹节点')
    } else if (res.updated) {
      message.success(`明细状态已更新：${routeStatusLabelZh(next.routeStatus, props.routeStatusLabelByCode) || '—'}`)
    } else {
      message.success('明细状态无变化')
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '明细状态更新失败')
  } finally {
    syncingRouteStatus.value = false
  }
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
    <NDrawerContent closable :native-scrollbar="false" class="shipment-tracking-drawer-content">
      <template #header>
        <div v-if="shipment" class="drawer-header min-w-0">
          <div class="header-title-row">
            <button
              type="button"
              class="shipment-no shipment-no-copy-btn"
              :disabled="!shipment.shipmentNo?.trim()"
              title="点击复制运单号"
              :aria-label="`运单号 ${shipment.shipmentNo}，点击复制`"
              @click="copyShipmentNo"
            >
              {{ shipment.shipmentNo }}
            </button>
            <button
              v-if="headerStatusDisplay"
              type="button"
              class="route-status-btn"
              :class="[
                headerStatusDisplay.label !== '无明细状态'
                  ? ['shipment-status-badge', headerStatusDisplay.toneClass]
                  : 'route-status-btn--empty',
                { 'route-status-btn--loading': syncingRouteStatus },
              ]"
              :disabled="syncingRouteStatus"
              :title="headerStatusTitle"
              :aria-label="`状态 ${headerStatusDisplay.label}，点击更新明细`"
              @click="syncRouteStatus"
            >
              <RefreshCw
                v-if="syncingRouteStatus"
                class="route-status-btn__icon route-status-btn__icon--spin"
                :stroke-width="ICON_STROKE"
                aria-hidden="true"
              />
              {{ headerStatusDisplay.label }}
            </button>
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
              <ExternalLink class="link-icon" :stroke-width="ICON_STROKE" aria-hidden="true" />
            </button>
            <span v-else class="transfer-value">{{ transferNumber.number }}</span>
          </div>

          <div v-if="shipment.statusCode?.trim()" class="status-row">
            <span
              class="status-badge"
              :class="dpsPreportStatusBadgeClass(shipment.statusCode)"
            >
              {{ shipmentStatusLabel(shipment.statusCode) }}
            </span>
          </div>
        </div>
      </template>

      <div v-if="shipment" class="drawer-body">
        <section class="drawer-section meta-section">
          <dl class="meta-list">
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
            <div class="meta-item meta-item--split">
              <div class="meta-split-cell">
                <dt class="section-label">派送仓库</dt>
                <dd class="section-value">{{ shipment.addressCode?.trim() || '—' }}</dd>
              </div>
              <div class="meta-split-cell">
                <dt class="section-label">邮编</dt>
                <dd class="section-value drawer-yahei-bold">{{ shipment.zipcode?.trim() || '—' }}</dd>
              </div>
            </div>
          </dl>
        </section>

        <ShipmentExceptionHistory
          :shipment-id="shipment.id"
          :shipment="shipment"
          :label-by-code="exceptionLabelByCode"
          mode="drawer"
        />

        <section class="drawer-section timeline-section">
          <ShipmentTrackingTimeReview
            :key="shipment.id + '-' + shipment.updatedTime"
            :shipment="shipment"
            @updated="(row) => emit('shipment-updated', row)"
          />
          <ShipmentTrackingPanel
            :key="shipment.id + '-' + (initialTab || 'internal')"
            :shipment-id="shipment.id"
            :shipment="shipment"
            mode="drawer"
            :initial-tab="initialTab || 'internal'"
            @shipment-updated="(row) => emit('shipment-updated', row)"
          />
        </section>
      </div>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped>
.shipment-tracking-drawer :deep(.n-drawer-content) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.shipment-tracking-drawer :deep(.n-drawer-header) {
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid var(--color-border);
}

.shipment-tracking-drawer :deep(.n-drawer-body-content-wrapper),
.shipment-tracking-drawer :deep(.n-drawer-body) {
  padding: 0;
  flex: 1;
  min-height: 0;
  overflow: hidden;
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
  font-family: "Microsoft YaHei UI Bold", "MicrosoftYaHeiUI-Bold", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-size: 1.375rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
  color: var(--color-fg-emphasis);
}

.shipment-no-copy-btn {
  margin: 0;
  padding: 0;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: var(--color-accent-text, var(--color-fg-emphasis));
  max-width: 100%;
}

.shipment-no-copy-btn:hover:not(:disabled) {
  text-decoration: underline;
}

.shipment-no-copy-btn:disabled {
  cursor: default;
  color: var(--color-muted);
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

.route-status-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  flex-shrink: 0;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s ease, transform 0.12s ease;
}

.route-status-btn:hover:not(:disabled) {
  opacity: 0.88;
  transform: translateY(-1px);
}

.route-status-btn:disabled {
  cursor: wait;
  opacity: 0.75;
}

.route-status-btn--empty {
  border-radius: 0.25rem;
  padding: 0.2rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--tag-slate-fg);
  background: var(--tag-slate-bg);
}

.route-status-btn__icon {
  height: 0.75rem;
  width: 0.75rem;
  flex-shrink: 0;
}

.route-status-btn__icon--spin {
  animation: route-status-spin 0.8s linear infinite;
}

@keyframes route-status-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .route-status-btn {
    transition: none;
  }
  .route-status-btn:hover:not(:disabled) {
    transform: none;
  }
  .route-status-btn__icon--spin {
    animation: none;
  }
}

.shipment-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.2rem 0.5rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.25;
  white-space: nowrap;
}

.shipment-status-badge--default {
  color: var(--tag-default-fg);
  background: var(--tag-default-bg);
}
.shipment-status-badge--warning {
  color: var(--tag-warning-fg);
  background: var(--tag-warning-bg);
}
.shipment-status-badge--success {
  color: var(--tag-success-fg);
  background: var(--tag-success-bg);
}
.shipment-status-badge--error {
  color: var(--tag-error-fg);
  background: var(--tag-error-bg);
}
.shipment-status-badge--slate {
  color: var(--tag-slate-fg);
  background: var(--tag-slate-bg);
}
.shipment-status-badge--sky {
  color: var(--tag-sky-fg);
  background: var(--tag-sky-bg);
}
.shipment-status-badge--teal {
  color: var(--tag-teal-fg);
  background: var(--tag-teal-bg);
}
.shipment-status-badge--indigo {
  color: var(--tag-indigo-fg);
  background: var(--tag-indigo-bg);
}
.shipment-status-badge--violet {
  color: var(--tag-violet-fg);
  background: var(--tag-violet-bg);
}
.shipment-status-badge--cyan {
  color: var(--tag-cyan-fg);
  background: var(--tag-cyan-bg);
}
.shipment-status-badge--orange {
  color: var(--tag-orange-fg);
  background: var(--tag-orange-bg);
}
.shipment-status-badge--rose {
  color: var(--tag-rose-fg);
  background: var(--tag-rose-bg);
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

.drawer-yahei-bold {
  font-family: "Microsoft YaHei UI Bold", "MicrosoftYaHeiUI-Bold", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-weight: 700;
  letter-spacing: 0;
}

.timeline-section {
  padding-bottom: 1rem;
  border-bottom: none;
}
</style>
