<script setup lang="ts">
import {
  NAlert,
  NButton,
  NDataTable,
  NDatePicker,
  NInput,
  NPagination,
  NSelect,
  NSpin,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  type DataTableColumns,
  type DataTableSortState,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getShipmentFilterOptions } from '@/api/shipments'
import { buildCarrierSelectOptions } from '@/utils/carrierFilterOptions'
import {
  exportShipmentPerformanceCsv,
  formatPerformanceDays,
  formatPerformanceMetric,
  formatPerformanceRate,
  getShipmentPerformanceAnalysis,
  getShipmentPerformanceDetails,
  type PerformanceCarrierChannelRow,
  type PerformanceGroupRow,
  type PerformanceMetricBlock,
  type ShipmentPerformanceAnalysis,
  type ShipmentPerformanceDetailRow,
  type ShipmentPerformanceQueryParams,
} from '@/api/statistics'
import { formatDateYmd } from '@/utils/formatDateTime'

const message = useMessage()
const router = useRouter()

type TabKey = 'overview' | 'channel' | 'carrier' | 'customer' | 'details'

const activeTab = ref<TabKey>('overview')
const loading = ref(false)
const exporting = ref(false)
const loadingDetails = ref(false)
const error = ref('')
const truncated = ref(false)

const analysis = ref<ShipmentPerformanceAnalysis | null>(null)
const detailItems = ref<ShipmentPerformanceDetailRow[]>([])
const detailTotal = ref(0)
const detailPage = ref(1)
const detailPageSize = ref(50)
const detailSortBy = ref('fullTransitDays')
const detailSortOrder = ref<'asc' | 'desc'>('desc')
const detailsTruncated = ref(false)

const dateFromTs = ref<number | null>(null)
const dateToTs = ref<number | null>(null)
const dateBasis = ref<ShipmentPerformanceQueryParams['dateBasis']>('atd')
const channelCode = ref<string | null>(null)
const carrierCode = ref<string | null>(null)
const customer = ref<string | null>(null)
const destinationPortCode = ref('')

const channelOptions = ref<{ label: string; value: string }[]>([])
const carrierOptions = ref<{ label: string; value: string }[]>([])
const customerOptions = ref<{ label: string; value: string }[]>([])

const dateBasisOptions = [
  { label: '按实际离港 (ATD)', value: 'atd' },
  { label: '按实际到港 (ATA)', value: 'ata' },
  { label: '按签收时间', value: 'signed_time' },
  { label: '按创建时间', value: 'created_time' },
]

