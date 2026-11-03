<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NInput,
  NPagination,
  NPopconfirm,
  NSelect,
  NSpace,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
  type DataTableRowKey,
} from 'naive-ui'
import { computed, h, onActivated, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { listCustomers } from '@/api/customers'
import {
  batchDeleteCustomerAddresses,
  createCustomerAddress,
  deleteCustomerAddress,
  downloadCustomerAddressTemplate,
  exportCustomerAddressesExcel,
  importCustomerAddressesExcel,
  listCustomerAddresses,
  updateCustomerAddress,
  type CustomerAddress,
  type CustomerAddressPayload,
} from '@/api/customerAddresses'
import CustomerAddressFormModal from '@/components/customers/CustomerAddressFormModal.vue'
import { useCountryLabels } from '@/composables/useCountryLabels'
import {
  formatCustomerAddressCopy,
  formatCustomerAddressCopyBatch,
} from '@/utils/customerAddressCopy'

const message = useMessage()
const dialog = useDialog()
const route = useRoute()
const { loadCountryLabels, countryLabel } = useCountryLabels()

const kindOptions = [
  { label: '海外仓', value: 'WAREHOUSE' },
  { label: '商业', value: 'COMMERCIAL' },
  { label: '住宅', value: 'RESIDENTIAL' },
]
const remoteOptions = [
  { label: '偏远', value: 'yes' },
  { label: '非偏远', value: 'no' },
]
const kindLabel: Record<string, string> = {
  WAREHOUSE: '海外仓',
  COMMERCIAL: '商业',
  RESIDENTIAL: '住宅',
}

const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const items = ref<CustomerAddress[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const search = ref('')
const filterCustomer = ref<string | null>(null)
const filterKind = ref<string | null>(null)
const filterRemote = ref<string | null>(null)
const checkedKeys = ref<DataTableRowKey[]>([])
const customerOptions = ref<Array<{ label: string; value: string }>>([])
const showForm = ref(false)
const editing = ref<CustomerAddress | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

function queryCustomer(): string {
  const raw = route.query.customer
  const text = Array.isArray(raw) ? raw[0] : raw
  return (text || '').trim()
}

function applyRouteCustomer() {
  const name = queryCustomer()
  filterCustomer.value = name || null
}

function errorText(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'data' in error) {
    const detail = (error as { data?: { detail?: unknown } }).data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return error instanceof Error ? error.message : fallback
}

function rowTitle(row: CustomerAddress): string {
  return (
    row.label.trim() ||
    row.consigneeName.trim() ||
    row.company.trim() ||
    row.address.trim().slice(0, 24) ||
    '未命名地址'
  )
}

function listQuery() {
  return {
    customer: filterCustomer.value || undefined,
    addressKind: filterKind.value || undefined,
    remote: filterRemote.value === 'yes' ? true : filterRemote.value === 'no' ? false : undefined,
    search: search.value.trim() || undefined,
  }
}

async function loadCustomers() {
  try {
    const res = await listCustomers({ limit: 500 })
    customerOptions.value = res.items.map((row) => ({
      label: row.customerName,
      value: row.customerName,
    }))
  } catch {
    customerOptions.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listCustomerAddresses({
      ...listQuery(),
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = res.items
    total.value = res.total
    const ids = new Set(res.items.map((row) => row.id))
    checkedKeys.value = checkedKeys.value.filter((id) => ids.has(String(id)))
  } catch (e) {
    message.error(errorText(e, '加载失败'))
  } finally {
    loading.value = false
  }
}

async function copyText(text: string) {
  if (!text.trim()) {
    message.warning('没有可复制的内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制')
  } catch {
    message.error('复制失败')
  }
}

function copyOne(row: CustomerAddress) {
  void copyText(formatCustomerAddressCopy(row))
}

function copySelected() {
  const picked = items.value.filter((row) => checkedKeys.value.includes(row.id))
  void copyText(formatCustomerAddressCopyBatch(picked))
}

function openCreate() {
  editing.value = null
  showForm.value = true
}

function openEdit(row: CustomerAddress) {
  editing.value = row
  showForm.value = true
}

async function handleSubmit(payload: CustomerAddressPayload) {
  saving.value = true
  try {
    if (editing.value) {
      await updateCustomerAddress(editing.value.id, payload)
      message.success('已保存')
    } else {
      await createCustomerAddress(payload)
      message.success('已新增')
    }
    showForm.value = false
    await load()
  } catch (e) {
    message.error(errorText(e, '保存失败'))
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: CustomerAddress) {
  try {
    await deleteCustomerAddress(row.id)
    message.success('已删除')
    await load()
  } catch (e) {
    message.error(errorText(e, '删除失败'))
  }
}

function confirmBatchDelete() {
  const ids = checkedKeys.value.map(String)
  if (!ids.length) return
  dialog.warning({
    title: '批量删除',
    content: `删除选中的 ${ids.length} 条地址？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        const res = await batchDeleteCustomerAddresses(ids)
        checkedKeys.value = []
        message.success(`已删除 ${res.deleted} 条`)
        await load()
      } catch (e) {
        message.error(errorText(e, '删除失败'))
      }
    },
  })
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
    const blob = await exportCustomerAddressesExcel(listQuery())
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').slice(0, 14)
    downloadBlob(blob, `客户地址导出_${ts}.xlsx`)
  } catch (e) {
    message.error(errorText(e, '导出失败'))
  } finally {
    exporting.value = false
  }
}

async function handleTemplate() {
  try {
    const blob = await downloadCustomerAddressTemplate()
    downloadBlob(blob, '客户地址模板.xlsx')
  } catch (e) {
    message.error(errorText(e, '下载失败'))
  }
}

function pickImport() {
  fileInput.value?.click()
}

async function onImportFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const res = await importCustomerAddressesExcel(file)
    const detail = res.errors
      .slice(0, 3)
      .map((item) => `第 ${item.row} 行：${item.message}`)
      .join('；')
    if (res.failed) {
      message.warning(`新增 ${res.created} 条，失败 ${res.failed} 条${detail ? `。${detail}` : ''}`)
    } else {
      message.success(`新增 ${res.created} 条`)
    }
    page.value = 1
    await load()
  } catch (e) {
    message.error(errorText(e, '导入失败'))
  }
}

const columns = computed<DataTableColumns<CustomerAddress>>(() => [
  { type: 'selection' },
  {
    title: '客户',
    key: 'customerName',
    width: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: '地址',
    key: 'label',
    minWidth: 220,
    render: (row) =>
      h('div', { class: 'min-w-0' }, [
        h('div', { class: 'truncate font-medium' }, rowTitle(row)),
        h(
          'div',
          { class: 'truncate text-xs text-zinc-500', title: row.address },
          [countryLabel(row.country), row.postcode, row.address].filter(Boolean).join(' · '),
        ),
      ]),
  },
  {
    title: '收货人',
    key: 'consigneeName',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row) => row.consigneeName || row.company || '—',
  },
  {
    title: '类型',
    key: 'addressKind',
    width: 88,
    render: (row) =>
      h(NTag, { size: 'small', bordered: false }, () => kindLabel[row.addressKind] || row.addressKind),
  },
  {
    title: '偏远',
    key: 'isRemote',
    width: 72,
    render: (row) => (row.isRemote ? h(NTag, { size: 'small', type: 'warning' }, () => '偏远') : '—'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 168,
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => copyOne(row) }, () => '复制'),
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openEdit(row) }, () => '修改'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row) },
          {
            trigger: () => h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, () => '删除'),
            default: () => '删除这条地址？',
          },
        ),
      ]),
  },
])

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
})

watch([filterCustomer, filterKind, filterRemote], () => {
  page.value = 1
  void load()
})

watch([page, pageSize], load)

watch(
  () => route.query.customer,
  () => {
    applyRouteCustomer()
  },
)

onMounted(async () => {
  applyRouteCustomer()
  await loadCountryLabels()
  await loadCustomers()
  await load()
})

onActivated(() => {
  applyRouteCustomer()
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="page-h2">客户地址簿</h2>
        <p class="text-xs text-zinc-500">客户自己的收货地址。数据只保存在本机数据库。</p>
      </div>
      <NSpace size="small">
        <NButton size="small" @click="handleTemplate">下载模板</NButton>
        <NButton size="small" @click="pickImport">导入</NButton>
        <NButton size="small" :loading="exporting" @click="handleExport">导出</NButton>
        <NButton size="small" type="primary" @click="openCreate">新增</NButton>
      </NSpace>
    </div>

    <input
      ref="fileInput"
      type="file"
      accept=".xlsx"
      class="hidden"
      @change="onImportFile"
    />

    <div class="panel shrink-0 px-3 py-3">
      <div class="flex flex-wrap items-center gap-2">
        <NSelect
          v-model:value="filterCustomer"
          class="customer-address-filter customer-address-filter--customer"
          clearable
          filterable
          placeholder="客户"
          :options="customerOptions"
        />
        <NSelect
          v-model:value="filterKind"
          class="customer-address-filter customer-address-filter--kind"
          clearable
          placeholder="地址类型"
          :options="kindOptions"
        />
        <NSelect
          v-model:value="filterRemote"
          class="customer-address-filter customer-address-filter--remote"
          clearable
          placeholder="偏远"
          :options="remoteOptions"
        />
        <NInput
          v-model:value="search"
          class="customer-address-filter customer-address-filter--search"
          clearable
          placeholder="简称 / 收货人 / 公司 / 电话 / 地址 / 邮编"
        />
      </div>
    </div>

    <div v-if="checkedKeys.length" class="panel flex shrink-0 items-center gap-2 px-3 py-2">
      <span class="text-sm">已选 {{ checkedKeys.length }} 条</span>
      <NButton size="small" @click="copySelected">批量复制</NButton>
      <NButton size="small" type="error" secondary @click="confirmBatchDelete">批量删除</NButton>
    </div>

    <div class="panel min-h-0 flex-1 overflow-hidden">
      <NDataTable
        class="h-full"
        flex-height
        remote
        :columns="columns"
        :data="items"
        :loading="loading"
        :row-key="(row: CustomerAddress) => row.id"
        :checked-row-keys="checkedKeys"
        :pagination="false"
        @update:checked-row-keys="(keys: DataTableRowKey[]) => (checkedKeys = keys)"
      />
    </div>
    <div class="flex shrink-0 justify-end">
      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[20, 50, 100]"
        show-size-picker
      />
    </div>

    <CustomerAddressFormModal
      v-model:show="showForm"
      :saving="saving"
      :row="editing"
      :customer-options="customerOptions"
      :preset-customer="filterCustomer || ''"
      @submit="handleSubmit"
    />
  </div>
</template>

<style scoped>
.customer-address-filter {
  flex: 0 0 auto;
}
.customer-address-filter--customer {
  width: 13rem;
}
.customer-address-filter--kind {
  width: 8.5rem;
}
.customer-address-filter--remote {
  width: 7rem;
}
.customer-address-filter--search {
  width: 18rem;
}
</style>
