<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NInput,
  NPopconfirm,
  NSelect,
  NSpace,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import VoyageFormModal from '@/components/vessel-schedules/VoyageFormModal.vue'
import VoyageTimeline from '@/components/vessel-schedules/VoyageTimeline.vue'
import {
  createVesselSchedule,
  deleteVesselSchedule,
  getVesselSchedule,
  importVesselScheduleExcel,
  listVesselSchedules,
  listVoyageShipments,
  updateVesselSchedule,
  vesselScheduleTemplateUrl,
} from '@/api/vesselSchedules'
import type {
  MaritimeStatus,
  VesselVoyageDetail,
  VesselVoyagePayload,
  VesselVoyageSummary,
  VoyageShipment,
} from '@/types/vesselSchedule'
import { MARITIME_STATUS_OPTIONS, maritimeStatusTagType } from '@/types/vesselSchedule'

const message = useMessage()
const route = useRoute()
const loading = ref(false)
const detailLoading = ref(false)
const importing = ref(false)
const voyages = ref<VesselVoyageSummary[]>([])
const selectedId = ref<string | null>(null)
const detail = ref<VesselVoyageDetail | null>(null)
const search = ref('')
const statusFilter = ref<MaritimeStatus | ''>('')
const shipments = ref<VoyageShipment[]>([])
const shipmentTotal = ref(0)

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const fileInputRef = ref<HTMLInputElement | null>(null)

const voyageOptions = computed(() =>
  voyages.value.map((v) => ({
    label: `${v.vesselVoyage}（${v.shipmentCount ?? 0} 票）`,
    value: v.id,
  })),
)

const summary = computed(() => detail.value?.shipmentSummary)

async function loadVoyages() {
  loading.value = true
  try {
    const res = await listVesselSchedules({ search: search.value.trim() || undefined, limit: 200 })
    voyages.value = res.items
    if (!selectedId.value && res.items.length) {
      selectedId.value = res.items[0].id
    } else if (selectedId.value && !res.items.some((v) => v.id === selectedId.value)) {
      selectedId.value = res.items[0]?.id ?? null
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

onMounted(async () => {
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

watch(selectedId, () => {
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
      const created = await createVesselSchedule(payload)
      message.success('航次已创建')
      selectedId.value = created.id
    } else if (selectedId.value) {
      await updateVesselSchedule(selectedId.value, payload)
      message.success('航次已更新')
    }
    modalShow.value = false
    await loadVoyages()
    await loadDetail()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function handleDelete() {
  if (!selectedId.value) return
  try {
    await deleteVesselSchedule(selectedId.value)
    message.success('已删除航次')
    selectedId.value = null
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
  <div class="mx-auto max-w-7xl space-y-6 p-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="page-h1">船期监控</h1>
        <p class="mt-1 text-sm text-zinc-500">
          维护船名航次挂靠计划，按 vessel_voyage 关联运单并查看海运动态
        </p>
      </div>
      <NSpace>
        <NButton tag="a" :href="vesselScheduleTemplateUrl()" target="_blank" rel="noopener">
          下载模板
        </NButton>
        <NButton :loading="importing" @click="triggerImport">导入 Excel</NButton>
        <NButton type="primary" @click="openCreate">新建航次</NButton>
      </NSpace>
      <input ref="fileInputRef" type="file" accept=".xlsx,.xls" class="hidden" @change="onImportFile" />
    </div>

    <div class="flex flex-wrap items-end gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] p-4">
      <div class="min-w-[280px] flex-1">
        <div class="mb-1 text-xs text-zinc-500">选择航次</div>
        <NSelect
          v-model:value="selectedId"
          :options="voyageOptions"
          filterable
          placeholder="选择船名航次"
          :loading="loading"
        />
      </div>
      <div class="min-w-[200px] flex-1">
        <div class="mb-1 text-xs text-zinc-500">搜索航次</div>
        <NInput v-model:value="search" placeholder="船名航次 / 备注" @keyup.enter="loadVoyages" />
      </div>
      <NButton :loading="loading" @click="loadVoyages">刷新列表</NButton>
      <NButton v-if="detail" :disabled="detailLoading" @click="openEdit">编辑</NButton>
      <NPopconfirm v-if="selectedId" @positive-click="handleDelete">
        <template #trigger>
          <NButton type="error" quaternary>删除</NButton>
        </template>
        确定删除该航次及全部挂靠记录？
      </NPopconfirm>
    </div>

    <div v-if="detailLoading" class="py-12 text-center text-zinc-500">加载中…</div>

    <template v-else-if="detail">
      <VoyageTimeline :vessel-voyage="detail.vesselVoyage" :port-calls="detail.portCalls" />

      <div v-if="summary" class="flex flex-wrap gap-2">
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
        <span class="self-center text-xs text-zinc-500">
          关联运单 {{ detail.shipmentCount ?? 0 }} 票
        </span>
      </div>

      <div class="rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] p-4">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 class="section-h2">关联运单</h2>
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
        <p class="mt-2 text-xs text-zinc-500">共 {{ shipmentTotal }} 票（按运单 vessel_voyage 精确匹配）</p>
      </div>
    </template>

    <div v-else class="rounded-xl border border-dashed border-[var(--color-border)] py-16 text-center text-zinc-500">
      暂无航次，请新建或导入 Excel
    </div>

    <VoyageFormModal
      v-model:show="modalShow"
      :mode="modalMode"
      :initial="modalMode === 'edit' ? detail : null"
      @submit="handleFormSubmit"
    />
  </div>
</template>
