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
  getShipmentTrackingLogs,
  importShipmentsExcel,
  listShipments,
  syncTracking,
  updateShipment,
} from '@/api/shipments'
import ShipmentFormModal from '@/components/shipments/ShipmentFormModal.vue'
import type { Shipment, ShipmentPayload } from '@/types/shipment'
import type { TrackingSyncResult } from '@/types/tracking'

const message = useMessage()
const loading = ref(false)
const importing = ref(false)
const syncingTracking = ref(false)
const copyingTracking = ref(false)
const items = ref<Shipment[]>([])
const total = ref(0)
const search = ref('')
const filterStatus = ref<string | null>(null)
const filterStaleDays = ref<number | null>(null)
const filterNoTracking = ref(false)
const page = ref(1)
const pageSize = ref(20)
const expandedRowKeys = ref<string[]>([])

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingRow = ref<Shipment | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const checkedRowKeys = ref<string[]>([])

const selectedCount = computed(() => checkedRowKeys.value.length)

const selectedShipmentNos = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)).map((row) => row.shipmentNo),
)

const selectedRows = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)),
)

function rowKey(row: Shipment) {
  return row.id
}

function formatTrackingMessage(res: TrackingSyncResult) {
  const errHint = res.errors.length ? `；接口错误 ${res.errors.length} 条` : ''
  return (
    `轨迹已更新：${res.updated}/${res.total} 单（${res.batches} 批×${res.batchSize}），新增 ${res.logCount} 条` +
    (res.skipped ? `，跳过 ${res.skipped} 单` : '') +
    (res.notFound ? `，未返回 ${res.notFound} 单` : '') +
    (res.empty ? `，无轨迹 ${res.empty} 单` : '') +
    errHint
  )
}

function daysSince(time: string | null | undefined): number | null {
  if (!time?.trim()) return null
  const t = new Date(time.trim().replace(' ', 'T'))
  if (Number.isNaN(t.getTime())) return null
  return Math.floor((Date.now() - t.getTime()) / 86_400_000)
}

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '转运中', value: 'IN_TRANSIT' },
  { label: '已签收', value: 'DELIVERED' },
  { label: '查验', value: 'INSPECTION' },
  { label: '未知', value: 'UNKNOWN' },
]

const staleOptions = [
  { label: '≥7 天未更新', value: 7 },
  { label: '≥14 天未更新', value: 14 },
  { label: '≥30 天未更新', value: 30 },
]

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

const statusLabel: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

const addressTypeColor: Record<string, 'info' | 'warning' | 'success' | 'default'> = {
  AMZ: 'warning',
  WFS: 'info',
  '3PL': 'success',
}

async function loadList() {
  loading.value = true
  try {
    const res = await listShipments({
      search: search.value.trim() || undefined,
      statusCode: filterStatus.value || undefined,
      minStaleDays: filterNoTracking.value ? undefined : filterStaleDays.value ?? undefined,
      noTracking: filterNoTracking.value || undefined,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = res.items
    total.value = res.total
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadList, 300)
})

watch([page, pageSize], () => {
  checkedRowKeys.value = []
  expandedRowKeys.value = []
  loadList()
})

watch([filterStatus, filterStaleDays, filterNoTracking], () => {
  page.value = 1
  loadList()
})

watch(filterNoTracking, (v) => {
  if (v) filterStaleDays.value = null
})

onMounted(loadList)

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
    message.success(formatTrackingMessage(res), { duration: 6000 })
    if (res.errors.length) {
      console.warn('sync-tracking errors', res.errors)
    }
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新轨迹失败')
  } finally {
    syncingTracking.value = false
  }
}

function resetFilters() {
  filterStatus.value = null
  filterStaleDays.value = null
  filterNoTracking.value = false
  search.value = ''
  page.value = 1
  loadList()
}