function tsToDateFilter(ts: number | null): string | undefined {
  if (ts == null) return undefined
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function buildQueryParams(): ShipmentPerformanceQueryParams {
  return {
    dateFrom: tsToDateFilter(dateFromTs.value),
    dateTo: tsToDateFilter(dateToTs.value),
    dateBasis: dateBasis.value,
    channelCode: channelCode.value || undefined,
    carrierCode: carrierCode.value || undefined,
    customer: customer.value || undefined,
    destinationPortCode: destinationPortCode.value.trim() || undefined,
  }
}

function resetFilters() {
  dateFromTs.value = null
  dateToTs.value = null
  dateBasis.value = 'atd'
  channelCode.value = null
  carrierCode.value = null
  customer.value = null
  destinationPortCode.value = ''
}

function metricCell(block: PerformanceMetricBlock, analyzedCount?: number) {
  return formatPerformanceMetric(block, analyzedCount)
}

function pctCell(rate: number) {
  return formatPerformanceRate(rate)
}

function goShipment(no: string | null | undefined) {
  const sn = (no || '').trim()
  if (!sn) return
  void router.push({ path: '/shipments', query: { shipmentNo: sn } })
}

function extremeTransitCell(
  days: number | null | undefined,
  shipmentNo: string | null | undefined,
) {
  if (days == null) return '—'
  if (!shipmentNo) return formatPerformanceDays(days)
  return h('div', { class: 'flex flex-col items-end gap-0.5 leading-tight' }, [
    h('span', { class: 'tabular-nums' }, formatPerformanceDays(days)),
    h(
      'button',
      {
        type: 'button',
        class: 'max-w-[120px] truncate text-violet-400 hover:underline',
        title: shipmentNo,
        onClick: () => goShipment(shipmentNo),
      },
      shipmentNo,
    ),
  ])
}

function groupColumns(
  analyzedCount: number,
  nameTitle: string,
  showSignedRate = true,
): DataTableColumns<PerformanceGroupRow> {
  const cols: DataTableColumns<PerformanceGroupRow> = [
    { title: nameTitle, key: 'label', minWidth: 120, ellipsis: { tooltip: true } },
    { title: '总票数', key: 'totalCount', width: 88, align: 'right' },
    { title: '已签收', key: 'signedCount', width: 88, align: 'right' },
  ]
  if (showSignedRate) {
    cols.push({
      title: '签收完成率',
      key: 'signedRate',
      width: 100,
      align: 'right',
      render: (row) => pctCell(row.signedRate),
    })
  }
  cols.push(
    {
      title: '平均海运时效',
      key: 'seaTransit',
      minWidth: 130,
      render: (row) => metricCell(row.seaTransit, analyzedCount),
    },
    {
      title: '平均到港后送仓',
      key: 'postArrival',
      minWidth: 140,
      render: (row) => metricCell(row.postArrival, analyzedCount),
    },
    {
      title: '平均全程时效',
      key: 'fullTransit',
      minWidth: 130,
      render: (row) => metricCell(row.fullTransit, analyzedCount),
    },
    {
      title: 'P50 全程',
      key: 'p50',
      width: 88,
      align: 'right',
      render: (row) => formatPerformanceDays(row.fullTransit.p50Days),
    },
    {
      title: 'P90 全程',
      key: 'p90',
      width: 88,
      align: 'right',
      render: (row) => formatPerformanceDays(row.fullTransit.p90Days),
    },
    {
      title: '最快签收',
      key: 'fastestSigned',
      minWidth: 130,
      render: (row) => extremeTransitCell(row.fullTransit.minDays, row.fastestShipmentNo),
    },
    {
      title: '最慢签收',
      key: 'slowestSigned',
      minWidth: 130,
      render: (row) => extremeTransitCell(row.fullTransit.maxDays, row.slowestShipmentNo),
    },
    {
      title: '平均送仓偏差',
      key: 'deliveryDeviation',
      minWidth: 130,
      render: (row) => metricCell(row.deliveryDeviation, analyzedCount),
    },
    {
      title: '异常票',
      key: 'anomalyCount',
      width: 80,
      align: 'right',
    },
    {
      title: '异常率',
      key: 'anomalyRate',
      width: 88,
      align: 'right',
      render: (row) => pctCell(row.anomalyRate),
    },
  )
  return cols
}

const channelColumns = computed(() => groupColumns(analysis.value?.analyzedCount ?? 0, '渠道', true))

const carrierColumns = computed(() => groupColumns(analysis.value?.analyzedCount ?? 0, '承运商', false))

const customerColumns = computed((): DataTableColumns<PerformanceGroupRow> => {
  const analyzed = analysis.value?.analyzedCount ?? 0
  return [
    { title: '客户', key: 'label', minWidth: 120, ellipsis: { tooltip: true } },
    { title: '总票数', key: 'totalCount', width: 88, align: 'right' },
    { title: '已签收', key: 'signedCount', width: 88, align: 'right' },
    {
      title: '签收完成率',
      key: 'signedRate',
      width: 100,
      align: 'right',
      render: (row) => pctCell(row.signedRate),
    },
    {
      title: '平均全程时效',
      key: 'fullTransit',
      minWidth: 130,
      render: (row) => metricCell(row.fullTransit, analyzed),
    },
    {
      title: 'P90 全程',
      key: 'p90',
      width: 88,
      align: 'right',
      render: (row) => formatPerformanceDays(row.fullTransit.p90Days),
    },
    {
      title: '平均送仓偏差',
      key: 'deliveryDeviation',
      minWidth: 130,
      render: (row) => metricCell(row.deliveryDeviation, analyzed),
    },
    { title: '异常票', key: 'anomalyCount', width: 80, align: 'right' },
    {
      title: '最快签收',
      key: 'fastestSigned',
      minWidth: 130,
      render: (row) => extremeTransitCell(row.fullTransit.minDays, row.fastestShipmentNo),
    },
    {
      title: '最慢签收',
      key: 'slowestSigned',
      minWidth: 130,
      render: (row) => extremeTransitCell(row.fullTransit.maxDays, row.slowestShipmentNo),
    },
  ]
})

const carrierChannelColumns: DataTableColumns<PerformanceCarrierChannelRow> = [
  { title: '承运商', key: 'carrierCode', minWidth: 100 },
  { title: '渠道', key: 'channelCode', minWidth: 100 },
  { title: '总票数', key: 'totalCount', width: 88, align: 'right' },
  { title: '已签收', key: 'signedCount', width: 88, align: 'right' },
  {
    title: '平均海运时效',
    key: 'seaTransit',
    minWidth: 120,
    render: (row) => metricCell(row.seaTransit),
  },
  {
    title: '平均全程时效',
    key: 'fullTransit',
    minWidth: 120,
    render: (row) => metricCell(row.fullTransit),
  },
  {
    title: 'P50',
    key: 'p50',
    width: 72,
    align: 'right',
    render: (row) => formatPerformanceDays(row.fullTransit.p50Days),
  },
  {
    title: 'P90',
    key: 'p90',
    width: 72,
    align: 'right',
    render: (row) => formatPerformanceDays(row.fullTransit.p90Days),
  },
  {
    title: '最快签收',
    key: 'minDays',
    width: 96,
    align: 'right',
    render: (row) => formatPerformanceDays(row.fullTransit.minDays),
  },
  {
    title: '最慢签收',
    key: 'maxDays',
    width: 96,
    align: 'right',
    render: (row) => formatPerformanceDays(row.fullTransit.maxDays),
  },
  {
    title: '异常率',
    key: 'anomalyRate',
    width: 88,
    align: 'right',
    render: (row) => pctCell(row.anomalyRate),
  },
]

const detailColumns: DataTableColumns<ShipmentPerformanceDetailRow> = [
  {
    title: '运单号',
    key: 'shipmentNo',
    minWidth: 130,
    sorter: true,
    render: (row) =>
      h(
        'button',
        {
          type: 'button',
          class: 'text-violet-400 hover:underline',
          onClick: () => goShipment(row.shipmentNo),
        },
        row.shipmentNo,
      ),
  },
  { title: '客户', key: 'customer', minWidth: 100, ellipsis: { tooltip: true } },
  { title: '渠道', key: 'channelCode', width: 100 },
  { title: '承运商', key: 'carrierCode', width: 100 },
  { title: '目的港', key: 'destinationPortCode', width: 88 },
  { title: 'ETD', key: 'etd', width: 100, render: (row) => formatDateYmd(row.etd) },
  { title: 'ATD', key: 'atd', width: 100, render: (row) => formatDateYmd(row.atd) },
  { title: 'ETA', key: 'eta', width: 100, render: (row) => formatDateYmd(row.eta) },
  { title: 'ATA', key: 'ata', width: 100, render: (row) => formatDateYmd(row.ata) },
  {
    title: '预计送仓',
    key: 'expectedDeliveryTime',
    width: 100,
    render: (row) => formatDateYmd(row.expectedDeliveryTime),
  },
  {
    title: '签收时间',
    key: 'signedTime',
    width: 100,
    sorter: true,
    render: (row) => formatDateYmd(row.signedTime),
  },
  {
    title: '海运时效',
    key: 'seaTransitDays',
    width: 88,
    align: 'right',
    sorter: true,
    render: (row) => formatPerformanceDays(row.seaTransitDays),
  },
  {
    title: '到港后送仓',
    key: 'postArrivalDays',
    width: 100,
    align: 'right',
    sorter: true,
    render: (row) => formatPerformanceDays(row.postArrivalDays),
  },
  {
    title: '全程时效',
    key: 'fullTransitDays',
    width: 88,
    align: 'right',
    sorter: true,
    defaultSortOrder: 'descend',
    render: (row) => formatPerformanceDays(row.fullTransitDays),
  },
  {
    title: '送仓偏差',
    key: 'deliveryDeviationDays',
    width: 88,
    align: 'right',
    sorter: true,
    render: (row) => formatPerformanceDays(row.deliveryDeviationDays),
  },
  {
    title: '异常',
    key: 'anomalyFlags',
    minWidth: 160,
    render: (row) =>
      row.anomalyFlags.length
        ? h(
            'div',
            { class: 'flex flex-wrap gap-1' },
            row.anomalyFlags.map((flag) =>
              h(NTag, { size: 'small', type: 'warning', bordered: false }, { default: () => flag }),
            ),
          )
        : '—',
  },
]

const overviewKpis = computed(() => {
  const o = analysis.value?.overview
  const n = analysis.value?.analyzedCount ?? 0
  if (!o) return []
  return [
    { label: '总票数', value: String(o.totalCount) },
    { label: '已签收', value: String(o.signedCount) },
    { label: '签收完成率', value: pctCell(o.signedRate) },
    { label: '平均海运时效', value: metricCell(o.seaTransit, n) },
    { label: '平均到港后送仓', value: metricCell(o.postArrival, n) },
    { label: '平均全程时效', value: metricCell(o.fullTransit, n) },
    {
      label: '最快签收时效',
      value: formatPerformanceDays(o.fastestSignedTransitDays),
      shipmentNo: o.fastestSignedShipmentNo,
    },
    {
      label: '最慢签收时效',
      value: formatPerformanceDays(o.slowestSignedTransitDays),
      shipmentNo: o.slowestSignedShipmentNo,
    },
    { label: '平均送仓偏差', value: metricCell(o.deliveryDeviation, n) },
    { label: '异常票数', value: String(o.anomalyCount) },
    { label: '异常率', value: pctCell(o.anomalyRate) },
  ]
})

function rankingRows(rows: PerformanceGroupRow[]) {
  return rows.map((row) => ({
    label: row.label,
    avg: row.fullTransit.avgDays,
    sample: row.fullTransit.sampleCount,
  }))
}

async function loadFilterOptions() {
  try {
    const opts = await getShipmentFilterOptions()
    channelOptions.value = opts.channelCodes.map((v) => ({ label: v, value: v }))
    carrierOptions.value = buildCarrierSelectOptions(opts.carriers, opts.carrierCodes)
    customerOptions.value = opts.customers.map((v) => ({ label: v, value: v }))
  } catch {
    /* 筛选项加载失败不阻塞主流程 */
  }
}

async function loadAnalysis() {
  loading.value = true
  error.value = ''
  try {
    analysis.value = await getShipmentPerformanceAnalysis(buildQueryParams())
    truncated.value = analysis.value.truncated
    if (activeTab.value === 'details') {
      detailPage.value = 1
      await loadDetails()
    }
  } catch (e) {
    analysis.value = null
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadDetails() {
  loadingDetails.value = true
  try {
    const res = await getShipmentPerformanceDetails({
      ...buildQueryParams(),
      page: detailPage.value,
      pageSize: detailPageSize.value,
      sortBy: detailSortBy.value,
      sortOrder: detailSortOrder.value,
    })
    detailItems.value = res.items
    detailTotal.value = res.total
    detailsTruncated.value = res.truncated
  } catch (e) {
    detailItems.value = []
    detailTotal.value = 0
    message.error(e instanceof Error ? e.message : '明细加载失败')
  } finally {
    loadingDetails.value = false
  }
}

function handleSearch() {
  void loadAnalysis()
}

function handleReset() {
  resetFilters()
  void loadAnalysis()
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportShipmentPerformanceCsv(buildQueryParams())
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').slice(0, 14)
    downloadBlob(blob, `运输时效统计_${ts}.csv`)
    message.success('CSV 已导出')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

function handleDetailSorterChange(sorter: DataTableSortState | null) {
  const allowed = new Set([
    'shipmentNo',
    'signedTime',
    'seaTransitDays',
    'postArrivalDays',
    'fullTransitDays',
    'deliveryDeviationDays',
  ])
  if (!sorter || !sorter.order || !allowed.has(String(sorter.columnKey))) {
    detailSortBy.value = 'fullTransitDays'
    detailSortOrder.value = 'desc'
  } else {
    detailSortBy.value = String(sorter.columnKey)
    detailSortOrder.value = sorter.order === 'ascend' ? 'asc' : 'desc'
  }
  detailPage.value = 1
  void loadDetails()
}

watch(activeTab, (tab) => {
  if (tab === 'details' && analysis.value) {
    void loadDetails()
  }
})

watch([detailPage, detailPageSize], () => {
  if (activeTab.value === 'details' && analysis.value) {
    void loadDetails()
  }
})

onMounted(async () => {
  await loadFilterOptions()
  await loadAnalysis()
})
</script>

<template>
  <div class="scrollbar-subtle flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="page-h2">统计管理</h2>
        <p class="mt-1 text-xs text-[var(--color-muted)]">
          运输时效分析：海运时效、到港后送仓、全程时效与送仓偏差；默认按 ATD 口径筛选。
        </p>
      </div>
    </div>

    <section class="panel p-4">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">开始日期</p>
          <NDatePicker v-model:value="dateFromTs" type="date" clearable class="w-full" />
        </div>
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">结束日期</p>
          <NDatePicker v-model:value="dateToTs" type="date" clearable class="w-full" />
        </div>
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">时间口径</p>
          <NSelect v-model:value="dateBasis" :options="dateBasisOptions" />
        </div>
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">渠道</p>
          <NSelect v-model:value="channelCode" :options="channelOptions" clearable filterable />
        </div>
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">承运商</p>
          <NSelect v-model:value="carrierCode" :options="carrierOptions" clearable filterable />
        </div>
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">客户</p>
          <NSelect v-model:value="customer" :options="customerOptions" clearable filterable />
        </div>
        <div>
          <p class="mb-1 text-[10px] text-[var(--color-muted)]">目的港</p>
          <NInput v-model:value="destinationPortCode" clearable placeholder="目的港代码" />
        </div>
      </div>
      <div class="mt-3 flex flex-wrap gap-2">
        <NButton type="primary" size="small" :loading="loading" @click="handleSearch">查询</NButton>
        <NButton size="small" :disabled="loading" @click="handleReset">重置</NButton>
        <NButton size="small" :loading="exporting" @click="handleExport">导出 CSV</NButton>
      </div>
    </section>

    <NAlert v-if="truncated" type="warning" :bordered="false">
      筛选结果超过分析上限，仅统计前 20,000 条运单；导出同样受限于该范围。
    </NAlert>

    <NSpin :show="loading">
      <div v-if="error" class="panel px-4 py-6 text-sm text-red-400">{{ error }}</div>
      <template v-else-if="analysis">
        <NTabs v-model:value="activeTab" type="line" animated>
          <NTabPane name="overview" tab="总览">
            <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <article v-for="item in overviewKpis" :key="item.label" class="panel p-4">
                <p class="text-xs text-[var(--color-muted)]">{{ item.label }}</p>
                <p class="mt-1 text-lg font-semibold tabular-nums text-[var(--color-fg-emphasis)]">
                  {{ item.value }}
                </p>
                <button
                  v-if="item.shipmentNo"
                  type="button"
                  class="mt-1 max-w-full truncate text-left text-xs text-violet-400 hover:underline"
                  :title="item.shipmentNo"
                  @click="goShipment(item.shipmentNo)"
                >
                  {{ item.shipmentNo }}
                </button>
              </article>
            </div>

            <div class="mt-4 grid gap-4 xl:grid-cols-2">
              <section class="panel p-4">
                <h3 class="mb-3 text-sm font-medium text-[var(--color-fg-emphasis)]">渠道全程时效排行</h3>
                <ul v-if="analysis.overview.channelRanking.length" class="space-y-2 text-xs">
                  <li
                    v-for="(row, idx) in rankingRows(analysis.overview.channelRanking)"
                    :key="row.label"
                    class="flex items-center justify-between gap-2"
                  >
                    <span class="truncate text-[var(--color-fg)]">{{ idx + 1 }}. {{ row.label }}</span>
                    <span class="shrink-0 tabular-nums text-[var(--color-muted)]">
                      {{ row.avg != null ? `${row.avg} 天` : '—' }}
                      <span v-if="row.sample" class="text-[var(--color-fg-secondary)]">· n={{ row.sample }}</span>
                    </span>
                  </li>
                </ul>
                <p v-else class="text-xs text-[var(--color-muted)]">暂无可计算样本</p>
              </section>
              <section class="panel p-4">
                <h3 class="mb-3 text-sm font-medium text-[var(--color-fg-emphasis)]">承运商全程时效排行</h3>
                <ul v-if="analysis.overview.carrierRanking.length" class="space-y-2 text-xs">
                  <li
                    v-for="(row, idx) in rankingRows(analysis.overview.carrierRanking)"
                    :key="row.label"
                    class="flex items-center justify-between gap-2"
                  >
                    <span class="truncate text-[var(--color-fg)]">{{ idx + 1 }}. {{ row.label }}</span>
                    <span class="shrink-0 tabular-nums text-[var(--color-muted)]">
                      {{ row.avg != null ? `${row.avg} 天` : '—' }}
                      <span v-if="row.sample" class="text-[var(--color-fg-secondary)]">· n={{ row.sample }}</span>
                    </span>
                  </li>
                </ul>
                <p v-else class="text-xs text-[var(--color-muted)]">暂无可计算样本</p>
              </section>
            </div>
          </NTabPane>

          <NTabPane name="channel" tab="渠道时效">
            <NDataTable
              :columns="channelColumns"
              :data="analysis.byChannel"
              :bordered="false"
              size="small"
              :scroll-x="1400"
              :pagination="false"
            />
          </NTabPane>

          <NTabPane name="carrier" tab="承运商时效">
            <NDataTable
              class="mb-4"
              :columns="carrierColumns"
              :data="analysis.byCarrier"
              :bordered="false"
              size="small"
              :scroll-x="1400"
              :pagination="false"
            />
            <h3 class="mb-2 text-sm font-medium text-[var(--color-fg-emphasis)]">承运商 × 渠道</h3>
            <NDataTable
              :columns="carrierChannelColumns"
              :data="analysis.byCarrierChannel"
              :bordered="false"
              size="small"
              :scroll-x="1100"
              :pagination="false"
            />
          </NTabPane>

          <NTabPane name="customer" tab="客户时效">
            <NDataTable
              :columns="customerColumns"
              :data="analysis.byCustomer"
              :bordered="false"
              size="small"
              :scroll-x="1100"
              :pagination="false"
            />
          </NTabPane>

          <NTabPane name="details" tab="明细">
            <NAlert
              v-if="detailsTruncated"
              class="mb-3"
              type="warning"
              :bordered="false"
            >
              明细导出/列表受分析上限影响，当前页数据可能不完整。
            </NAlert>
            <NSpin :show="loadingDetails">
              <NDataTable
                remote
                :columns="detailColumns"
                :data="detailItems"
                :bordered="false"
                size="small"
                :scroll-x="1800"
                :pagination="false"
                @update:sorter="handleDetailSorterChange"
              />
              <div class="mt-3 flex justify-end">
                <NPagination
                  v-model:page="detailPage"
                  v-model:page-size="detailPageSize"
                  :item-count="detailTotal"
                  :page-sizes="[20, 50, 100, 200]"
                  show-size-picker
                />
              </div>
            </NSpin>
          </NTabPane>
        </NTabs>
      </template>
    </NSpin>
  </div>
</template>
