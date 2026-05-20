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
import ShipmentExceptionHistory from '@/components/shipments/ShipmentExceptionHistory.vue'
import ShipmentExceptionCloseModal from '@/components/shipments/ShipmentExceptionCloseModal.vue'
import ShipmentExceptionOpenModal from '@/components/shipments/ShipmentExceptionOpenModal.vue'
import ShipmentTrackingPanel from '@/components/shipments/ShipmentTrackingPanel.vue'
import {
  closeShipmentExceptions,
  deleteShipment,
  exportShipmentsExcel,
  getShipmentFilterOptions,
  getShipmentTrackingLogs,
  getTrackingSyncDailyStats,
  importShipmentsExcel,
  listShipments,
  openShipmentExceptions,
  syncCarrierTracking,
  syncTracking,
  updateShipment,
} from '@/api/shipments'
import ShipmentFormModal from '@/components/shipments/ShipmentFormModal.vue'
import type { Shipment, ShipmentPayload } from '@/types/shipment'
import type { ShipmentFilterOptions } from '@/api/shipments'
import type { TrackingSyncDailyStats, TrackingSyncResult } from '@/types/tracking'
import { useDictLabels } from '@/composables/useDictLabels'
import { parseBatchSearchTokens } from '@/utils/parseBatchSearch'
import {
  hasEffectiveInternalTracking,
  isInternalNoTrackingDesc,
} from '@/utils/internalTracking'

const message = useMessage()
const { loadDictTypes, dictLabel } = useDictLabels()
const countryLabel = (raw: string | null | undefined) => dictLabel('country_code', raw)
const loading = ref(false)
const importing = ref(false)
const exporting = ref(false)
const syncingTracking = ref(false)
const syncingCarrier = ref(false)
const carrierDaily = ref<TrackingSyncDailyStats | null>(null)
const copyingTracking = ref(false)
const items = ref<Shipment[]>([])
const total = ref(0)
const searchShipmentNo = ref('')
const searchKeyword = ref('')
const DEFAULT_STATUS_FILTER = 'IN_TRANSIT'
const filterStatus = ref<string | null>(DEFAULT_STATUS_FILTER)
const filterCustomer = ref<string | null>(null)
const filterCarrier = ref<string | null>(null)
const filterCountry = ref<string | null>(null)
const filterChannel = ref<string | null>(null)
const filterStaleDays = ref<number | null>(null)
const filterNoTracking = ref(false)
const filterException = ref<string | null>(null)
const filterHasException = ref<boolean | null>(null)
const filterOptions = ref<ShipmentFilterOptions>({
  customers: [],
  carrierCodes: [],
  countryCodes: [],
  channelCodes: [],
  statusCodes: [],
  exceptionCodes: [],
  exceptionTypes: [],
})
const exceptionOpenShow = ref(false)
const exceptionCloseShow = ref(false)
const exceptionSubmitting = ref(false)
const page = ref(1)
const pageSize = ref(20)
const expandedRowKeys = ref<string[]>([])

const modalShow = ref(false)
const modalMode = ref<'edit'>('edit')
const editingRow = ref<Shipment | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const checkedRowKeys = ref<string[]>([])

const selectedCount = computed(() => checkedRowKeys.value.length)

const shipmentNoTokens = computed(() => parseBatchSearchTokens(searchShipmentNo.value))
const batchShipmentSearchActive = computed(() => shipmentNoTokens.value.length > 1)

/** 按当前页最长运单号估算列宽（略收窄，为其它列腾空间） */
const shipmentNoColWidth = computed(() => {
  let maxLen = 10
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.shipmentNo || '').length)
  }
  return Math.min(280, Math.max(152, Math.ceil(maxLen * 7) + 20))
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

