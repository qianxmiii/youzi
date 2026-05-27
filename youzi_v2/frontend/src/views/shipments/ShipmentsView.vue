<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDataTable,
  NInput,
  NPagination,
  NPopconfirm,
  NSelect,
  NSpace,
  NTag,
  NTooltip,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import ShipmentExceptionCloseModal from '@/components/shipments/ShipmentExceptionCloseModal.vue'
import ShipmentExceptionOpenModal from '@/components/shipments/ShipmentExceptionOpenModal.vue'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import ShipmentTrackingFreshnessBar from '@/components/shipments/ShipmentTrackingFreshnessBar.vue'
import ShipmentBatchEditModal from '@/components/shipments/ShipmentBatchEditModal.vue'
import VipStarBadge from '@/components/common/VipStarBadge.vue'
import LastMileBadge from '@/components/common/LastMileBadge.vue'
import ExceptionStatusBadge from '@/components/common/ExceptionStatusBadge.vue'
import {
  batchDeleteShipments,
  batchUpdateShipments,
  closeShipmentExceptions,
  deleteShipment,
  exportShipmentsExcel,
  getShipment,
  getShipmentFilterOptions,
  getTrackingFreshnessStats,
  getTrackingSyncDailyStats,
  importShipmentsExcel,
  listShipments,
  openShipmentExceptions,
  syncCarrierTracking,
  syncTracking,
  updateShipment,
} from '@/api/shipments'
import ShipmentFormModal from '@/components/shipments/ShipmentFormModal.vue'
import type { Shipment, ShipmentBatchResult, ShipmentPayload } from '@/types/shipment'
import type { ShipmentFilterOptions } from '@/api/shipments'
import type { TrackingSyncDailyStats, TrackingSyncResult } from '@/types/tracking'
import { CARRIER_FILTER_EMPTY } from '@/constants/shipmentFilters'
import { useDictLabels } from '@/composables/useDictLabels'
import { formatRelativeTime } from '@/utils/formatDateTime'
import { parseBatchSearchTokens } from '@/utils/parseBatchSearch'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'
import { formatLastMileTooltip, resolveLastMileTracking } from '@/utils/lastMileTracking'
import {
  daysSinceLocalCalendar,
  FRESHNESS_DOT_CLASS,
  isCarrierTrackingNewerThanInternal,
  trackingFreshnessLevel,
  type TrackingFreshnessBucket,
  type TrackingFreshnessStats,
} from '@/utils/trackingFreshness'

const message = useMessage()
const { loadDictTypes, dictLabel } = useDictLabels()
const countryLabel = (raw: string | null | undefined) => dictLabel('country_code', raw)
const loading = ref(false)
const importing = ref(false)
const exporting = ref(false)
const syncingTracking = ref(false)
const syncingCarrier = ref(false)
const carrierDaily = ref<TrackingSyncDailyStats | null>(null)
const freshnessStats = ref<TrackingFreshnessStats | null>(null)
const filterInternalFreshness = ref<TrackingFreshnessBucket | null>(null)
const filterCarrierFreshness = ref<TrackingFreshnessBucket | null>(null)
const filterCarrierAheadOfInternal = ref(false)
const items = ref<Shipment[]>([])
const total = ref(0)
const searchShipmentNo = ref('')
const searchKeyword = ref('')
const searchTrackingContent = ref('')
const DEFAULT_STATUS_FILTER = 'IN_TRANSIT'
const filterStatus = ref<string | null>(DEFAULT_STATUS_FILTER)
const filterCustomer = ref<string | null>(null)
const filterCarrier = ref<string | null>(null)
const filterCountry = ref<string | null>(null)
const filterChannelNameZh = ref<string | null>(null)
const filterChannelCategory = ref<string | null>(null)
const filtersExpanded = ref(false)
const filterStaleDays = ref<number | null>(null)
const filterNoTracking = ref(false)
const filterException = ref<string | null>(null)
const filterHasException = ref<boolean | null>(null)
const filterOptions = ref<ShipmentFilterOptions>({
  customers: [],
  carrierCodes: [],
  countryCodes: [],
  channelCodes: [],
  channelNameZhs: [],
  channelCategories: [],
  statusCodes: [],
  exceptionCodes: [],
  exceptionTypes: [],
})
const exceptionOpenShow = ref(false)
const exceptionCloseShow = ref(false)
const exceptionSubmitting = ref(false)
const batchEditShow = ref(false)
const batchSubmitting = ref(false)
const page = ref(1)
const pageSize = ref(20)
const trackingDrawerShow = ref(false)
const trackingDrawerShipment = ref<Shipment | null>(null)
const trackingDrawerTab = ref<'internal' | 'carrier'>('internal')

const modalShow = ref(false)
const modalMode = ref<'edit'>('edit')
const editingRow = ref<Shipment | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const checkedRowKeys = ref<string[]>([])

const selectedCount = computed(() => checkedRowKeys.value.length)

const shipmentNoTokens = computed(() => parseBatchSearchTokens(searchShipmentNo.value))
const batchShipmentSearchActive = computed(() => shipmentNoTokens.value.length > 1)

/** 按当前页最长运单号 + 侧栏标识（VIP / 异常）估算列宽 */
const shipmentNoColWidth = computed(() => {
  let maxLen = 10
  let maxBadges = 0
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.shipmentNo || '').length)
    let badges = 0
    if (row.isVip) badges++
    if (hasActiveException(row)) badges++
    maxBadges = Math.max(maxBadges, badges)
  }
  const textW = Math.ceil(maxLen * 7) + 28
  const badgeW = maxBadges > 0 ? 8 + maxBadges * 22 : 0
  return Math.min(320, Math.max(176, textW + badgeW))
})

/** 按当前页最长客户名估算列宽 */
const customerColWidth = computed(() => {
  let maxLen = 4
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.customer || '').length)
  }
  return Math.min(180, Math.max(108, Math.ceil(maxLen * 7) + 20))
})

const selectedShipmentNos = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)).map((row) => row.shipmentNo),
)

const selectedRows = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)),
)

