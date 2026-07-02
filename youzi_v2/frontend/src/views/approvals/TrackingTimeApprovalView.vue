<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NDatePicker,
  NPagination,
  NSelect,
  NSpace,
  NTag,
  NTooltip,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { Copy } from 'lucide-vue-next'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getShipment, getShipmentFilterOptions, listPendingTrackingTimeReviews, reviewTrackingTimeCandidate } from '@/api/shipments'
import { buildCarrierSelectOptions } from '@/utils/carrierFilterOptions'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import TableActionIcon from '@/components/common/TableActionIcon.vue'
import { ICON_STROKE } from '@/constants/icons'
import type { Shipment } from '@/types/shipment'
import type { TrackingTimeCandidate, TrackingTimeReviewAction } from '@/types/trackingTimeWriteback'
import { formatSignedTimeReviewQuestion } from '@/types/trackingTimeWriteback'
import { formatAbsoluteDateTime } from '@/utils/formatDateTime'
import { usePendingTrackingTimeReviewCount } from '@/composables/usePendingTrackingTimeReviewCount'

const message = useMessage()
const router = useRouter()
const { refreshPendingTrackingTimeReviewCount } = usePendingTrackingTimeReviewCount()
const loading = ref(false)
const reviewingId = ref<string | null>(null)
const manualRowId = ref<string | null>(null)
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
  reviewingId.value = row.id
  try {
    await reviewTrackingTimeCandidate(row.id, { action, manualValue })
    const labels: Record<string, string> = {
      use_expected_delivery: '已采用预计送仓时间',
      use_signed_track: '已采用签收节点时间',
      manual: '已写入手动签收时间',
      reject: '已暂不处理',
    }
    message.success(labels[action] || '已处理')
    manualRowId.value = null
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

function submitManual(row: TrackingTimeCandidate) {
  if (manualAt.value == null) {
    message.warning('请选择签收时间')
    return
  }
  const d = new Date(manualAt.value)
  const pad = (n: number) => String(n).padStart(2, '0')
  const manualValue = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  void review(row, 'manual', manualValue)
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

const columns = computed<DataTableColumns<TrackingTimeCandidate>>(() => [
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
    render: (row) => carrierDisplayLabel(row),
  },
  {
    title: '推荐（预计送仓）',
    key: 'candidateValue',
    width: 148,
    render: (row) => formatTime(row.candidateValue),
  },
  {
    title: '对照（签收节点）',
    key: 'compareValue',
    width: 168,
    render: (row) => formatTime(row.compareValue),
  },
  {
    title: '当前签收',
    key: 'deliveredTime',
    width: 148,
    render: (row) => formatTime(row.deliveredTime),
  },
  {
    title: '审批问题',
    key: 'reviewQuestion',
    minWidth: 240,
    ellipsis: { tooltip: true },
    render: (row) => formatSignedTimeReviewQuestion(row.candidateValue),
  },
  {
    title: '预计送仓轨迹',
    key: 'sourceTrackDesc',
    minWidth: 200,
    ellipsis: { tooltip: true },
  },
  {
    title: '状态',
    key: 'reviewStatus',
    width: 96,
    render: () => h(NTag, { size: 'small', type: 'warning', bordered: false }, () => '待审批'),
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
    width: 320,
    fixed: 'right',
    render: (row) => {
      const busy = reviewingId.value === row.id
      const disabled = reviewingId.value != null && reviewingId.value !== row.id
      return h(NSpace, { size: 6, wrap: true }, () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              loading: busy,
              disabled,
              onClick: () => void review(row, 'use_expected_delivery'),
            },
            () => '采用预计送仓',
          ),
          h(
            NButton,
            {
              size: 'small',
              loading: busy,
              disabled,
              onClick: () => void review(row, 'use_signed_track'),
            },
            () => '签收节点',
          ),
          h(
            NButton,
            {
              size: 'small',
              loading: busy,
              disabled,
              onClick: () => {
                manualRowId.value = manualRowId.value === row.id ? null : row.id
                manualAt.value = null
              },
            },
            () => '手动',
          ),
          h(
            NButton,
            {
              size: 'small',
              loading: busy,
              disabled,
              onClick: () => void review(row, 'reject'),
            },
          () => '暂不处理',
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
  <div class="tracking-approval-page flex h-full min-h-0 w-full flex-col gap-4">
    <div class="flex shrink-0 flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="page-h2">轨迹审批</h2>
        <p class="mt-1 text-xs text-[var(--color-muted)]">
          签收节点与预计送仓日期不一致时，推荐采用预计送仓时间作为签收时间；也可选用签收节点或手动填写。
        </p>
      </div>
      <NButton size="small" :loading="loading" @click="load">刷新</NButton>
    </div>

    <article class="panel flex min-h-0 flex-1 flex-col overflow-hidden p-0">
      <div class="shrink-0 flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
        <div class="text-sm text-[var(--color-fg-secondary)]">
          待审批
          <span class="ml-1 font-semibold tabular-nums text-[var(--color-fg-emphasis)]">{{ total }}</span>
          条
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-[var(--color-muted)]">承运商</span>
          <NSelect
            v-model:value="filterCarrier"
            :options="carrierOptions"
            clearable
            filterable
            size="small"
            class="w-40"
            placeholder="全部"
          />
        </div>
      </div>

      <div
        v-if="manualRowId"
        class="flex shrink-0 flex-wrap items-end gap-3 border-b border-[var(--color-border)] px-4 py-3"
      >
        <div class="text-xs text-[var(--color-muted)]">手动填写签收时间</div>
        <NDatePicker
          v-model:value="manualAt"
          type="datetime"
          clearable
          size="small"
          format="yyyy-MM-dd HH:mm:ss"
        />
        <NButton
          size="small"
          type="primary"
          :loading="reviewingId === manualRowId"
          @click="submitManual(items.find((r) => r.id === manualRowId)!)"
        >
          确认写入
        </NButton>
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
          flex-height
          :loading="loading"
          class="tracking-approval-table h-full"
          :columns="columns"
          :data="items"
          :row-key="(row: TrackingTimeCandidate) => row.id"
          size="small"
          :scroll-x="1700"
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
