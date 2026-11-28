<script setup lang="ts">
import { carrierVisible, displayCarrier } from '@/composables/useCarrierPrivacy'
import {
  NButton,
  NDataTable,
  NDatePicker,
  NDropdown,
  NModal,
  NPagination,
  NSelect,
  NSpace,
  NTooltip,
  useDialog,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { Copy } from 'lucide-vue-next'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getShipment, getShipmentFilterOptions, listPendingTrackingTimeReviews, reviewTrackingTimeCandidate, batchReviewTrackingTimeCandidates } from '@/api/shipments'
import { buildCarrierSelectOptions } from '@/utils/carrierFilterOptions'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import TableActionIcon from '@/components/common/TableActionIcon.vue'
import { ICON_STROKE } from '@/constants/icons'
import type { Shipment } from '@/types/shipment'
import type { TrackingTimeCandidate, TrackingTimeReviewAction } from '@/types/trackingTimeWriteback'
import { formatAbsoluteDateTime, formatDateYmd, formatTimestampForApi } from '@/utils/formatDateTime'
import { usePendingTrackingTimeReviewCount } from '@/composables/usePendingTrackingTimeReviewCount'

const message = useMessage()
const dialog = useDialog()
const router = useRouter()
const { refreshPendingTrackingTimeReviewCount } = usePendingTrackingTimeReviewCount()
const loading = ref(false)
const reviewingId = ref<string | null>(null)
const batching = ref<'use_expected_delivery' | 'use_signed_track' | 'reject' | null>(null)
const checkedRowKeys = ref<string[]>([])
const manualRow = ref<TrackingTimeCandidate | null>(null)
const manualAt = ref<number | null>(null)
const items = ref<TrackingTimeCandidate[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const error = ref('')
const trackingDrawerShow = ref(false)
const trackingDrawerShipment = ref<Shipment | null>(null)
const trackingDrawerTab = ref<'internal' | 'carrier'>('carrier')
const exceptionLabelByCode = ref<Record<string, string>>({})
const filterCarrier = ref<string | null>(null)
const carrierOptions = ref<{ label: string; value: string }[]>([])

function formatTime(value: string | null | undefined) {
  const text = (value || '').trim()
  if (!text) return '—'
  return formatAbsoluteDateTime(text) || text
}

function renderDateWithTime(value: string | null | undefined) {
  if (!value?.trim()) return '—'
  return h(NTooltip, { trigger: 'hover' }, {
    trigger: () => h('span', {
      class: 'whitespace-nowrap tabular-nums',
      'aria-label': formatTime(value),
    }, formatDateYmd(value)),
    default: () => formatTime(value),
  })
}

function dateDifference(row: TrackingTimeCandidate) {
  const days = (Date.parse(formatDateYmd(row.compareValue)) - Date.parse(formatDateYmd(row.candidateValue))) / 86_400_000
  if (!Number.isFinite(days)) return '—'
  if (days === 0) return '同一天'
  return `签收${days > 0 ? '晚' : '早'} ${Math.abs(days)} 天`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await listPendingTrackingTimeReviews({
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
      carrierCode: filterCarrier.value || undefined,
    })
    items.value = res.items
    total.value = res.total
    const visible = new Set(res.items.map((row) => row.id))
    checkedRowKeys.value = checkedRowKeys.value.filter((id) => visible.has(id))
    await refreshPendingTrackingTimeReviewCount()
  } catch (e) {
    items.value = []
    total.value = 0
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function review(row: TrackingTimeCandidate, action: TrackingTimeReviewAction, manualValue?: string) {
  if (reviewingId.value || batching.value) return
  reviewingId.value = row.id
  try {
    await reviewTrackingTimeCandidate(row.id, { action, manualValue })
    const labels: Record<string, string> = {
      use_expected_delivery: '已采用预计送仓时间',
      use_signed_track: '已采用签收节点时间',
      manual: '已写入手动签收时间',
      reject: '已保留当前签收',
    }
    message.success(labels[action] || '已处理')
    manualRow.value = null
    manualAt.value = null
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '审批失败')
  } finally {
    reviewingId.value = null
  }
}

const batchLabels = {
  use_expected_delivery: '采用预计送仓',
  use_signed_track: '采用签收节点',
  reject: '保留当前签收',
}

function confirmBatchReview(action: keyof typeof batchLabels) {
  const ids = checkedRowKeys.value.filter(Boolean)
  if (!ids.length || batching.value || reviewingId.value) return
  dialog.warning({
    title: '批量审批',
    content: `为选中的 ${ids.length} 票${batchLabels[action]}？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: () => batchReview(action, ids),
  })
}

async function batchReview(action: keyof typeof batchLabels, ids: string[]) {
  if (batching.value || reviewingId.value) return
  batching.value = action
  try {
    const res = await batchReviewTrackingTimeCandidates({ ids, action })
    if (res.failed) {
      message.warning(`${batchLabels[action]}完成 ${res.ok} 条，失败 ${res.failed} 条`)
    } else {
      message.success(`已${batchLabels[action]} ${res.ok} 条`)
    }
    checkedRowKeys.value = []
    if (items.value.length <= ids.length && page.value > 1) {
      page.value -= 1
    }
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量审批失败')
  } finally {
    batching.value = null
  }
}

function submitManual() {
  const row = manualRow.value
  if (!row) return
  if (manualAt.value == null) {
    message.warning('请选择签收时间')
    return
  }
  void review(row, 'manual', formatTimestampForApi(manualAt.value))
}

function shipmentStub(row: TrackingTimeCandidate): Shipment {
  return {
    id: row.shipmentId,
    shipmentNo: row.shipmentNo || '',
    deliveredTime: row.deliveredTime ?? null,
    expectedDeliveryTime: row.expectedDeliveryTime ?? null,
    trackingLogCount: 0,
    carrierLogCount: 0,
    createdTime: row.createdTime || '',
    updatedTime: row.updatedTime || '',
  } as Shipment
}

async function openTrackingDrawer(row: TrackingTimeCandidate, tab: 'internal' | 'carrier' = 'carrier') {
  const sid = row.shipmentId?.trim()
  if (!sid) {
    message.warning('缺少运单 ID')
    return
  }
  trackingDrawerTab.value = tab
  trackingDrawerShow.value = true
  trackingDrawerShipment.value = shipmentStub(row)
  try {
    trackingDrawerShipment.value = await getShipment(sid)
  } catch {
    /* 列表行数据兜底 */
  }
}

function handleTrackingDrawerShipmentUpdated(row: Shipment) {
  trackingDrawerShipment.value = row
  void load()
}

function openShipmentList(row: TrackingTimeCandidate) {
  const sn = row.shipmentNo?.trim()
  if (!sn) return
  void router.push({ path: '/shipments', query: { shipmentNo: sn } })
}

async function copyShipmentNo(row: TrackingTimeCandidate) {
  const sn = row.shipmentNo?.trim()
  if (!sn) return
  try {
    await navigator.clipboard.writeText(sn)
    message.success('已复制运单号')
  } catch {
    message.error('复制失败')
  }
}

function renderShipmentNoCell(row: TrackingTimeCandidate) {
  const sn = row.shipmentNo || '—'
  return h('span', { class: 'tracking-approval-shipment-no' }, [
    h(
      NButton,
      {
        text: true,
        type: 'primary',
        size: 'small',
        class: 'font-mono',
        onClick: () => openShipmentList(row),
      },
      () => sn,
    ),
    row.shipmentNo
      ? h(
          NTooltip,
          { trigger: 'hover', showArrow: false },
          {
            trigger: () =>
              h(
                'button',
                {
                  type: 'button',
                  class: 'tracking-approval-copy-btn',
                  'aria-label': '复制运单号',
                  onClick: (e: MouseEvent) => {
                    e.stopPropagation()
                    void copyShipmentNo(row)
                  },
                },
                [
                  h(Copy, {
                    class: 'h-3.5 w-3.5',
                    strokeWidth: ICON_STROKE,
                    'aria-hidden': 'true',
                  }),
                ],
              ),
            default: () => '复制运单号',
          },
        )
      : null,
  ])
}

function renderTrackingAction(row: TrackingTimeCandidate) {
  return h(
    NTooltip,
    { trigger: 'hover', showArrow: false },
    {
      trigger: () =>
        h(TableActionIcon, {
          kind: 'view',
          title: '轨迹',
          onClick: () => void openTrackingDrawer(row, 'carrier'),
        }),
      default: () => '轨迹',
    },
  )
}

function carrierDisplayLabel(row: TrackingTimeCandidate): string {
  const zh = row.carrierNameZh?.trim()
  if (zh) return zh
  return row.carrierCode?.trim() || '—'
}

const reviewOptions = [
  { label: '手动填写', key: 'manual' },
  { label: '保留当前签收', key: 'reject' },
]

function selectReviewOption(row: TrackingTimeCandidate, key: string | number) {
  if (key === 'manual') {
    manualAt.value = null
    manualRow.value = row
  } else if (key === 'reject') {
    void review(row, 'reject')
  }
}

const columns = computed<DataTableColumns<TrackingTimeCandidate>>(() => [
  { type: 'selection', fixed: 'left', width: 40 },
  {
    title: '运单号',
    key: 'shipmentNo',
    width: 172,
    fixed: 'left',
    render: (row) => renderShipmentNoCell(row),
  },
  {
    title: '承运商',
    key: 'carrierNameZh',
    width: 112,
    ellipsis: { tooltip: true },
    render: (row) => displayCarrier(carrierDisplayLabel(row)),
  },
  {
    title: '预计送仓（推荐）',
    key: 'candidateValue',
    width: 124,
    render: (row) => renderDateWithTime(row.candidateValue),
  },
  {
    title: '签收节点',
    key: 'compareValue',
    width: 112,
    render: (row) => renderDateWithTime(row.compareValue),
  },
  {
    title: '当前签收',
    key: 'deliveredTime',
    width: 112,
    render: (row) => renderDateWithTime(row.deliveredTime),
  },
  {
    title: '日期差',
    key: 'dateDifference',
    width: 108,
    render: dateDifference,
  },
  {
    title: '轨迹',
    key: 'tracking',
    width: 56,
    fixed: 'right',
    align: 'center',
    render: (row) => renderTrackingAction(row),
  },
  {
    title: '操作',
    key: 'actions',
    width: 204,
    fixed: 'right',
    render: (row) => {
      const busy = reviewingId.value === row.id
      const disabled = batching.value != null || reviewingId.value != null
      return h(NSpace, { size: 4, wrap: false }, () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              loading: busy,
              disabled,
              onClick: () => void review(row, 'use_expected_delivery'),
            },
            () => '用预计',
          ),
          h(
            NButton,
            {
              size: 'small',
              loading: busy,
              disabled: disabled || !row.compareValue?.trim(),
              onClick: () => void review(row, 'use_signed_track'),
            },
            () => '用节点',
          ),
          h(
            NDropdown,
            { trigger: 'click', options: reviewOptions, disabled, onSelect: (key) => selectReviewOption(row, key) },
            { default: () => h(NButton, { size: 'small', quaternary: true, disabled }, () => '更多') },
          ),
      ])
    },
  },
])

watch([page, pageSize], () => {
  void load()
})

watch(filterCarrier, () => {
  page.value = 1
  void load()
})

onMounted(() => {
  void load()
  void getShipmentFilterOptions()
    .then((opts) => {
      carrierOptions.value = buildCarrierSelectOptions(opts.carriers, opts.carrierCodes)
      const m: Record<string, string> = {}
      for (const t of opts.exceptionTypes) {
        m[t.code] = t.nameZh
      }
      exceptionLabelByCode.value = m
    })
    .catch(() => {
      /* 异常类型标签可选 */
    })
})
</script>

<template>
  <div class="tracking-approval-page flex h-full min-h-0 w-full flex-col gap-2">
    <div class="flex shrink-0 flex-wrap items-center justify-between gap-x-3 gap-y-2">
      <div class="flex items-center gap-3">
        <h2 class="page-h2">轨迹审批</h2>
        <span class="text-sm tabular-nums text-[var(--color-fg-secondary)]">待审批 {{ total }} 票</span>
      </div>
      <div class="tracking-approval-filters" :class="{ 'tracking-approval-filters--masked': !carrierVisible }">
        <span class="text-xs text-[var(--color-muted)]">承运商</span>
        <span v-if="!carrierVisible">***</span>
        <NSelect
          v-else
          v-model:value="filterCarrier"
          :options="carrierOptions"
          clearable
          filterable
          size="small"
          class="min-w-0"
          placeholder="全部"
          aria-label="承运商筛选"
        />
        <NButton size="small" :loading="loading" @click="load">刷新</NButton>
      </div>
    </div>

    <article class="panel flex min-h-0 flex-1 flex-col overflow-hidden p-0">
      <div
        v-if="checkedRowKeys.length"
        class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border)] px-4 py-2"
      >
        <span class="text-sm text-[var(--color-fg-secondary)]">
          已选
          <span class="font-semibold tabular-nums text-[var(--color-fg-emphasis)]">{{ checkedRowKeys.length }}</span>
          条
        </span>
        <NSpace size="small">
          <NButton
            size="small"
            type="primary"
            :loading="batching === 'use_expected_delivery'"
            :disabled="batching != null || reviewingId != null"
            @click="confirmBatchReview('use_expected_delivery')"
          >
            采用预计送仓
          </NButton>
          <NButton
            size="small"
            :loading="batching === 'use_signed_track'"
            :disabled="batching != null || reviewingId != null"
            @click="confirmBatchReview('use_signed_track')"
          >
            签收节点
          </NButton>
          <NButton
            size="small"
            :loading="batching === 'reject'"
            :disabled="batching != null || reviewingId != null"
            @click="confirmBatchReview('reject')"
          >
            保留当前签收
          </NButton>
          <NButton size="small" quaternary :disabled="batching != null" @click="checkedRowKeys = []">
            取消选择
          </NButton>
        </NSpace>
      </div>

      <div v-if="error" class="shrink-0 px-4 py-8 text-sm text-red-400">{{ error }}</div>
      <div
        v-else-if="!total && !loading"
        class="shrink-0 px-4 py-12 text-center text-sm text-[var(--color-muted)]"
      >
        暂无待审批的签收时间
      </div>
      <div v-else class="tracking-approval-table-wrap min-h-0 flex-1 overflow-hidden">
        <NDataTable
          v-model:checked-row-keys="checkedRowKeys"
          flex-height
          :loading="loading"
          class="tracking-approval-table h-full"
          :columns="columns"
          :data="items"
          :row-key="(row: TrackingTimeCandidate) => row.id"
          size="small"
          :scroll-x="1040"
          :bordered="false"
        />
      </div>

      <div
        v-if="total > 0"
        class="shrink-0 flex justify-end border-t border-[var(--color-border)] px-4 py-3"
      >
        <NPagination
          v-model:page="page"
          v-model:page-size="pageSize"
          :item-count="total"
          :page-sizes="[20, 50, 100, 200]"
          show-size-picker
          size="small"
        />
      </div>
    </article>

    <NModal
      :show="manualRow !== null"
      preset="card"
      :title="manualRow?.shipmentNo ? `填写签收时间 · ${manualRow.shipmentNo}` : '填写签收时间'"
      class="w-[min(460px,calc(100vw-2rem))]"
      :mask-closable="false"
      :closable="reviewingId === null"
      :close-on-esc="reviewingId === null"
      @update:show="show => { if (!show && !reviewingId) manualRow = null }"
    >
      <div v-if="manualRow" class="space-y-3">
        <dl class="grid grid-cols-2 gap-2 text-sm tabular-nums">
          <div><dt class="text-[var(--color-muted)]">预计送仓</dt><dd>{{ formatTime(manualRow.candidateValue) }}</dd></div>
          <div><dt class="text-[var(--color-muted)]">签收节点</dt><dd>{{ formatTime(manualRow.compareValue) }}</dd></div>
        </dl>
        <NDatePicker v-model:value="manualAt" type="datetime" clearable format="yyyy-MM-dd HH:mm:ss" />
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton :disabled="reviewingId !== null" @click="manualRow = null">取消</NButton>
          <NButton type="primary" :disabled="manualAt == null" :loading="reviewingId !== null" @click="submitManual">确认写入</NButton>
        </NSpace>
      </template>
    </NModal>

    <ShipmentTrackingDrawer
      v-model:show="trackingDrawerShow"
      :shipment="trackingDrawerShipment"
      :initial-tab="trackingDrawerTab"
      :exception-label-by-code="exceptionLabelByCode"
      @shipment-updated="handleTrackingDrawerShipmentUpdated"
    />
  </div>
</template>

<style scoped>
.tracking-approval-filters {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr) max-content;
  align-items: center;
  gap: 0.5rem;
  width: min(100%, 17rem);
}

.tracking-approval-filters--masked {
  grid-template-columns: repeat(3, max-content);
  width: auto;
}

.tracking-approval-table-wrap {
  min-height: 200px;
}

.tracking-approval-table :deep(.n-data-table-th) {
  font-size: 12px;
}

.tracking-approval-table :deep(.n-data-table-wrapper) {
  height: 100%;
}

.tracking-approval-table :deep(.tracking-approval-shipment-no) {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  max-width: 100%;
}

.tracking-approval-table :deep(.tracking-approval-copy-btn) {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  border-radius: 0.375rem;
  padding: 0;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
}

.tracking-approval-table :deep(.tracking-approval-copy-btn:hover) {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg);
}
</style>