function daysSince(time: string | null | undefined): number | null {
  if (!time?.trim()) return null
  const t = new Date(time.trim().replace(' ', 'T'))
  if (Number.isNaN(t.getTime())) return null
  return Math.floor((Date.now() - t.getTime()) / 86_400_000)
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

function rowClassName(row: Shipment) {
  return hasActiveException(row) ? 'shipment-row--exception' : ''
}

function renderTrackingSummaryCell(
  time: string | null | undefined,
  desc: string | null | undefined,
) {
  const t = (time || '').trim()
  const d = (desc || '').trim()
  if (!t && !d) {
    return h('span', { class: 'text-zinc-600' }, '—')
  }
  const block = h('div', { class: 'tracking-summary-cell min-w-0 max-w-full' }, [
    t
      ? h('div', { class: 'text-xs text-zinc-500 tabular-nums leading-tight' }, t)
      : null,
    d
      ? h(
          'div',
          { class: 'text-xs text-zinc-200 leading-snug truncate', title: d },
          d,
        )
      : h('div', { class: 'text-xs text-zinc-600' }, '—'),
  ])
  const tip = [t, d].filter(Boolean).join('\n')
  if (tip.length > 36) {
    return h(NTooltip, { trigger: 'hover' }, { trigger: () => block, default: () => tip })
  }
  return block
}

function renderShipmentNo(row: Shipment) {
  const active = hasActiveException(row)
  const label = exceptionLabel(row.exceptionCode)
  const duration = row.exceptionDurationLabel || '—'
  const cell = h(
    'span',
    {
      class: active
        ? 'shipment-no-cell shipment-no-cell--exception font-semibold'
        : 'shipment-no-cell font-medium text-zinc-100',
    },
    row.shipmentNo,
  )
  if (!active) return cell
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () => cell,
      default: () => `异常：${label} · 已持续 ${duration}`,
    },
  )
}

const exceptionColumns: DataTableColumns<Shipment> = [
  {
    title: '异常',
    key: 'exceptionCode',
    width: 100,
    align: 'center',
    render: (row) => {
      if (!row.exceptionCode) {
        return h('span', { class: 'text-zinc-600' }, '—')
      }
      const type = row.exceptionCode === 'LOST' ? 'error' : 'warning'
      return h(NTag, { size: 'small', bordered: false, type }, () => exceptionLabel(row.exceptionCode))
    },
  },
  {
    title: '异常时长',
    key: 'exceptionDurationLabel',
    width: 96,
    align: 'center',
    render: (row) => {
      if (!row.exceptionDurationLabel) {
        return h('span', { class: 'text-zinc-600' }, '—')
      }
      const secs = row.exceptionDurationSeconds ?? 0
      const long = secs >= 7 * 86_400
      return h(
        'span',
        { class: long ? 'text-red-300 text-xs font-medium' : 'text-amber-200/90 text-xs' },
        row.exceptionDurationLabel,
      )
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
const carrierOptions = computed(() =>
  filterOptions.value.carrierCodes.map((v) => ({ label: v, value: v })),
)
const countryOptions = computed(() =>
  filterOptions.value.countryCodes.map((code) => ({
    label: countryLabel(code) === code ? code : `${countryLabel(code)} (${code})`,
    value: code,
  })),
)
const channelOptions = computed(() =>
  filterOptions.value.channelCodes.map((v) => ({ label: v, value: v })),
)

/** 横向滚动宽度 = 各列 width 之和 + 余量（避免滑条到不了最右侧） */
function sumTableColumnWidths(cols: DataTableColumns<Shipment>): number {
  let total = 0
  for (const col of cols) {
    if (col.type === 'selection' || col.type === 'expand') {
      total += typeof col.width === 'number' ? col.width : 40
      continue
    }
    const w = 'width' in col ? col.width : undefined
    if (typeof w === 'number') total += w
  }
  return total
}

/** 运单表常显滚动条（Naive 默认隐藏原生条，用 Scrollbar 轨道） */
const tableScrollbarProps = {
  trigger: 'none' as const,
  size: 12,
  themeOverrides: {
    railColor: 'rgba(255, 255, 255, 0.06)',
    color: 'rgba(82, 82, 91, 0.95)',
    colorHover: 'rgba(161, 161, 170, 1)',
    height: '12px',
    width: '12px',
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
    channelCode: filterChannel.value || undefined,
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
  expandedRowKeys.value = []
  void loadList()
}

function onNoTrackingChanged(checked: boolean) {
  if (checked) filterStaleDays.value = null
  onFiltersChanged()
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchShipmentNo, searchKeyword], () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    checkedRowKeys.value = []
    expandedRowKeys.value = []
    void loadList()
  }, 300)
})