const selectedIds = computed(() => selectedRows.value.map((row) => row.id))

const channelCodeOptions = computed(() =>
  filterOptions.value.channelCodes.map((v) => ({ label: v, value: v })),
)

function rowKey(row: Shipment) {
  return row.id
}

function formatTrackingMessage(res: TrackingSyncResult, label = '轨迹') {
  const unassigned =
    res.unassigned && res.unassigned > 0 ? `，未匹配 vendor ${res.unassigned} 单` : ''
  let text =
    `${label}已更新：${res.updated}/${res.total} 单（${res.batches} 批×${res.batchSize}），新增 ${res.logCount} 条` +
    (res.skipped ? `，跳过 ${res.skipped} 单` : '') +
    (res.notFound ? `，未返回/失败 ${res.notFound} 单` : '') +
    (res.empty ? `，无轨迹 ${res.empty} 单` : '') +
    (res.excludedNotInTransit
      ? `，已跳过不可同步 ${res.excludedNotInTransit} 单`
      : '') +
    unassigned
  if (res.errors.length) {
    const preview = res.errors.slice(0, 3).join('；')
    const more = res.errors.length > 3 ? `…等 ${res.errors.length} 条` : ''
    text += `；错误：${preview}${more}`
  }
  return text
}

function notifyTrackingSyncResult(res: TrackingSyncResult, label: string) {
  const content = formatTrackingMessage(res, label)
  if (res.errors.length && res.updated === 0) {
    message.error(content, { duration: 12_000 })
  } else if (res.errors.length) {
    message.warning(content, { duration: 12_000 })
  } else {
    message.success(content, { duration: 8000 })
  }
  if (res.errors.length) {
    console.warn(`sync ${label} errors:`, res.errors)
  }
  if (res.logs?.length) {
    console.info(`sync ${label} log:\n${res.logs.join('\n')}`)
  }
}

async function loadCarrierDailyStats() {
  try {
    carrierDaily.value = await getTrackingSyncDailyStats('carrier')
  } catch {
    carrierDaily.value = null
  }
}

async function loadFreshnessStats() {
  try {
    freshnessStats.value = await getTrackingFreshnessStats()
  } catch {
    freshnessStats.value = null
  }
}

const carrierSyncHint = computed(() => {
  if (!carrierDaily.value) return null
  const d = carrierDaily.value
  let s = `今日同步任务已更新 ${d.updatedShipments} 单、新增 ${d.newLogCount} 条节点`
  if (d.lastFinished) s += ` · 上次 ${d.lastFinished}`
  return s
})

function applyFreshnessFilter(source: 'internal' | 'carrier', bucket: TrackingFreshnessBucket) {
  if (source === 'internal') {
    filterInternalFreshness.value = bucket
  } else {
    filterCarrierFreshness.value = bucket
  }
  filtersExpanded.value = true
  onFiltersChanged()
}

function clearFreshnessFilter(source: 'internal' | 'carrier') {
  if (source === 'internal') filterInternalFreshness.value = null
  else filterCarrierFreshness.value = null
  onFiltersChanged()
}

function toggleCarrierAheadFilter() {
  filterCarrierAheadOfInternal.value = !filterCarrierAheadOfInternal.value
  filtersExpanded.value = true
  onFiltersChanged()
}

const statusLabel: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

const exceptionLabelByCode = computed(() => {
  const m: Record<string, string> = {}
  for (const t of filterOptions.value.exceptionTypes) {
    m[t.code] = t.nameZh
  }
  return m
})

function exceptionLabel(code: string | null | undefined) {
  if (!code) return '—'
  return exceptionLabelByCode.value[code] || code
}

function hasActiveException(row: Shipment) {
  return !!(row.exceptionCode && row.exceptionCode.trim())
}

async function openTrackingDrawer(row: Shipment, tab: 'internal' | 'carrier' = 'internal') {
  trackingDrawerTab.value = tab
  trackingDrawerShow.value = true
  trackingDrawerShipment.value = row
  try {
    trackingDrawerShipment.value = await getShipment(row.id)
  } catch {
    /* 列表行数据兜底 */
  }
}

function renderTrackingSummaryCell(
  row: Shipment,
  tab: 'internal' | 'carrier',
  time: string | null | undefined,
  desc: string | null | undefined,
) {
  const t = (time || '').trim()
  const d = (desc || '').trim()
  if (!t && !d) {
    return h('span', { class: 'tracking-empty' }, '—')
  }
  const carrierAhead = isCarrierTrackingNewerThanInternal(row)
  const effective =
    tab === 'internal' ? hasEffectiveInternalTracking(row) : Boolean(t)
  const level = trackingFreshnessLevel(time, effective)
  const dot = h('span', {
    class: `mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${FRESHNESS_DOT_CLASS[level]}`,
    'aria-hidden': 'true',
  })
  const timeRow =
    tab === 'carrier' && carrierAhead
      ? h('div', { class: 'flex min-w-0 items-center gap-1 leading-tight' }, [
          h('div', { class: 'tracking-ahead-time truncate text-xs tabular-nums' }, t),
          h('span', { class: 'tracking-ahead-badge shrink-0' }, '承新'),
        ])
      : t
        ? h(
            'div',
            {
              class: [
                'text-xs tabular-nums leading-tight',
                tab === 'internal' && carrierAhead ? 'tracking-time--faded' : 'tracking-time',
              ],
            },
            t,
          )
        : null
  const block = h('div', { class: 'tracking-summary-cell min-w-0 max-w-full flex gap-1.5' }, [
    dot,
    h('div', { class: 'min-w-0 flex-1' }, [
      timeRow,
      d
        ? h(
            'div',
            {
              class: [
                'text-xs leading-snug truncate',
                tab === 'carrier' && carrierAhead
                  ? 'tracking-ahead-desc'
                  : tab === 'internal' && carrierAhead
                    ? 'tracking-desc--faded'
                    : 'tracking-desc',
              ],
              title: d,
            },
            d,
          )
        : h('div', { class: 'tracking-empty text-xs' }, '—'),
    ]),
  ])
  const btnClass = [
    'tracking-summary-btn w-full min-w-0 cursor-pointer rounded px-1 py-0.5 text-left transition-colors',
    tab === 'carrier' && carrierAhead ? 'tracking-summary-btn--carrier-ahead' : '',
    tab === 'internal' && carrierAhead ? 'tracking-summary-btn--internal-behind' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const clickable = h(
    'button',
    {
      type: 'button',
      class: btnClass,
      onClick: (e: MouseEvent) => {
        e.stopPropagation()
        openTrackingDrawer(row, tab)
      },
    },
    [block],
  )
  const tip = [t, d].filter(Boolean).join('\n')
  if (tip.length > 36) {
    return h(NTooltip, { trigger: 'hover' }, { trigger: () => clickable, default: () => tip })
  }
  return clickable
}

function renderVipBadge(row: Shipment) {
  if (!row.isVip) return null
  return h(VipStarBadge)
}

function openLastMileTrackUrl(row: Shipment) {
  const info = resolveLastMileTracking(row)
  if (!info?.url) {
    message.warning('暂未识别承运商官网，请手动查询')
    return
  }
  window.open(info.url, '_blank', 'noopener,noreferrer')
}

function renderLastMileBadge(row: Shipment) {
  const info = resolveLastMileTracking(row)
  if (!info) return null
  const badgeBtn = h(
    'button',
    {
      type: 'button',
      class: 'last-mile-badge-btn',
      onClick: (e: MouseEvent) => {
        e.stopPropagation()
        openLastMileTrackUrl(row)
      },
    },
    [h(LastMileBadge, { interactive: Boolean(info.url) })],
  )
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () => badgeBtn,
      default: () => formatLastMileTooltip(row) ?? info.number,
    },
  )
}

