<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NInput,
  NPagination,
  NPopconfirm,
  NSpace,
  NTabPane,
  NTabs,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  codeTableTemplateUrl,
  createCodeTableRow,
  deleteCodeTableRow,
  importCodeTableExcel,
  listCodeTableRows,
  listCodeTableTypes,
  updateCodeTableRow,
} from '@/api/codeTables'
import CodeTableFormModal from '@/components/admin/CodeTableFormModal.vue'
import ChannelsView from '@/views/channels/ChannelsView.vue'
import { shipmentExceptionPhaseLabel } from '@/constants/shipmentExceptionPhase'
import type { CodeTableMeta, CodeTablePayload, CodeTableRow } from '@/types/codeTable'

const CHANNEL_CODES_TABLE = 'channel_codes'

const message = useMessage()
const route = useRoute()
const router = useRouter()
const tables = ref<CodeTableMeta[]>([])
const activeTable = ref('')
const loading = ref(false)
const importing = ref(false)
const items = ref<CodeTableRow[]>([])
const total = ref(0)
const search = ref('')
const page = ref(1)
const pageSize = ref(50)

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingRow = ref<CodeTableRow | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const activeMeta = computed(() => tables.value.find((t) => t.table === activeTable.value))
const isChannelTable = computed(() => activeTable.value === CHANNEL_CODES_TABLE)
const hasPortType = computed(() => activeMeta.value?.hasPortType ?? false)
const hasChannelFields = computed(() => activeMeta.value?.hasChannelFields ?? false)
const hasCarrierFields = computed(() => activeMeta.value?.hasCarrierFields ?? false)
const hasRouteStatusFields = computed(() => activeMeta.value?.hasRouteStatusFields ?? false)
const hasExceptionPhaseFields = computed(
  () => activeMeta.value?.hasExceptionPhaseFields ?? false,
)
const hasAmzPortRuleFields = computed(() => activeMeta.value?.hasAmzPortRuleFields ?? false)

async function loadTables() {
  const res = await listCodeTableTypes()
  tables.value = res.tables
  const q = route.query.table
  if (typeof q === 'string' && res.tables.some((t) => t.table === q)) {
    activeTable.value = q
  } else if (!activeTable.value && res.tables.length) {
    activeTable.value = res.tables[0].table
  }
}