watch([page, pageSize], () => {
  checkedRowKeys.value = []
  expandedRowKeys.value = []
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
    await updateShipment(editingRow.value.id, payload)
    message.success('运单已更新')
    modalShow.value = false
    await loadList()
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

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleSyncTracking(shipmentNos?: string[]) {
  syncingTracking.value = true
  try {
    const res = await syncTracking(shipmentNos)
    notifyTrackingSyncResult(res, '内部轨迹')
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
  filterChannel.value = null
  filterStaleDays.value = null
  filterNoTracking.value = false
  searchShipmentNo.value = ''
  searchKeyword.value = ''
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
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  await handleSyncTracking(nos)
}

async function handleSyncSelectedCarrier() {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
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

/** 复制格式：运单号 = 客户订单号 = 地址代码 = 件数ctns → 物流时间 → 物流轨迹 */
function formatTrackingCopyBlock(
  row: Shipment,
  tracking: { desc: string; time: string },
): string {
  const head = [
    displayField(row.shipmentNo),
    displayField(row.customerNo),
    displayField(row.addressCode),
    formatCtnsField(row.ctns),
  ].join(' = ')
  return `${head}\n${tracking.time}\n${tracking.desc}`
}

async function resolveLatestTracking(row: Shipment): Promise<{ desc: string; time: string }> {
  if (hasEffectiveInternalTracking(row)) {
    return {
      desc: row.latestTrackingDesc?.trim() || '—',
      time: row.latestTrackingTime?.trim() || '—',
    }
  }
  const res = await getShipmentTrackingLogs(row.id, { limit: 20, offset: 0 })
  const log = res.items.find((item) => !isInternalNoTrackingDesc(item.trackingDesc))
  if (!log) {
    return { desc: '—', time: '—' }
  }
  return {
    desc: log.trackingDesc?.trim() || '—',
    time: log.trackingTime?.trim() || '—',
  }
}

async function copySelectedLatestTracking() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  copyingTracking.value = true
  try {
    const blocks = await Promise.all(
      rows.map(async (row) => {
        const tracking = await resolveLatestTracking(row)
        return formatTrackingCopyBlock(row, tracking)
      }),
    )
    await navigator.clipboard.writeText(blocks.join('\n\n'))
    message.success(`已复制 ${rows.length} 条最新轨迹`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '复制失败')
  } finally {
    copyingTracking.value = false
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
    type: 'expand',
    fixed: 'left',
    width: 40,
    renderExpand: (row) =>
      h('div', {}, [
        h(ShipmentTrackingPanel, { shipmentId: row.id }),
        h(ShipmentExceptionHistory, {
          shipmentId: row.id,
          labelByCode: exceptionLabelByCode.value,
        }),
      ]),
  },
  {
    title: '运单号',
    key: 'shipmentNo',
    width: shipmentNoColWidth.value,
    minWidth: 152,
    fixed: 'left',
    cellProps: (row) =>
      hasActiveException(row) ? { class: 'shipment-td-exception-no' } : {},
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
    title: '国家',
    key: 'countryCode',
    width: 96,
    ellipsis: { tooltip: true },
    render: (row) => countryLabel(row.countryCode),
  },
  { title: '渠道', key: 'channelCode', width: 160, ellipsis: { tooltip: true } },
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
        return h('span', { class: 'text-zinc-600' }, '—')
      }
      return renderTrackingSummaryCell(row.latestTrackingTime, row.latestTrackingDesc)
    },
  },
  {
    title: '承运商轨迹',
    key: 'latestCarrier',
    width: 220,
    ellipsis: { tooltip: true },
    render: (row) =>
      renderTrackingSummaryCell(row.latestCarrierTime, row.latestCarrierDesc),
  },
  {
    title: '未更新',
    key: 'staleDays',
    width: 72,
    align: 'center',
    render: (row) => {
      const d = hasEffectiveInternalTracking(row) ? daysSince(row.latestTrackingTime) : null
      if (d === null) {
        return h('span', { class: 'text-zinc-600' }, '—')
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
  { title: '更新时间', key: 'updatedTime', width: 160 },
  ...exceptionColumns,
  {
    title: '操作',
    key: 'actions',
    width: 128,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
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
        <h2 class="text-lg font-semibold text-white">运单管理</h2>
        <p class="text-xs text-zinc-500">
          共 {{ total }} 条 · 支持导入/导出运单 Excel
          <span v-if="batchShipmentSearchActive" class="text-violet-400">
            · 批量运单号 {{ shipmentNoTokens.length }} 个
          </span>
        </p>
      </div>
      <NSpace align="center">
        <NButton size="small" :loading="syncingTracking" @click="handleSyncTracking()">
          更新全部内部轨迹
        </NButton>
        <NButton size="small" :loading="syncingCarrier" @click="handleSyncCarrierTracking()">
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

    <div
      v-if="carrierDaily"
      class="shrink-0 rounded-lg border border-sky-500/25 bg-sky-500/10 px-3 py-2 text-xs text-zinc-300"
    >
      承运商轨迹 · 今日已更新
      <strong class="text-white">{{ carrierDaily.updatedShipments }}</strong>
      单，新增
      <strong class="text-white">{{ carrierDaily.newLogCount }}</strong>
      条节点
      <span v-if="carrierDaily.lastFinished" class="text-zinc-500">
        · 上次同步 {{ carrierDaily.lastFinished }}
      </span>
    </div>

    <div class="panel shipments-filters-bar shrink-0 px-3 py-2">
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
          placeholder="订单号/地址/轨迹"
          clearable
          size="small"
          class="shipments-filter-keyword"
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
          v-model:value="filterChannel"
          :options="channelOptions"
          placeholder="渠道"
          clearable
          filterable
          size="small"
          class="shipments-filter-select shipments-filter-select--wide"
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
        <NButton size="small" quaternary class="shrink-0" @click="resetFilters">重置</NButton>
      </div>
    </div>

    <div class="panel shipments-table-panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        v-model:expanded-row-keys="expandedRowKeys"
        :row-key="rowKey"
        :row-class-name="rowClassName"
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
      class="shrink-0 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-2"
    >
      <span class="text-sm text-zinc-300">
        已选 <strong class="text-white">{{ selectedCount }}</strong> 条（本页）
      </span>
      <NSpace size="small">
        <NButton size="small" quaternary @click="clearSelection">取消选择</NButton>
        <NButton size="small" @click="copySelectedShipmentNos">复制运单号</NButton>
        <NButton size="small" :loading="copyingTracking" @click="copySelectedLatestTracking">
          查询并复制最新轨迹
        </NButton>
        <NButton size="small" :loading="syncingTracking" @click="handleSyncSelectedInternal">
          更新选中内部轨迹
        </NButton>
        <NButton size="small" type="primary" :loading="syncingCarrier" @click="handleSyncSelectedCarrier">
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

/* 左侧固定列不透明，横向滚动时不透底 */
.shipments-data-table :deep(td.n-data-table-td--fixed-left) {
  background-color: var(--n-td-color) !important;
  z-index: 2;
}

.shipments-data-table :deep(th.n-data-table-th--fixed-left) {
  background-color: var(--n-th-color) !important;
  z-index: 4;
}

.shipments-data-table :deep(.tracking-summary-cell) {
  line-height: 1.35;
}

.shipments-data-table :deep(.shipment-no-cell) {
  display: inline-block;
  white-space: nowrap;
  word-break: keep-all;
  font-variant-numeric: tabular-nums;
}

.shipments-data-table :deep(.shipment-no-cell--exception) {
  color: rgb(253 230 138);
}

/* 异常行：不透明底色，避免横向滚动时与后方列文字叠在一起 */
.shipments-data-table :deep(tr.shipment-row--exception td) {
  background: #1a1814 !important;
}

.shipments-data-table :deep(tr.shipment-row--exception:hover td) {
  background: #221e17 !important;
}

.shipments-data-table :deep(tr.shipment-row--exception .n-data-table-td--fixed-left),
.shipments-data-table :deep(tr.shipment-row--exception .n-data-table-th--fixed-left) {
  z-index: 3;
}

.shipments-data-table :deep(.shipment-td-exception-no) {
  box-shadow: inset 3px 0 0 rgb(245 158 11 / 0.95);
}

/* 运单表底部/右侧常显滚动条（Naive 默认 hover 才显示） */
.shipments-table-panel {
  display: flex;
  flex-direction: column;
}

.shipments-table-panel :deep(.n-data-table) {
  flex: 1;
  min-height: 0;
}

.shipments-table-panel :deep(.n-scrollbar-rail--horizontal) {
  height: 12px !important;
  opacity: 1 !important;
}

.shipments-table-panel :deep(.n-scrollbar-rail--horizontal .n-scrollbar-rail__scrollbar) {
  height: 8px !important;
  border-radius: 4px;
}

.shipments-table-panel :deep(.n-scrollbar-rail--vertical) {
  width: 12px !important;
  opacity: 1 !important;
}

.shipments-table-panel :deep(.n-scrollbar-rail--vertical .n-scrollbar-rail__scrollbar) {
  width: 8px !important;
  border-radius: 4px;
}
</style>