function renderUpdatedTime(row: Shipment) {
  const formatted = formatRelativeTime(row.updatedTime)
  if (!formatted) return '—'
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () =>
        h(
          'span',
          { class: 'cursor-default text-zinc-400 tabular-nums' },
          formatted.relative,
        ),
      default: () => formatted.absolute,
    },
  )
}

function renderExceptionBadge(row: Shipment) {
  if (!hasActiveException(row) || !row.exceptionCode) return null
  return h(ExceptionStatusBadge, {
    code: row.exceptionCode,
    label: exceptionLabel(row.exceptionCode),
    durationLabel: row.exceptionDurationLabel,
  })
}

function renderShipmentNo(row: Shipment) {
  const noCell = h(
    'span',
    { class: 'shipment-no-cell font-medium' },
    row.shipmentNo,
  )
  const inner = h('span', { class: 'shipment-no-cell-row' }, [
    noCell,
    renderVipBadge(row),
    renderLastMileBadge(row),
    renderExceptionBadge(row),
  ])
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () => inner,
      default: () => row.shipmentNo,
    },
  )
}

const exceptionColumns: DataTableColumns<Shipment> = [
  {
    title: '异常',
    key: 'exceptionCode',
    width: 88,
    align: 'center',
    render: (row) => {
      if (!row.exceptionCode) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return h(ExceptionStatusBadge, {
        code: row.exceptionCode,
        label: exceptionLabel(row.exceptionCode),
        durationLabel: row.exceptionDurationLabel,
        showLabel: true,
      })
    },
  },
  {
    title: '异常时长',
    key: 'exceptionDurationLabel',
    width: 88,
    align: 'center',
    render: (row) => {
      if (!row.exceptionDurationLabel) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return h('span', { class: 'text-xs tabular-nums text-zinc-400' }, row.exceptionDurationLabel)
    },
  },
]

const statusOptions = computed(() =>
  filterOptions.value.statusCodes.map((code) => ({
    label: statusLabel[code] || code,
    value: code,
  })),
)

const exceptionFilterOptions = computed(() =>
  filterOptions.value.exceptionTypes.map((t) => ({
    label: t.nameZh,
    value: t.code,
  })),
)

const hasExceptionFilterOptions = [
  { label: '有异常', value: 'yes' },
  { label: '无异常', value: 'no' },
]

const staleOptions = [
  { label: '≥7 天未更新', value: 7 },
  { label: '≥14 天未更新', value: 14 },
  { label: '≥30 天未更新', value: 30 },
]

const customerOptions = computed(() =>
  filterOptions.value.customers.map((v) => ({ label: v, value: v })),
)
const carrierOptions = computed(() => [
  { label: '（未填写）', value: CARRIER_FILTER_EMPTY },
  ...filterOptions.value.carrierCodes.map((v) => ({ label: v, value: v })),
])
const countryOptions = computed(() =>
  filterOptions.value.countryCodes.map((code) => ({
    label: countryLabel(code) === code ? code : `${countryLabel(code)} (${code})`,
    value: code,
  })),
)
const channelNameZhOptions = computed(() =>
  filterOptions.value.channelNameZhs.map((v) => ({ label: v, value: v })),
)
const channelCategoryOptions = computed(() =>
  filterOptions.value.channelCategories.map((v) => ({ label: v, value: v })),
)

const advancedFiltersActiveCount = computed(() => {
  let n = 0
  if (filterCarrier.value) n++
  if (filterCountry.value) n++
  if (filterChannelNameZh.value) n++
  if (filterChannelCategory.value) n++
  if (filterHasException.value != null) n++
  if (filterException.value) n++
  if (filterStaleDays.value != null && filterStaleDays.value !== '') n++
  if (filterNoTracking.value) n++
  if (filterInternalFreshness.value) n++
  if (filterCarrierFreshness.value) n++
  if (filterCarrierAheadOfInternal.value) n++
  return n
})

function channelDisplayLabel(row: Shipment): string {
  const zh = row.channelNameZh?.trim()
  if (zh) return zh
  return row.channelCode?.trim() || '—'
}