async function loadRows() {
  if (!activeTable.value || isChannelTable.value) return
  loading.value = true
  try {
    const res = await listCodeTableRows(activeTable.value, {
      search: search.value.trim() || undefined,
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

function syncTableQuery(table: string) {
  const current = typeof route.query.table === 'string' ? route.query.table : ''
  if (current === table) return
  void router.replace({
    path: route.path,
    query: { ...route.query, table },
  })
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (isChannelTable.value) return
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadRows, 300)
})

watch(activeTable, (table) => {
  page.value = 1
  search.value = ''
  if (table) syncTableQuery(table)
  if (!isChannelTable.value) void loadRows()
})

watch([page, pageSize], () => {
  if (!isChannelTable.value) void loadRows()
})

onMounted(async () => {
  await loadTables()
  if (!isChannelTable.value) await loadRows()
})

function openCreate() {
  modalMode.value = 'create'
  editingRow.value = null
  modalShow.value = true
}

function openEdit(row: CodeTableRow) {
  modalMode.value = 'edit'
  editingRow.value = row
  modalShow.value = true
}

async function handleFormSubmit(payload: CodeTablePayload) {
  try {
    if (modalMode.value === 'create') {
      await createCodeTableRow(activeTable.value, payload)
      message.success('已新增')
    } else if (editingRow.value) {
      const { code: _c, ...body } = payload
      await updateCodeTableRow(activeTable.value, editingRow.value.code, body)
      message.success('已更新')
    }
    modalShow.value = false
    await loadRows()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function handleDelete(row: CodeTableRow) {
  try {
    await deleteCodeTableRow(activeTable.value, row.code)
    message.success('已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await loadRows()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除失败')
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function onFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !activeTable.value || isChannelTable.value) return
  importing.value = true
  try {
    const res = await importCodeTableExcel(activeTable.value, file)
    message.success(`导入完成：新增 ${res.created}，更新 ${res.updated}，失败 ${res.failed}`)
    if (res.errors.length) console.warn('code table import errors', res.errors)
    page.value = 1
    await loadRows()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

function downloadTemplate() {
  if (!activeTable.value || isChannelTable.value) return
  window.open(codeTableTemplateUrl(activeTable.value), '_blank')
}

const columns = computed<DataTableColumns<CodeTableRow>>(() => {
  const cols: DataTableColumns<CodeTableRow> = [
    {
      title: '编码',
      key: 'code',
      width: 140,
      fixed: 'left',
      render: (row) =>
        h('span', { class: 'code-table-code font-mono font-semibold tabular-nums' }, row.code),
    },
    { title: '中文名', key: 'nameZh', width: 160, ellipsis: { tooltip: true } },
    { title: '英文名', key: 'nameEn', width: 160, ellipsis: { tooltip: true } },
  ]
  if (hasPortType.value) {
    cols.push({
      title: '港口类型',
      key: 'portType',
      width: 100,
      render: (row) => row.portType || '—',
    })
  }
  if (hasCarrierFields.value) {
    cols.push({
      title: '承运商ID',
      key: 'carrierId',
      minWidth: 160,
      ellipsis: { tooltip: true },
      render: (row) => row.carrierId || '—',
    })
  }
  if (hasRouteStatusFields.value) {
    cols.push({
      title: 'DPS status',
      key: 'dpsStatus',
      width: 110,
      render: (row) => row.dpsStatus || '—',
    })
  }
  if (hasAmzPortRuleFields.value) {
    cols.push(
      { title: '运输', key: 'transportMode', width: 72 },
      { title: '国家', key: 'countryCode', width: 64 },
      { title: '港口', key: 'portCode', width: 88 },
      { title: '规则', key: 'ruleKind', width: 120 },
      {
        title: '匹配',
        key: 'matchText',
        width: 100,
        render: (row) => row.matchText || '—',
      },
    )
  }
  if (hasExceptionPhaseFields.value) {
    cols.push({
      title: '异常大类',
      key: 'phaseCategory',
      width: 88,
      render: (row) => shipmentExceptionPhaseLabel(row.phaseCategory),
    })
  }
  if (hasChannelFields.value) {
    cols.push(
      { title: '国家', key: 'country', width: 88, render: (row) => row.country || '—' },
      {
        title: '大类',
        key: 'category',
        width: 72,
        render: (row) =>
          row.category
            ? h(NTag, { size: 'small', bordered: false }, () => row.category)
            : h('span', { class: 'text-zinc-500' }, '—'),
      },
      {
        title: 'DPS渠道名',
        key: 'dpsChannelName',
        minWidth: 140,
        ellipsis: { tooltip: true },
        render: (row) => row.dpsChannelName || '—',
      },
      {
        title: '备注',
        key: 'note',
        minWidth: 100,
        ellipsis: { tooltip: true },
        render: (row) => row.note || '—',
      },
    )
  }
  cols.push(
    { title: '排序', key: 'sortOrder', width: 72, align: 'center' },
    {
      title: '启用',
      key: 'isActive',
      width: 72,
      align: 'center',
      render: (row) =>
        h(
          NTag,
          { size: 'small', bordered: false, type: row.isActive ? 'success' : 'default' },
          () => (row.isActive ? '是' : '否'),
        ),
    },
    { title: '更新时间', key: 'updatedTime', width: 168 },
    {
      title: '操作',
      key: 'actions',
      width: 120,
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
            { onPositiveClick: () => handleDelete(row) },
            {
              trigger: () =>
                h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, () => '删除'),
              default: () => `确定删除「${row.code}」？`,
            },
          ),
        ]),
    },
  )
  return cols
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="shrink-0 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="page-h2">后台管理 · 码表</h2>
        <p class="text-xs text-zinc-500">
          「渠道」页与原渠道管理一致（含时效、全量导入）；其他码表可 Excel 导入。承运商「编码」对应运单
          <code class="text-zinc-400">carrier_code</code>；「承运商ID」为 DPS
          <code class="text-zinc-400">carrierId</code>
          ，仅用于反查编码。
        </p>
      </div>
      <NSpace v-if="!isChannelTable">
        <NButton size="small" quaternary @click="downloadTemplate">下载模板</NButton>
        <NButton size="small" :loading="importing" @click="triggerImport">导入 Excel</NButton>
        <NButton size="small" type="primary" :disabled="!activeTable" @click="openCreate">
          新增
        </NButton>
      </NSpace>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls"
      class="hidden"
      @change="onFileSelected"
    />

    <NTabs v-model:value="activeTable" type="line" animated class="shrink-0">
      <NTabPane
        v-for="t in tables"
        :key="t.table"
        :name="t.table"
        :tab="t.label"
      />
    </NTabs>

    <div v-if="isChannelTable" class="min-h-0 flex-1 overflow-hidden">
      <ChannelsView embedded />
    </div>

    <template v-else>
      <div class="shrink-0 flex flex-wrap items-center gap-2">
        <NInput
          v-model:value="search"
          placeholder="搜索编码、中英文名…"
          clearable
          size="small"
          class="w-64"
        />
      </div>

      <div class="panel min-h-0 flex-1 overflow-hidden p-0">
        <NDataTable
          :columns="columns"
          :data="items"
          :loading="loading"
          :scroll-x="hasPortType ? 980 : hasChannelFields ? 1220 : hasCarrierFields || hasRouteStatusFields ? 980 : 880"
          size="small"
          flex-height
          class="code-tables-data-table h-full"
          :bordered="false"
        />
      </div>

      <div class="shrink-0 flex justify-end border-t border-[var(--color-border)] pt-3">
        <NPagination
          v-model:page="page"
          v-model:page-size="pageSize"
          :item-count="total"
          :page-sizes="[20, 50, 100, 200]"
          show-size-picker
          size="small"
        />
      </div>

      <CodeTableFormModal
        :show="modalShow"
        :mode="modalMode"
        :has-port-type="hasPortType"
        :has-channel-fields="hasChannelFields"
        :has-carrier-fields="hasCarrierFields"
        :has-route-status-fields="hasRouteStatusFields"
        :has-exception-phase-fields="hasExceptionPhaseFields"
        :has-amz-port-rule-fields="hasAmzPortRuleFields"
        :initial="editingRow"
        @close="modalShow = false"
        @submit="handleFormSubmit"
      />
    </template>
  </div>
</template>

<style scoped>
.code-tables-data-table :deep(.code-table-code) {
  color: var(--color-fg-emphasis);
}

.code-tables-data-table :deep(th.n-data-table-th--fixed-left),
.code-tables-data-table :deep(td.n-data-table-td--fixed-left) {
  background-color: var(--n-th-color, var(--color-elevated)) !important;
}

.code-tables-data-table :deep(td.n-data-table-td--fixed-left) {
  background-color: var(--n-td-color, var(--color-elevated)) !important;
}
</style>
