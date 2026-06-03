<script setup lang="ts">
import {
  NButton,
  NCollapse,
  NCollapseItem,
  NDataTable,
  NDropdown,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type DropdownOption,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import CarrierVesselSelect from '@/components/vessel-schedules/CarrierVesselSelect.vue'
import VesselScheduleActiveBanner from '@/components/vessel-schedules/VesselScheduleActiveBanner.vue'
import VoyageFormModal from '@/components/vessel-schedules/VoyageFormModal.vue'
import VoyageTimeline from '@/components/vessel-schedules/VoyageTimeline.vue'
import {
  createVesselSchedule,
  deleteVesselSchedule,
  getVesselSchedule,
  importVesselScheduleExcel,
  listMaritimeScheduleProviders,
  listVesselSchedules,
  listVoyageShipments,
  syncAllExternalVesselSchedules,
  syncExternalVesselSchedule,
  updateVesselSchedule,
  vesselScheduleTemplateUrl,
} from '@/api/vesselSchedules'
import type {
  MaritimeScheduleProviderInfo,
  MaritimeStatus,
  VesselVoyageDetail,
  VesselVoyagePayload,
  VesselVoyageSummary,
  VoyageShipment,
} from '@/types/vesselSchedule'
import { MARITIME_STATUS_OPTIONS, maritimeStatusTagType } from '@/types/vesselSchedule'
import { apiErrorMessage } from '@/utils/apiError'
import { formatPortDisplay } from '@/utils/portDisplay'
import { resolveVesselName, resolveVoyageNo } from '@/utils/vesselVoyageDisplay'

const message = useMessage()
const dialog = useDialog()
const route = useRoute()
const syncModalShow = ref(false)
const loading = ref(false)
const detailLoading = ref(false)
const importing = ref(false)
const exporting = ref(false)
const voyages = ref<VesselVoyageSummary[]>([])
const selectedVesselName = ref<string | null>(null)
const selectedId = ref<string | null>(null)
const detail = ref<VesselVoyageDetail | null>(null)
const search = ref('')
const tableFilter = ref('')
const statusFilter = ref<MaritimeStatus | ''>('')
const shipments = ref<VoyageShipment[]>([])
const shipmentTotal = ref(0)

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const fileInputRef = ref<HTMLInputElement | null>(null)
const scheduleProviders = ref<MaritimeScheduleProviderInfo[]>([])
const syncCompany = ref('')
const syncVesselCode = ref('')
const syncVesselName = ref('')
const syncPeriod = ref(90)
const scheduleSyncing = ref(false)
const syncAllLoading = ref(false)

const providerOptions = computed(() =>
  scheduleProviders.value.map((p) => ({
    label: p.label,
    value: p.shippingCompany,
  })),
)

const syncProvider = computed(() =>
  scheduleProviders.value.find((p) => p.shippingCompany === syncCompany.value),
)

const syncVesselSearchEnabled = computed(() => Boolean(syncProvider.value?.features?.vesselSearch))

const vesselNameOptions = computed(() => {
  const names = new Set<string>()
  for (const v of voyages.value) {
    const name = resolveVesselName(v)
    if (name) names.add(name)
  }
  return [...names].sort().map((name) => ({ label: name, value: name }))
})

const voyageNoOptions = computed(() => {
  if (!selectedVesselName.value) return []
  return voyages.value
    .filter((v) => resolveVesselName(v) === selectedVesselName.value)
    .map((v) => ({
      label: `${resolveVoyageNo(v)} (${v.portCount ?? 0} Ports)`,
      value: v.id,
    }))
})

const moreMenuOptions = computed<DropdownOption[]>(() => [
  { label: '新建航次', key: 'create' },
  { label: '编辑当前航次', key: 'edit', disabled: !detail.value },
  { label: '导入 Excel', key: 'import' },
  { label: '下载模板', key: 'template' },
  { type: 'divider', key: 'd1' },
  { label: '同步单船船期', key: 'sync-one' },
  { label: '更新全部挂靠', key: 'sync-all' },
  {
    label: '从船公司更新挂靠',
    key: 'refresh-carrier',
    disabled: !detail.value?.vesselCode || !detail.value?.shippingCompany,
  },
  { type: 'divider', key: 'd2' },
  { label: '删除当前航次', key: 'delete', disabled: !selectedId.value },
])

function syncVesselNameFromSelectedId() {
  if (!selectedId.value) return
  const v = voyages.value.find((x) => x.id === selectedId.value)
  if (v) selectedVesselName.value = resolveVesselName(v)
}

const summary = computed(() => detail.value?.shipmentSummary)

async function loadVoyages() {
  loading.value = true
  try {
    const res = await listVesselSchedules({ search: search.value.trim() || undefined, limit: 200 })
    voyages.value = res.items
    if (selectedId.value && !res.items.some((v) => v.id === selectedId.value)) {
      selectedId.value = null
      selectedVesselName.value = null
    }
    if (selectedId.value) {
      syncVesselNameFromSelectedId()
    } else if (selectedVesselName.value) {
      const under = res.items.filter((v) => resolveVesselName(v) === selectedVesselName.value)
      if (under.length === 1) {
        selectedId.value = under[0].id
      } else if (!under.some((v) => v.id === selectedId.value)) {
        selectedId.value = null
      }
    } else if (res.items.length) {
      selectedVesselName.value = resolveVesselName(res.items[0])
      selectedId.value = res.items[0].id
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载航次列表失败')
  } finally {
    loading.value = false
  }
}

async function loadDetail() {
  if (!selectedId.value) {
    detail.value = null
    shipments.value = []
    shipmentTotal.value = 0
    return
  }
  detailLoading.value = true
  try {
    detail.value = await getVesselSchedule(selectedId.value)
    await loadShipments()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载航次详情失败')
  } finally {
    detailLoading.value = false
  }
}

async function loadShipments() {
  if (!selectedId.value) return
  try {
    const res = await listVoyageShipments(selectedId.value, {
      maritimeStatus: statusFilter.value || undefined,
      limit: 200,
    })
    shipments.value = res.items as VoyageShipment[]
    shipmentTotal.value = res.total
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载关联运单失败')
  }
}

async function handleRefresh() {
  await loadVoyages()
  await loadDetail()
}

onMounted(async () => {
  try {
    const res = await listMaritimeScheduleProviders()
    scheduleProviders.value = res.items
    if (!syncCompany.value && res.items.length) {
      syncCompany.value = res.items[0].shippingCompany
    }
  } catch {
    /* ignore */
  }
  const qStatus = route.query.maritimeStatus
  if (typeof qStatus === 'string' && qStatus) {
    statusFilter.value = qStatus as MaritimeStatus
  }
  await loadVoyages()
  const qVoyage = route.query.voyageId
  if (typeof qVoyage === 'string' && qVoyage) {
    selectedId.value = qVoyage
  }
  await loadDetail()
})

watch(selectedVesselName, (name, prev) => {
  if (name === prev) return
  if (!name) {
    selectedId.value = null
    return
  }
  const current = voyages.value.find((v) => v.id === selectedId.value)
  if (current && resolveVesselName(current) !== name) {
    selectedId.value = null
  }
  const under = voyages.value.filter((v) => resolveVesselName(v) === name)
  if (under.length === 1) {
    selectedId.value = under[0].id
  }
})

watch(selectedId, () => {
  syncVesselNameFromSelectedId()
  loadDetail()
})

watch(statusFilter, () => {
  loadShipments()
})

function openCreate() {
  modalMode.value = 'create'
  modalShow.value = true
}

function openEdit() {
  if (!detail.value) return
  modalMode.value = 'edit'
  modalShow.value = true
}

async function handleFormSubmit(payload: VesselVoyagePayload) {
  try {
    if (modalMode.value === 'create') {
      const saved = await createVesselSchedule(payload)
      message.success('航次已保存')
      selectedId.value = saved.id
      selectedVesselName.value = resolveVesselName(saved)
    } else if (selectedId.value) {
      const saved = await updateVesselSchedule(selectedId.value, payload)
      message.success('航次已保存')
      selectedVesselName.value = resolveVesselName(saved)
    }
    modalShow.value = false
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(apiErrorMessage(e, '保存失败'))
  }
}

async function handleDelete() {
  if (!selectedId.value) return
  try {
    await deleteVesselSchedule(selectedId.value)
    message.success('已删除航次')
    selectedId.value = null
    selectedVesselName.value = null
    detail.value = null
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除失败')
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function refreshDetailFromCarrier() {
  const d = detail.value
  if (!d?.vesselCode || !d?.shippingCompany) {
    message.warning('当前航次缺少船舶代码或船公司，请编辑后填写再拉取')
    return
  }
  scheduleSyncing.value = true
  try {
    const res = await syncExternalVesselSchedule(
      d.shippingCompany,
      d.vesselCode,
      syncPeriod.value,
    )
    selectedId.value = res.voyage.id
    selectedVesselName.value = resolveVesselName(res.voyage)
    const n = res.voyage.portCalls?.length ?? 0
    message.success(`已更新 ${n} 个挂靠港`)
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '船期更新失败')
  } finally {
    scheduleSyncing.value = false
  }
}

async function handleScheduleSyncAll() {
  syncAllLoading.value = true
  try {
    const res = await syncAllExternalVesselSchedules(syncPeriod.value)
    const parts = [
      `共 ${res.total} 条`,
      `成功 ${res.synced}`,
      res.created ? `新建 ${res.created}` : '',
      res.updated ? `更新 ${res.updated}` : '',
      res.failed ? `失败 ${res.failed}` : '',
      res.skippedUnsupported ? `未接入 ${res.skippedUnsupported}` : '',
      res.skippedIncomplete ? `缺代码 ${res.skippedIncomplete}` : '',
    ].filter(Boolean)
    if (res.failed && res.errors.length) {
      message.warning(
        `${parts.join('，')}；${res.errors
          .slice(0, 2)
          .map((e) => `${e.vesselCode}: ${e.message}`)
          .join('；')}`,
        { duration: 8000 },
      )
    } else if (res.synced === 0 && res.total === 0) {
      message.info('库内暂无已配置船公司 + 船舶代码的航次')
    } else {
      message.success(parts.join('，'))
    }
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '全库船期同步失败')
  } finally {
    syncAllLoading.value = false
  }
}

async function handleScheduleSync() {
  const company = syncCompany.value.trim()
  const code = syncVesselCode.value.trim().toUpperCase()
  if (!company) {
    message.warning('请选择船公司')
    return
  }
  if (!code) {
    message.warning('请输入船舶代码')
    return
  }
  scheduleSyncing.value = true
  try {
    const res = await syncExternalVesselSchedule(company, code, syncPeriod.value)
    const label =
      scheduleProviders.value.find((p) => p.shippingCompany === company)?.label || company
    message.success(res.created ? `已从 ${label} 新建航次` : `已从 ${label} 更新航次`)
    selectedId.value = res.voyage.id
    selectedVesselName.value = resolveVesselName(res.voyage)
    syncVesselCode.value = ''
    syncModalShow.value = false
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '船期同步失败')
  } finally {
    scheduleSyncing.value = false
  }
}

async function onImportFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  importing.value = true
  try {
    const res = await importVesselScheduleExcel(file)
    message.success(`导入完成：新增 ${res.created}，更新 ${res.updated}，失败 ${res.failed}`)
    if (res.errors.length) {
      message.warning(res.errors.slice(0, 3).map((x) => x.message).join('；'))
    }
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

function escapeCsvCell(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`
  return value
}

function handleExport() {
  if (!detail.value) {
    message.warning('请先选择航次')
    return
  }
  exporting.value = true
  try {
    const headers = ['Sequence', 'Port', 'ETD', 'ATD', 'ETA', 'ATA', 'Status']
    const rows = [...detail.value.portCalls]
      .sort((a, b) => a.sequence - b.sequence)
      .map((pc) =>
        [
          String(pc.sequence),
          formatPortDisplay(pc),
          pc.etd ?? '',
          pc.atd ?? '',
          pc.eta ?? '',
          pc.ata ?? '',
          pc.statusLabel || pc.status || '',
        ]
          .map(escapeCsvCell)
          .join(','),
      )
    const csv = [headers.join(','), ...rows].join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `port-schedule-${detail.value.vesselVoyage || 'voyage'}.csv`
    a.click()
    URL.revokeObjectURL(url)
    message.success('已导出挂靠港 CSV')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

function handleMoreMenu(key: string) {
  switch (key) {
    case 'create':
      openCreate()
      break
    case 'edit':
      openEdit()
      break
    case 'import':
      triggerImport()
      break
    case 'template':
      window.open(vesselScheduleTemplateUrl(), '_blank', 'noopener')
      break
    case 'sync-one':
      syncModalShow.value = true
      break
    case 'sync-all':
      handleScheduleSyncAll()
      break
    case 'refresh-carrier':
      refreshDetailFromCarrier()
      break
    case 'delete':
      if (!selectedId.value) return
      dialog.warning({
        title: '删除航次',
        content: '确定删除该航次及全部挂靠记录？',
        positiveText: '删除',
        negativeText: '取消',
        onPositiveClick: () => {
          handleDelete()
          return true
        },
      })
      break
    default:
      break
  }
}

const shipmentColumns: DataTableColumns<VoyageShipment> = [
  {
    title: '运单号',
    key: 'shipmentNo',
    minWidth: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: '客户',
    key: 'customer',
    width: 120,
    ellipsis: { tooltip: true },
  },
  {
    title: '起运港',
    key: 'originPortCode',
    width: 100,
    render: (row) => row.originPortCode || '—',
  },
  {
    title: '目的港',
    key: 'destinationPortCode',
    width: 100,
    render: (row) => row.destinationPortCode || '—',
  },
  {
    title: 'ETD',
    key: 'etd',
    width: 130,
    render: (row) => (row.etd ? row.etd.slice(0, 16) : '—'),
  },
  {
    title: 'ETA',
    key: 'eta',
    width: 130,
    render: (row) => (row.eta ? row.eta.slice(0, 16) : '—'),
  },
  {
    title: 'ATA',
    key: 'ata',
    width: 130,
    render: (row) => (row.ata ? row.ata.slice(0, 16) : '—'),
  },
  {
    title: '海运状态',
    key: 'maritimeStatusLabel',
    width: 120,
    render: (row) =>
      h(
        NTag,
        { size: 'small', type: maritimeStatusTagType(row.maritimeStatus), bordered: false },
        { default: () => row.maritimeStatusLabel || '待更新' },
      ),
  },
]
</script>

<template>
  <div class="vessel-schedules-page scrollbar-subtle h-full min-h-0 w-full overflow-y-auto">
    <section class="vessel-schedules-filter panel">
      <div class="vessel-schedules-filter__fields">
        <label class="vessel-schedules-filter__field">
          <span class="vessel-schedules-filter__label">Vessel Name</span>
          <NSelect
            v-model:value="selectedVesselName"
            :options="vesselNameOptions"
            filterable
            clearable
            placeholder="选择船名"
            :loading="loading"
          />
        </label>
        <label class="vessel-schedules-filter__field">
          <span class="vessel-schedules-filter__label">Voyage</span>
          <NSelect
            v-model:value="selectedId"
            :options="voyageNoOptions"
            filterable
            clearable
            placeholder="选择航次"
            :disabled="!selectedVesselName"
            :loading="loading"
          />
        </label>
        <label class="vessel-schedules-filter__field vessel-schedules-filter__field--grow">
          <span class="vessel-schedules-filter__label">Global Filter</span>
          <NInput
            v-model:value="tableFilter"
            placeholder="Port, carrier, or status..."
            clearable
          />
        </label>
        <label class="vessel-schedules-filter__field vessel-schedules-filter__field--grow">
          <span class="vessel-schedules-filter__label">搜索航次库</span>
          <NInput
            v-model:value="search"
            placeholder="船名 / 航次 / 船名航次 / 船舶代码"
            clearable
            @keyup.enter="loadVoyages"
          />
        </label>
      </div>
      <div class="vessel-schedules-filter__actions">
        <NButton
          class="vessel-schedules-toolbar-btn"
          :loading="loading || detailLoading"
          @click="handleRefresh"
        >
          <svg viewBox="0 0 20 20" fill="none" class="vessel-schedules-toolbar-btn__icon" aria-hidden="true">
            <path
              d="M16.5 10a6.5 6.5 0 1 1-1.9-4.6M16.5 4.5V10h-5.5"
              stroke="currentColor"
              stroke-width="1.35"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          Refresh
        </NButton>
        <NButton
          class="vessel-schedules-toolbar-btn"
          :loading="exporting"
          :disabled="!detail"
          @click="handleExport"
        >
          <svg viewBox="0 0 20 20" fill="none" class="vessel-schedules-toolbar-btn__icon" aria-hidden="true">
            <path
              d="M10 3.5v9M6.5 10 10 13.5 13.5 10M4.5 16.5h11"
              stroke="currentColor"
              stroke-width="1.35"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
          Export
        </NButton>
        <NDropdown trigger="click" :options="moreMenuOptions" @select="handleMoreMenu">
          <NButton class="vessel-schedules-toolbar-btn">更多</NButton>
        </NDropdown>
      </div>
      <input ref="fileInputRef" type="file" accept=".xlsx,.xls" class="hidden" @change="onImportFile" />
    </section>

    <div v-if="detailLoading" class="vessel-schedules-loading">加载中…</div>

    <template v-else-if="detail">
      <VesselScheduleActiveBanner
        :vessel-name="resolveVesselName(detail)"
        :voyage-no="resolveVoyageNo(detail)"
        :shipping-company="detail.shippingCompany"
        :port-calls="detail.portCalls"
      />

      <VoyageTimeline
        :vessel-voyage="detail.vesselVoyage"
        :shipping-company="detail.shippingCompany"
        :port-calls="detail.portCalls"
        :table-filter="tableFilter"
        @refresh="loadDetail"
      />

      <NCollapse v-if="shipmentTotal > 0 || summary" class="vessel-schedules-collapse">
        <NCollapseItem :title="`关联运单（${shipmentTotal} 票）`" name="shipments">
          <div v-if="summary" class="mb-3 flex flex-wrap gap-2">
            <NTag v-if="summary.arrivingSoon" type="warning" :bordered="false">
              三天内到港 {{ summary.arrivingSoon }}
            </NTag>
            <NTag v-if="summary.departingSoon" type="warning" :bordered="false">
              三天内离港 {{ summary.departingSoon }}
            </NTag>
            <NTag v-if="summary.arrived" type="success" :bordered="false">已到港 {{ summary.arrived }}</NTag>
            <NTag v-if="summary.inTransit" type="info" :bordered="false">在途 {{ summary.inTransit }}</NTag>
            <NTag v-if="summary.planned" :bordered="false">计划中 {{ summary.planned }}</NTag>
            <NTag v-if="summary.unknown" type="error" :bordered="false">待更新 {{ summary.unknown }}</NTag>
          </div>
          <div class="mb-3 flex justify-end">
            <NSelect
              v-model:value="statusFilter"
              :options="MARITIME_STATUS_OPTIONS"
              class="w-40"
              size="small"
            />
          </div>
          <NDataTable
            :columns="shipmentColumns"
            :data="shipments"
            :bordered="false"
            size="small"
            :scroll-x="900"
          />
        </NCollapseItem>
      </NCollapse>

    </template>

    <div v-else class="vessel-schedules-empty panel">
      暂无航次，请通过「更多」新建或导入 Excel
    </div>

    <VoyageFormModal
      v-model:show="modalShow"
      :mode="modalMode"
      :initial="modalMode === 'edit' ? detail : null"
      @submit="handleFormSubmit"
    />

    <NModal
      v-model:show="syncModalShow"
      preset="card"
      title="同步船期"
      class="max-w-lg"
      :mask-closable="!scheduleSyncing"
    >
      <div class="flex flex-col gap-3">
        <NSelect v-model:value="syncCompany" :options="providerOptions" placeholder="船公司" filterable />
        <CarrierVesselSelect
          v-if="syncVesselSearchEnabled"
          v-model:vessel-code="syncVesselCode"
          v-model:vessel-name="syncVesselName"
          :shipping-company="syncCompany"
          :enabled="syncVesselSearchEnabled"
          placeholder="输入船名检索"
        />
        <NInput v-else v-model:value="syncVesselCode" placeholder="船舶代码" @keyup.enter="handleScheduleSync" />
        <div class="flex items-center gap-2">
          <span class="text-sm text-[var(--color-muted)]">查询天数</span>
          <NInputNumber v-model:value="syncPeriod" class="w-24" :min="7" :max="90" />
        </div>
        <NButton type="primary" block :loading="scheduleSyncing" @click="handleScheduleSync">
          开始同步
        </NButton>
      </div>
    </NModal>
  </div>
</template>

<style scoped>
.vessel-schedules-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding-bottom: 0.5rem;
}

.vessel-schedules-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem 1.25rem;
  padding: 1rem 1.25rem;
}

.vessel-schedules-filter__fields {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 0.75rem 1rem;
  min-width: min(100%, 20rem);
}

.vessel-schedules-filter__field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  min-width: 10rem;
}

.vessel-schedules-filter__field--grow {
  flex: 1;
  min-width: 12rem;
}

.vessel-schedules-filter__label {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.vessel-schedules-filter__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.vessel-schedules-toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  background: rgb(70 72 212 / 0.06) !important;
  border: 1px solid rgb(70 72 212 / 0.14) !important;
  color: var(--color-fg-secondary) !important;
}

.vessel-schedules-toolbar-btn:hover {
  background: rgb(70 72 212 / 0.1) !important;
  color: var(--color-accent-text) !important;
}

.vessel-schedules-toolbar-btn__icon {
  width: 1rem;
  height: 1rem;
}

.vessel-schedules-loading,
.vessel-schedules-empty {
  padding: 3rem 1rem;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-muted);
}

.vessel-schedules-collapse :deep(.n-collapse-item__header) {
  font-weight: 600;
}

</style>