/** 横向滚动宽度 = 各列 width 之和 + 余量（避免滑条到不了最右侧） */
function sumTableColumnWidths(cols: DataTableColumns<Shipment>): number {
  let total = 0
  for (const col of cols) {
    if (col.type === 'selection') {
      total += typeof col.width === 'number' ? col.width : 40
      continue
    }
    const w = 'width' in col ? col.width : undefined
    if (typeof w === 'number') total += w
  }
  return total
}

/** 运单表滚动条：悬停显示、细轨道，避免常显抢眼 */
const tableScrollbarProps = {
  trigger: 'hover' as const,
  size: 6,
  themeOverrides: {
    railColor: 'transparent',
    color: 'rgba(113, 113, 122, 0.35)',
    colorHover: 'rgba(161, 161, 170, 0.55)',
  },
}

function clearSelection() {
  checkedRowKeys.value = []
}

function buildListParams(): Parameters<typeof listShipments>[0] {
  const tokens = shipmentNoTokens.value
  const keyword = searchKeyword.value.trim()
  const multiShipment = batchShipmentSearchActive.value
  const limit = multiShipment
    ? Math.min(500, Math.max(pageSize.value, tokens.length))
    : pageSize.value
  const offset = multiShipment ? 0 : (page.value - 1) * pageSize.value
  const staleRaw = filterStaleDays.value
  const staleDays =
    staleRaw == null || staleRaw === ''
      ? undefined
      : typeof staleRaw === 'number'
        ? staleRaw
        : Number(staleRaw)

  return {
    ...(tokens.length ? { shipmentNos: tokens } : {}),
    ...(keyword ? { search: keyword } : {}),
    ...(searchTrackingContent.value.trim()
      ? { trackingSearch: searchTrackingContent.value.trim() }
      : {}),
    statusCode: filterStatus.value || undefined,
    exceptionCode: filterException.value || undefined,
    hasException:
      filterHasException.value === true
        ? true
        : filterHasException.value === false
          ? false
          : undefined,
    customer: filterCustomer.value || undefined,
    carrierCode: filterCarrier.value || undefined,
    countryCode: filterCountry.value || undefined,
    channelNameZh: filterChannelNameZh.value || undefined,
    channelCategory: filterChannelCategory.value || undefined,
    internalFreshness: filterInternalFreshness.value || undefined,
    carrierFreshness: filterCarrierFreshness.value || undefined,
    carrierAheadOfInternal: filterCarrierAheadOfInternal.value || undefined,
    minStaleDays:
      filterNoTracking.value || staleDays == null || Number.isNaN(staleDays) || staleDays <= 0
        ? undefined
        : staleDays,
    noTracking: filterNoTracking.value || undefined,
    limit,
    offset,
  }
}

let listRequestSeq = 0

async function loadList() {
  const seq = ++listRequestSeq
  loading.value = true
  try {
    const res = await listShipments(buildListParams())
    if (seq !== listRequestSeq) return
    items.value = res.items
    total.value = res.total
  } catch (e) {
    if (seq !== listRequestSeq) return
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    if (seq === listRequestSeq) loading.value = false
  }
}

/** 下拉/勾选筛选变更：回到第 1 页并立即刷新 */
function onFiltersChanged() {
  page.value = 1
  checkedRowKeys.value = []
  void loadList()
}

function onNoTrackingChanged(checked: boolean) {
  if (checked) filterStaleDays.value = null
  onFiltersChanged()
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchShipmentNo, searchKeyword, searchTrackingContent], () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    checkedRowKeys.value = []
    void loadList()
  }, 300)
})

watch([page, pageSize], () => {
  checkedRowKeys.value = []
  void loadList()
})

async function loadFilterOptions() {
  try {
    filterOptions.value = await getShipmentFilterOptions()
  } catch {
    /* 筛选项加载失败不阻塞列表 */
  }
}

onMounted(async () => {
  await loadDictTypes('country_code')
  await loadFilterOptions()
  await loadCarrierDailyStats()
  await loadFreshnessStats()
  await loadList()
})

function openEdit(row: Shipment) {
  modalMode.value = 'edit'
  editingRow.value = row
  modalShow.value = true
}

