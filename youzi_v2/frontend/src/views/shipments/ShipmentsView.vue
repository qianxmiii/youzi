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
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import ShipmentTrackingPanel from '@/components/shipments/ShipmentTrackingPanel.vue'
import {
  createShipment,
  deleteShipment,
  getShipmentFilterOptions,
  getShipmentTrackingLogs,
  getTrackingSyncDailyStats,
  importShipmentsExcel,
  listShipments,
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
const syncingTracking = ref(false)
const syncingCarrier = ref(false)
const carrierDaily = ref<TrackingSyncDailyStats | null>(null)
const copyingTracking = ref(false)
const items = ref<Shipment[]>([])
const total = ref(0)
const searchShipmentNo = ref('')
const searchKeyword = ref('')
/** 承运商轨迹同步：指定运单号（逗号/换行）；留空则全库在途 */
const carrierTrackingInput = ref('')
const filterStatus = ref<string | null>(null)
const filterCustomer = ref<string | null>(null)
const filterCarrier = ref<string | null>(null)
const filterCountry = ref<string | null>(null)
const filterChannel = ref<string | null>(null)
const filterStaleDays = ref<number | null>(null)
const filterNoTracking = ref(false)
const filterOptions = ref<ShipmentFilterOptions>({
  customers: [],
  carrierCodes: [],
  countryCodes: [],
  channelCodes: [],
  statusCodes: [],
})
const page = ref(1)
const pageSize = ref(20)
const expandedRowKeys = ref<string[]>([])

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingRow = ref<Shipment | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const checkedRowKeys = ref<string[]>([])

const selectedCount = computed(() => checkedRowKeys.value.length)

const shipmentNoTokens = computed(() => parseBatchSearchTokens(searchShipmentNo.value))
const batchShipmentSearchActive = computed(() => shipmentNoTokens.value.length > 1)
const carrierTrackingTokens = computed(() => parseBatchSearchTokens(carrierTrackingInput.value))

/** 按当前页最长运单号估算列宽，避免截断 */
const shipmentNoColWidth = computed(() => {
  let maxLen = 10
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.shipmentNo || '').length)
  }
  return Math.min(400, Math.max(200, Math.ceil(maxLen * 8.5) + 28))
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

const statusOptions = computed(() =>
  filterOptions.value.statusCodes.map((code) => ({
    label: statusLabel[code] || code,
    value: code,
  })),
)

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

function openCreate() {
  modalMode.value = 'create'
  editingRow.value = null
  modalShow.value = true
}

function openEdit(row: Shipment) {
  modalMode.value = 'edit'
  editingRow.value = row
  modalShow.value = true
}

async function handleFormSubmit(payload: ShipmentPayload) {
  try {
    if (modalMode.value === 'create') {
      await createShipment(payload)
      message.success('运单已创建')
    } else if (editingRow.value) {
      await updateShipment(editingRow.value.id, payload)
      message.success('运单已更新')
    }
    modalShow.value = false
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
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

async function handleSyncCarrierTrackingFromInput() {
  const tokens = carrierTrackingTokens.value
  if (tokens.length) {
    await handleSyncCarrierTracking(tokens)
    return
  }
  await handleSyncCarrierTracking()
}

function onCarrierTrackingInputKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    void handleSyncCarrierTrackingFromInput()
  }
}

function resetFilters() {
  filterStatus.value = null
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
    message.success(`导入完成：新增 ${res.created}，更新 ${res.updated}，失败 ${res.failed}`)
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
    renderExpand: (row) => h(ShipmentTrackingPanel, { shipmentId: row.id }),
  },
  {
    title: '运单号',
    key: 'shipmentNo',
    width: shipmentNoColWidth.value,
    minWidth: 200,
    fixed: 'left',
    render: (row) =>
      h('span', { class: 'shipment-no-cell font-medium text-zinc-100' }, row.shipmentNo),
  },
  { title: '客户', key: 'customer', width: 100, ellipsis: { tooltip: true } },
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
  { title: '派送地址', key: 'deliveryAddress', width: 180, ellipsis: { tooltip: true } },
  {
    title: '内部轨迹时间',
    key: 'latestTrackingTime',
    width: 152,
    ellipsis: { tooltip: true },
    render: (row) => (hasEffectiveInternalTracking(row) ? row.latestTrackingTime : null) || '—',
  },
  {
    title: '内部最新轨迹',
    key: 'latestTrackingDesc',
    width: 180,
    ellipsis: { tooltip: true },
    render: (row) => (hasEffectiveInternalTracking(row) ? row.latestTrackingDesc : null) || '—',
  },
  {
    title: '承运商轨迹时间',
    key: 'latestCarrierTime',
    width: 152,
    ellipsis: { tooltip: true },
    render: (row) => row.latestCarrierTime || '—',
  },
  {
    title: '承运商最新轨迹',
    key: 'latestCarrierDesc',
    width: 180,
    ellipsis: { tooltip: true },
    render: (row) => row.latestCarrierDesc || '—',
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
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="shrink-0 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-white">运单管理</h2>
        <p class="text-xs text-zinc-500">
          共 {{ total }} 条 · 支持 Excel 按运单号 upsert
          <span v-if="batchShipmentSearchActive" class="text-violet-400">
            · 批量运单号 {{ shipmentNoTokens.length }} 个
          </span>
        </p>
      </div>
      <NSpace align="center">
        <NButton size="small" :loading="syncingTracking" @click="handleSyncTracking()">
          更新内部轨迹
        </NButton>
        <NInput
          v-model:value="carrierTrackingInput"
          type="textarea"
          placeholder="承运商轨迹运单号（逗号/换行，留空=全库在途）"
          :autosize="{ minRows: 1, maxRows: 2 }"
          clearable
          size="small"
          class="carrier-tracking-query-input"
          @keydown="onCarrierTrackingInputKeydown"
        />
        <NButton
          size="small"
          :loading="syncingCarrier"
          @click="handleSyncCarrierTrackingFromInput"
        >
          更新承运商轨迹
          <span v-if="carrierTrackingTokens.length" class="opacity-80">
            ({{ carrierTrackingTokens.length }})
          </span>
        </NButton>
        <NButton size="small" :loading="importing" @click="triggerImport">
          导入 Excel
        </NButton>
        <NButton size="small" type="primary" @click="openCreate">新增运单</NButton>
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
        :columns="columns"
        :data="items"
        :loading="loading"
        :scroll-x="1900 + shipmentNoColWidth"
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
      </NSpace>
    </div>

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
.carrier-tracking-query-input {
  width: min(280px, 32vw);
  min-width: 200px;
}

.carrier-tracking-query-input :deep(.n-input__textarea-el) {
  min-height: 28px;
  line-height: 1.4;
}

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

.shipments-data-table :deep(.shipment-no-cell) {
  display: inline-block;
  white-space: nowrap;
  word-break: keep-all;
  font-variant-numeric: tabular-nums;
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