async function handleSyncSelected() {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  await handleSyncTracking(nos)
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
  if (row.latestTrackingDesc?.trim() || row.latestTrackingTime?.trim()) {
    return {
      desc: row.latestTrackingDesc?.trim() || '—',
      time: row.latestTrackingTime?.trim() || '—',
    }
  }
  const res = await getShipmentTrackingLogs(row.id, { limit: 1, offset: 0 })
  const log = res.items[0]
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
    width: 140,
    fixed: 'left',
    ellipsis: { tooltip: true },
    render: (row) => h('span', { class: 'font-medium text-zinc-100' }, row.shipmentNo),
  },
  { title: '客户', key: 'customer', width: 100, ellipsis: { tooltip: true } },
  { title: '客户订单号', key: 'customerNo', width: 130, ellipsis: { tooltip: true } },
  { title: '件数', key: 'ctns', width: 64, align: 'center' },
  { title: '国家', key: 'countryCode', width: 72 },
  {
    title: '类型',
    key: 'addressType',
    width: 72,
    render: (row) =>
      row.addressType
        ? h(
            NTag,
            { size: 'small', bordered: false, type: addressTypeColor[row.addressType] || 'default' },
            () => row.addressType,
          )
        : '—',
  },
  { title: '渠道', key: 'channelCode', width: 160, ellipsis: { tooltip: true } },
  { title: '承运商', key: 'carrierCode', width: 90, ellipsis: { tooltip: true } },
  { title: '派送地址', key: 'deliveryAddress', width: 180, ellipsis: { tooltip: true } },
  { title: '交货仓库', key: 'originWarehouseCode', width: 90, ellipsis: { tooltip: true } },
  {
    title: '最新轨迹时间',
    key: 'latestTrackingTime',
    width: 152,
    ellipsis: { tooltip: true },
    render: (row) => row.latestTrackingTime || '—',
  },
  {
    title: '最新轨迹',
    key: 'latestTrackingDesc',
    width: 200,
    ellipsis: { tooltip: true },
    render: (row) => row.latestTrackingDesc || '—',
  },
  {
    title: '未更新',
    key: 'staleDays',
    width: 72,
    align: 'center',
    render: (row) => {
      const d = daysSince(row.latestTrackingTime)
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
  {
    title: '状态',
    key: 'statusCode',
    width: 88,
    render: (row) =>
      h(
        NTag,
        { size: 'small', bordered: false, type: row.statusCode === 'DELIVERED' ? 'success' : 'default' },
        () => statusLabel[row.statusCode || ''] || row.statusCode || '—',
      ),
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
        <p class="text-xs text-zinc-500">共 {{ total }} 条 · 支持 Excel 按运单号 upsert</p>
      </div>
      <NSpace>
        <NInput
          v-model:value="search"
          placeholder="搜索运单号、客户、地址…"
          clearable
          size="small"
          class="w-56"
        />
        <NButton size="small" :loading="syncingTracking" @click="handleSyncTracking()">
          更新所有轨迹
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

    <div class="shrink-0 flex flex-wrap items-center gap-2">
      <NSelect
        v-model:value="filterStatus"
        :options="statusOptions"
        placeholder="状态"
        clearable
        size="small"
        class="w-28"
      />
      <NSelect
        v-model:value="filterStaleDays"
        :options="staleOptions"
        :disabled="filterNoTracking"
        placeholder="停滞"
        clearable
        size="small"
        class="w-36"
      />
      <NCheckbox v-model:checked="filterNoTracking" size="small">无轨迹</NCheckbox>
      <NButton size="small" quaternary @click="resetFilters">重置筛选</NButton>
    </div>

    <div class="panel shipments-table-panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        v-model:expanded-row-keys="expandedRowKeys"
        :row-key="rowKey"
        :columns="columns"
        :data="items"
        :loading="loading"
        :scroll-x="1880"
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
        <NButton size="small" type="primary" :loading="syncingTracking" @click="handleSyncSelected">
          更新选中轨迹
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