async function handleFormSubmit(payload: ShipmentPayload) {
  try {
    if (!editingRow.value) return
    const editId = editingRow.value.id
    await updateShipment(editId, payload)
    message.success('运单已更新')
    modalShow.value = false
    await loadList()
    if (trackingDrawerShipment.value?.id === editId) {
      try {
        trackingDrawerShipment.value = await getShipment(editId)
      } catch {
        trackingDrawerShipment.value =
          items.value.find((r) => r.id === editId) ?? trackingDrawerShipment.value
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  }
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
    const params = buildListParams()
    const blob = await exportShipmentsExcel({
      ...params,
      limit: Math.min(total.value || 10_000, 10_000),
      offset: 0,
    })
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').slice(0, 14)
    downloadBlob(blob, `运单导出_${ts}.xlsx`)
    message.success(`已导出 ${total.value} 条运单（当前筛选）`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleDelete(row: Shipment) {
  try {
    await deleteShipment(row.id)
    message.success('已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除失败')
  }
}

function notifyBatchResult(res: ShipmentBatchResult, verb: '删除' | '更新') {
  const ok = verb === '删除' ? (res.deleted ?? 0) : (res.updated ?? 0)
  let text = `${verb}完成：成功 ${ok} / ${res.total} 条`
  if (res.skipped.length) text += `，跳过 ${res.skipped.length} 条`
  if (res.errors.length) text += `，失败 ${res.errors.length} 条`
  if (res.errors.length && ok === 0) {
    message.error(text, { duration: 8000 })
  } else if (res.skipped.length || res.errors.length) {
    message.warning(text, { duration: 6000 })
  } else {
    message.success(text)
  }
}

async function handleBatchDelete() {
  const ids = selectedIds.value
  if (!ids.length) {
    message.warning('请先勾选运单')
    return
  }
  batchSubmitting.value = true
  try {
    const res = await batchDeleteShipments(ids)
    notifyBatchResult(res, '删除')
    clearSelection()
    if (items.value.length <= ids.length && page.value > 1) page.value -= 1
    await loadList()
    await loadFreshnessStats()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量删除失败')
  } finally {
    batchSubmitting.value = false
  }
}

async function handleBatchEditSubmit(updates: Partial<ShipmentPayload>) {
  const ids = selectedIds.value
  if (!ids.length) return
  batchSubmitting.value = true
  try {
    const res = await batchUpdateShipments(ids, updates)
    notifyBatchResult(res, '更新')
    batchEditShow.value = false
    clearSelection()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量修改失败')
  } finally {
    batchSubmitting.value = false
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleSyncTracking(shipmentNos?: string[]) {
  syncingTracking.value = true
  try {
    const res = await syncTracking(shipmentNos)
    notifyTrackingSyncResult(res, '内部轨迹')
    await loadFreshnessStats()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新内部轨迹失败')
  } finally {
    syncingTracking.value = false
  }
}

async function handleSyncCarrierTracking(shipmentNos?: string[]) {
  syncingCarrier.value = true
  try {
    const res = await syncCarrierTracking(shipmentNos)
    notifyTrackingSyncResult(res, '承运商轨迹')
    await loadCarrierDailyStats()
    await loadFreshnessStats()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新承运商轨迹失败')
  } finally {
    syncingCarrier.value = false
  }
}

function resetFilters() {
  filterStatus.value = DEFAULT_STATUS_FILTER
  filterException.value = null
  filterHasException.value = null
  filterCustomer.value = null
  filterCarrier.value = null
  filterCountry.value = null
  filterChannelNameZh.value = null
  filterChannelCategory.value = null
  filterInternalFreshness.value = null
  filterCarrierFreshness.value = null
  filterCarrierAheadOfInternal.value = false
  filtersExpanded.value = false
  filterStaleDays.value = null
  filterNoTracking.value = false
  searchShipmentNo.value = ''
  searchKeyword.value = ''
  searchTrackingContent.value = ''
  page.value = 1
  loadList()
}

function onHasExceptionFilterChange(val: string | null) {
  filterHasException.value = val === 'yes' ? true : val === 'no' ? false : null
  onFiltersChanged()
}

async function handleOpenException(
  exceptionCode: string,
  openedTime?: string,
  note?: string,
) {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  exceptionSubmitting.value = true
  try {
    const res = await openShipmentExceptions(nos, exceptionCode, { openedTime, note })
    exceptionOpenShow.value = false
    let text = `已标记异常 ${res.opened ?? 0} 条`
    if (res.skipped.length) text += `，跳过 ${res.skipped.length} 条`
    if (res.errors.length) text += `，失败 ${res.errors.length} 条`
    message.success(text)
    clearSelection()
    await loadList()
    await loadFilterOptions()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '标记异常失败')
  } finally {
    exceptionSubmitting.value = false
  }
}

async function handleCloseException(closedTime?: string, note?: string) {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  exceptionSubmitting.value = true
  try {
    const res = await closeShipmentExceptions(nos, { closedTime, note })
    exceptionCloseShow.value = false
    let text = `已解除异常 ${res.closed ?? 0} 条`
    if (res.skipped.length) text += `，跳过 ${res.skipped.length} 条`
    if (res.errors.length) text += `，失败 ${res.errors.length} 条`
    message.success(text)
    clearSelection()
    await loadList()
    await loadFilterOptions()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '解除异常失败')
  } finally {
    exceptionSubmitting.value = false
  }
}

async function handleSyncSelectedInternal() {
  if (!selectedRows.value.length) {
    message.warning('请先勾选运单')
    return
  }
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('所选运单无有效运单号')
    return
  }
  await handleSyncTracking(nos)
}

async function handleSyncSelectedCarrier() {
  if (!selectedRows.value.length) {
    message.warning('请先勾选运单')
    return
  }
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('所选运单无有效运单号')
    return
  }
  await handleSyncCarrierTracking(nos)
}

async function copySelectedShipmentNos() {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  const text = nos.join('\n')
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制 ${nos.length} 个运单号`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

function displayField(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

function formatCtnsField(ctns: number | null | undefined): string {
  if (ctns === null || ctns === undefined) return ''
  return `${ctns}ctns`
}

/** 复制格式：运单号 = 客户订单号 [= 货件号] = 地址代码 = 件数ctns → 物流时间 → 物流轨迹 */
function formatTrackingCopyBlock(
  row: Shipment,
  tracking: { desc: string; time: string },
): string {
  const headParts = [
    displayField(row.shipmentNo),
    displayField(row.customerNo),
  ]
  const shipmentId = displayField(row.customerShipmentId)
  if (shipmentId) headParts.push(shipmentId)
  headParts.push(displayField(row.addressCode), formatCtnsField(row.ctns))
  const head = headParts.join(' = ')
  return `${head}\n${tracking.time}\n${tracking.desc}`
}

/** 列表已有字段：优先内部最新轨迹，否则承运商摘要 */
function latestTrackingForCopy(row: Shipment): { desc: string; time: string } {
  if (hasEffectiveInternalTracking(row)) {
    return {
      desc: row.latestTrackingDesc?.trim() || '—',
      time: row.latestTrackingTime?.trim() || '—',
    }
  }
  const carrierDesc = row.latestCarrierDesc?.trim()
  const carrierTime = row.latestCarrierTime?.trim()
  if (carrierDesc || carrierTime) {
    return {
      desc: carrierDesc || '—',
      time: carrierTime || '—',
    }
  }
  return { desc: '—', time: '—' }
}

async function copySelectedLatestTracking() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  try {
    const blocks = rows.map((row) =>
      formatTrackingCopyBlock(row, latestTrackingForCopy(row)),
    )
    await navigator.clipboard.writeText(blocks.join('\n\n'))
    message.success(`已复制 ${rows.length} 条最新轨迹`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '复制失败')
  }
}

async function onFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  importing.value = true
  try {
    const res = await importShipmentsExcel(file)
    let text =
      `导入完成：新增 ${res.created} 条，更新 ${res.updated} 条（按运单号匹配）` +
      (res.failed ? `，跳过/失败 ${res.failed} 行` : '')
    if (res.skippedColumns?.length) {
      const preview = res.skippedColumns.slice(0, 5).join('、')
      const more =
        res.skippedColumns.length > 5 ? ` 等 ${res.skippedColumns.length} 列` : ''
      text += `；未映射列已忽略：${preview}${more}`
    }
    message.success(text, { duration: 8000 })
    if (res.failed > 0 && res.errors.length) {
      console.warn('import errors', res.errors)
    }
    page.value = 1
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

const columns = computed<DataTableColumns<Shipment>>(() => [
  { type: 'selection', fixed: 'left', width: 40 },
  {
    title: '运单号',
    key: 'shipmentNo',
    width: shipmentNoColWidth.value,
    minWidth: 176,
    fixed: 'left',
    cellProps: () => ({ class: 'shipment-td-no' }),
    render: (row) => renderShipmentNo(row),
  },
  {
    title: '状态',
    key: 'statusCode',
    width: 88,
    align: 'center',
    render: (row) => {
      const code = row.statusCode || 'UNKNOWN'
      const label = statusLabel[code] || code
      const type =
        code === 'DELIVERED' ? 'success' : code === 'INSPECTION' ? 'warning' : 'default'
      return h(NTag, { size: 'small', bordered: false, type }, () => label)
    },
  },
  {
    title: '客户',
    key: 'customer',
    width: customerColWidth.value,
    minWidth: 108,
    ellipsis: { tooltip: true },
  },
  { title: '件数', key: 'ctns', width: 64, align: 'center' },
  {
    title: '渠道',
    key: 'channelCode',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => {
      const label = channelDisplayLabel(row)
      const code = row.channelCode?.trim()
      if (!code || label === code) {
        return h('span', label)
      }
      return h(
        NTooltip,
        { placement: 'top' },
        {
          trigger: () => h('span', { class: 'cursor-default' }, label),
          default: () => code,
        },
      )
    },
  },
  { title: '承运商', key: 'carrierCode', width: 90, ellipsis: { tooltip: true } },
  {
    title: '派送地址',
    key: 'addressCode',
    width: 100,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.addressCode) || '—',
  },
  {
    title: '邮编',
    key: 'zipcode',
    width: 96,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.zipcode) || '—',
  },
  {
    title: '内部轨迹',
    key: 'latestTracking',
    width: 220,
    ellipsis: { tooltip: true },
    render: (row) => {
      if (!hasEffectiveInternalTracking(row)) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return renderTrackingSummaryCell(
        row,
        'internal',
        row.latestTrackingTime,
        row.latestTrackingDesc,
      )
    },
  },
  {
    key: 'latestCarrier',
    width: 220,
    ellipsis: { tooltip: true },
    title: () =>
      h('span', { class: 'inline-flex items-center gap-1' }, [
        '承运商轨迹',
        h(
          NTooltip,
          { trigger: 'hover' },
          {
            trigger: () => h('span', { class: 'tracking-ahead-badge cursor-help' }, '承新'),
            default: () => '该运单承运最新节点时间晚于内部时，单元格琥珀色高亮（非按节点条数统计）',
          },
        ),
      ]),
    render: (row) =>
      renderTrackingSummaryCell(
        row,
        'carrier',
        row.latestCarrierTime,
        row.latestCarrierDesc,
      ),
  },
  {
    title: '未更新',
    key: 'staleDays',
    width: 72,
    align: 'center',
    render: (row) => {
      const d = hasEffectiveInternalTracking(row)
        ? daysSinceLocalCalendar(row.latestTrackingTime)
        : null
      if (d === null) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return h(
        NTag,
        {
          size: 'small',
          bordered: false,
          type: d >= 14 ? 'error' : d >= 7 ? 'warning' : 'default',
        },
        () => `${d}天`,
      )
    },
  },
  {
    title: '更新时间',
    key: 'updatedTime',
    width: 108,
    render: (row) => renderUpdatedTime(row),
  },
  ...exceptionColumns,
  {
    title: '操作',
    key: 'actions',
    width: 168,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(
          NButton,
          { size: 'tiny', quaternary: true, onClick: () => openTrackingDrawer(row, 'internal') },
          () => '轨迹',
        ),
        h(
          NButton,
          { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openEdit(row) },
          () => '修改',
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete(row),
          },
          {
            trigger: () =>
              h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, () => '删除'),
            default: () => '确定删除该运单？',
          },
        ),
      ]),
  },
])

const tableScrollX = computed(() => sumTableColumnWidths(columns.value) + 96)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="shrink-0 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="page-h2">运单管理</h2>
        <p class="page-subtitle">
          共 {{ total }} 条 · 支持导入/导出运单 Excel
          <span v-if="batchShipmentSearchActive" class="text-violet-400">
            · 批量运单号 {{ shipmentNoTokens.length }} 个
          </span>
        </p>
      </div>
      <NSpace align="center">
        <NButton
          size="small"
          :loading="syncingTracking"
          title="同步转运中、未知、查验；已签收不查"
          @click="handleSyncTracking()"
        >
          更新全部内部轨迹
        </NButton>
        <NButton
          size="small"
          :loading="syncingCarrier"
          title="仅同步转运中运单，已签收不查"
          @click="handleSyncCarrierTracking()"
        >
          更新全部承运商轨迹
        </NButton>
        <NButton size="small" :loading="importing" @click="triggerImport">导入运单</NButton>
        <NButton size="small" :loading="exporting" @click="handleExport">导出运单</NButton>
      </NSpace>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls"
      class="hidden"
      @change="onFileSelected"
    />

    <ShipmentTrackingFreshnessBar
      :stats="freshnessStats"
      :internal-active="filterInternalFreshness"
      :carrier-active="filterCarrierFreshness"
      :carrier-ahead-active="filterCarrierAheadOfInternal"
      :filtered-carrier-ahead-count="filterCarrierAheadOfInternal ? total : null"
      :carrier-sync-hint="carrierSyncHint"
      @apply="applyFreshnessFilter"
      @clear="clearFreshnessFilter"
      @toggle-carrier-ahead="toggleCarrierAheadFilter"
    />

    <div class="panel shipments-filters-bar shrink-0 px-3 py-2">
      <div class="flex min-w-0 flex-col gap-2">
        <div class="flex min-w-0 flex-wrap items-center gap-2">
          <NInput
            v-model:value="searchShipmentNo"
            type="textarea"
            placeholder="运单号（逗号/换行）"
            :autosize="{ minRows: 1, maxRows: 3 }"
            clearable
            size="small"
            class="shipments-filter-shipment-no"
          />
          <NInput
            v-model:value="searchKeyword"
            placeholder="客户/订单号/地址"
            clearable
            size="small"
            class="shipments-filter-keyword"
          />
          <NInput
            v-model:value="searchTrackingContent"
            placeholder="轨迹内容（搜全部节点）"
            clearable
            size="small"
            class="shipments-filter-tracking"
          />
          <span class="shipments-filter-divider" aria-hidden="true" />
          <NSelect
            v-model:value="filterCustomer"
            :options="customerOptions"
            placeholder="客户"
            clearable
            filterable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterStatus"
            :options="statusOptions"
            placeholder="状态"
            clearable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NButton
            size="small"
            quaternary
            class="shrink-0"
            @click="filtersExpanded = !filtersExpanded"
          >
            {{ filtersExpanded ? '收起筛选' : '更多筛选' }}
            <span
              v-if="!filtersExpanded && advancedFiltersActiveCount > 0"
              class="ml-1 rounded bg-violet-500/25 px-1.5 text-[10px] text-violet-200"
            >
              {{ advancedFiltersActiveCount }}
            </span>
          </NButton>
          <NButton size="small" quaternary class="shrink-0" @click="resetFilters">重置</NButton>
        </div>
        <div
          v-show="filtersExpanded"
          class="flex min-w-0 flex-wrap items-center gap-2 border-t border-[var(--color-border)] pt-2"
        >
          <NSelect
            v-model:value="filterChannelNameZh"
            :options="channelNameZhOptions"
            placeholder="渠道（中文）"
            clearable
            filterable
            size="small"
            class="shipments-filter-select shipments-filter-select--wide"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterChannelCategory"
            :options="channelCategoryOptions"
            placeholder="大类"
            clearable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterCarrier"
            :options="carrierOptions"
            placeholder="承运商"
            clearable
            filterable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterCountry"
            :options="countryOptions"
            placeholder="国家"
            clearable
            filterable
            size="small"
            class="shipments-filter-select shipments-filter-select--wide"
            @update:value="onFiltersChanged"
          />
          <NSelect
            :value="filterHasException === true ? 'yes' : filterHasException === false ? 'no' : null"
            :options="hasExceptionFilterOptions"
            placeholder="异常"
            clearable
            size="small"
            class="shipments-filter-select"
            @update:value="onHasExceptionFilterChange"
          />
          <NSelect
            v-model:value="filterException"
            :options="exceptionFilterOptions"
            placeholder="异常类型"
            clearable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterStaleDays"
            :options="staleOptions"
            :disabled="filterNoTracking"
            placeholder="停滞"
            clearable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NCheckbox
            v-model:checked="filterNoTracking"
            size="small"
            class="shrink-0 whitespace-nowrap"
            @update:checked="onNoTrackingChanged"
          >
            无轨迹
          </NCheckbox>
        </div>
      </div>
    </div>

    <div class="panel shipments-table-panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :row-key="rowKey"
        :columns="columns"
        :data="items"
        :loading="loading"
        :scroll-x="tableScrollX"
        :scrollbar-props="tableScrollbarProps"
        size="small"
        flex-height
        class="shipments-data-table h-full"
        :bordered="false"
      />
    </div>

    <div
      v-if="selectedCount > 0"
      class="shipments-selection-bar shrink-0 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2"
    >
      <span class="shipments-selection-bar__label text-sm">
        已选
        <strong class="shipments-selection-bar__count">{{ selectedCount }}</strong>
        条（本页）
      </span>
      <NSpace size="small">
        <NButton size="small" quaternary @click="clearSelection">取消选择</NButton>
        <NButton size="small" @click="batchEditShow = true">批量修改</NButton>
        <NPopconfirm
          :positive-button-props="{ type: 'error' }"
          @positive-click="handleBatchDelete"
        >
          <template #trigger>
            <NButton size="small" type="error" :loading="batchSubmitting">批量删除</NButton>
          </template>
          确定删除所选 {{ selectedCount }} 条运单？关联轨迹将一并删除且不可恢复。
        </NPopconfirm>
        <NButton size="small" @click="copySelectedShipmentNos">复制运单号</NButton>
        <NButton size="small" @click="copySelectedLatestTracking">复制最新轨迹</NButton>
        <NButton
          size="small"
          :loading="syncingTracking"
          title="含已签收；按勾选运单号同步"
          @click="handleSyncSelectedInternal"
        >
          更新选中内部轨迹
        </NButton>
        <NButton
          size="small"
          type="primary"
          :loading="syncingCarrier"
          title="含已签收；按勾选运单号同步"
          @click="handleSyncSelectedCarrier"
        >
          更新选中承运商轨迹
        </NButton>
        <NButton
          size="small"
          type="warning"
          :loading="exceptionSubmitting"
          @click="exceptionOpenShow = true"
        >
          标记异常
        </NButton>
        <NButton
          size="small"
          :loading="exceptionSubmitting"
          @click="exceptionCloseShow = true"
        >
          解除异常
        </NButton>
      </NSpace>
    </div>

    <ShipmentBatchEditModal
      :show="batchEditShow"
      :count="selectedCount"
      :status-options="statusOptions"
      :channel-options="channelCodeOptions"
      :carrier-options="carrierOptions"
      :country-options="countryOptions"
      @close="batchEditShow = false"
      @submit="handleBatchEditSubmit"
    />

    <ShipmentExceptionOpenModal
      :show="exceptionOpenShow"
      :count="selectedCount"
      :exception-types="filterOptions.exceptionTypes"
      @close="exceptionOpenShow = false"
      @confirm="handleOpenException"
    />
    <ShipmentExceptionCloseModal
      :show="exceptionCloseShow"
      :count="selectedCount"
      @close="exceptionCloseShow = false"
      @confirm="handleCloseException"
    />

    <div class="shrink-0 flex justify-end border-t border-[var(--color-border)] pt-3">
      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[10, 20, 50, 100]"
        show-size-picker
        size="small"
      />
    </div>

    <ShipmentFormModal
      :show="modalShow"
      :mode="modalMode"
      :initial="editingRow"
      @close="modalShow = false"
      @submit="handleFormSubmit"
    />

    <ShipmentTrackingDrawer
      v-model:show="trackingDrawerShow"
      :shipment="trackingDrawerShipment"
      :initial-tab="trackingDrawerTab"
      :exception-label-by-code="exceptionLabelByCode"
    />
  </div>
</template>

<style scoped>
.shipments-filters-bar {
  border-radius: 0.5rem;
}

.shipments-filters-bar .shipments-filter-shipment-no {
  width: min(200px, 20vw);
  min-width: 132px;
  max-width: 220px;
  flex: 1 1 132px;
}

.shipments-filters-bar .shipments-filter-shipment-no :deep(.n-input__textarea-el) {
  min-height: 28px;
  line-height: 1.4;
}

.shipments-filters-bar .shipments-filter-keyword {
  width: min(152px, 16vw);
  min-width: 120px;
  flex: 0 1 152px;
}

.shipments-filters-bar .shipments-filter-tracking {
  width: min(200px, 22vw);
  min-width: 160px;
  flex: 1 1 160px;
}

.shipments-filters-bar .shipments-filter-select {
  width: 7.25rem;
  min-width: 6.5rem;
}

.shipments-filters-bar .shipments-filter-select--wide {
  width: 8.75rem;
  min-width: 7.5rem;
}

.shipments-filter-divider {
  width: 1px;
  height: 1.25rem;
  flex-shrink: 0;
  background: var(--color-border);
}

/* 左侧固定列：不透明 + 轻阴影，横滚时不与右侧双行轨迹叠字 */
.shipments-data-table :deep(.n-data-table-tbody .n-data-table-td--fixed-left) {
  background-color: var(--n-td-color) !important;
  z-index: 3;
  box-shadow: 6px 0 10px -6px rgb(0 0 0 / 0.45);
}

.shipments-data-table :deep(
    .n-data-table-tbody .n-data-table-tr:not(.n-data-table-tr--summary):hover > .n-data-table-td
  ) {
  background-color: var(--n-td-color-hover) !important;
}

.shipments-data-table :deep(
    .n-data-table-tbody
      .n-data-table-tr:not(.n-data-table-tr--summary):hover
      > .n-data-table-td--fixed-left
  ) {
  background-color: var(--n-td-color-hover) !important;
}

.shipments-data-table :deep(.shipment-td-no) {
  padding-right: 10px !important;
  overflow: hidden;
}

.shipments-data-table :deep(.shipment-no-cell-row) {
  display: inline-flex;
  max-width: 100%;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.shipments-data-table :deep(th.n-data-table-th--fixed-left) {
  background-color: var(--n-th-color) !important;
  z-index: 4;
}

.shipments-data-table :deep(.tracking-summary-cell) {
  line-height: 1.35;
}

.shipments-data-table :deep(.tracking-summary-btn) {
  border: none;
  background: transparent;
  font: inherit;
}

.shipments-data-table :deep(.tracking-summary-btn:hover) {
  background: var(--color-nav-hover);
}

.shipments-data-table :deep(.tracking-empty) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.tracking-time) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.tracking-time--faded) {
  color: var(--color-muted);
  opacity: 0.72;
}

.shipments-data-table :deep(.tracking-desc) {
  color: var(--color-fg);
}

.shipments-data-table :deep(.tracking-desc--faded) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.tracking-ahead-time) {
  color: var(--tracking-ahead-fg);
}

.shipments-data-table :deep(.tracking-ahead-desc) {
  color: var(--tracking-ahead-desc);
}

.shipments-data-table :deep(.tracking-ahead-badge) {
  border-radius: 4px;
  border: 1px solid var(--tracking-ahead-badge-border);
  background: var(--tracking-ahead-badge-bg);
  padding: 0 4px;
  font-size: 9px;
  font-weight: 500;
  color: var(--tracking-ahead-badge-fg);
}

.shipments-data-table :deep(.tracking-summary-btn--carrier-ahead) {
  border-left: 2px solid rgb(251 191 36 / 0.75);
  background: rgb(245 158 11 / 0.08);
  box-shadow: inset 0 0 0 1px rgb(245 158 11 / 0.12);
}

.shipments-data-table :deep(.tracking-summary-btn--carrier-ahead:hover) {
  background: rgb(245 158 11 / 0.14);
}

/* 内部相对滞后：略淡化，与承运高亮成对比 */
.shipments-data-table :deep(.tracking-summary-btn--internal-behind) {
  opacity: 0.82;
}

.shipments-data-table :deep(.shipment-no-cell) {
  display: inline-block;
  white-space: nowrap;
  word-break: keep-all;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.shipments-data-table :deep(.last-mile-badge-btn) {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  line-height: 0;
}

.shipments-selection-bar {
  border: 1px solid color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 14%, var(--color-elevated));
  color: var(--color-fg);
  box-shadow: var(--panel-inset-shadow);
}

.shipments-selection-bar__label {
  color: var(--color-fg);
  font-weight: 500;
}

.shipments-selection-bar__count {
  margin: 0 0.15em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.shipments-table-panel {
  display: flex;
  flex-direction: column;
}

.shipments-table-panel :deep(.n-data-table) {
  flex: 1;
  min-height: 0;
}

/* Naive 滚动条圆角、弱化轨道占位 */
.shipments-table-panel :deep(.n-scrollbar-rail__scrollbar) {
  border-radius: 9999px !important;
}
</style>
