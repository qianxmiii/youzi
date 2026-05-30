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
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import AddressFormModal from '@/components/addresses/AddressFormModal.vue'
import {
  createAddress,
  deleteAddress,
  exportAddressesExcel,
  importAddressesExcel,
  listAddressFilterOptions,
  listAddresses,
  updateAddress,
  addressTemplateUrl,
  type Address,
  type AddressPayload,
} from '@/api/addresses'
import { useCountryLabels } from '@/composables/useCountryLabels'
import { formatAddressCopyText } from '@/utils/addressCopyFormat'

const message = useMessage()
const { loadCountryLabels, countryLabel } = useCountryLabels()
const loading = ref(false)
const importing = ref(false)
const exporting = ref(false)
const items = ref<Address[]>([])
const total = ref(0)
const search = ref('')
const filterType = ref<string | null>(null)
const filterCountry = ref<string | null>(null)
const filterCountries = ref<string[]>([])
const page = ref(1)
const pageSize = ref(50)
const fileInputRef = ref<HTMLInputElement | null>(null)

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingRow = ref<Address | null>(null)

const typeOptions = [
  { label: 'AMZ', value: 'AMZ' },
  { label: 'WFS', value: 'WFS' },
]

function countryOptionLabel(code: string): string {
  const label = countryLabel(code)
  if (label && label !== code && label !== '—') return `${label} (${code})`
  return code
}

const countryOptions = computed(() =>
  filterCountries.value.map((code) => ({
    label: countryOptionLabel(code),
    value: code,
  })),
)

function formatAddress(row: Address) {
  return [row.addressLine1, row.addressLine2, row.addressLine3].filter(Boolean).join(' · ')
}

async function load() {
  loading.value = true
  try {
    const res = await listAddresses({
      search: search.value.trim() || undefined,
      addressType: filterType.value || undefined,
      countryCode: filterCountry.value || undefined,
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

async function loadFilterOptions() {
  try {
    const res = await listAddressFilterOptions()
    filterCountries.value = res.countries
  } catch {
    /* 筛选项加载失败时仍可搜索 */
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
})
watch([filterType, filterCountry], () => {
  page.value = 1
  load()
})
watch([page, pageSize], load)

onMounted(async () => {
  await loadCountryLabels()
  await loadFilterOptions()
  await load()
})

function openCreate() {
  modalMode.value = 'create'
  editingRow.value = null
  modalShow.value = true
}

function openEdit(row: Address) {
  modalMode.value = 'edit'
  editingRow.value = row
  modalShow.value = true
}

async function handleFormSubmit(payload: AddressPayload) {
  try {
    if (modalMode.value === 'create') {
      await createAddress(payload)
      message.success('已新增地址')
    } else if (editingRow.value) {
      await updateAddress(editingRow.value.id, payload)
      message.success('已更新')
    }
    modalShow.value = false
    await loadFilterOptions()
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function handleDelete(row: Address) {
  try {
    await deleteAddress(row.id)
    message.success('已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await loadFilterOptions()
    await load()
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
  if (!file) return
  importing.value = true
  try {
    const res = await importAddressesExcel(file)
    message.success(
      `导入完成：新增 ${res.created} 条，更新 ${res.updated} 条` +
        (res.failed ? `，失败 ${res.failed} 条` : ''),
    )
    if (res.errors.length) {
      message.warning(res.errors.slice(0, 3).map((x) => `第 ${x.row} 行：${x.message}`).join('；'))
    }
    page.value = 1
    await loadFilterOptions()
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

function downloadTemplate() {
  window.open(addressTemplateUrl(), '_blank')
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
    const blob = await exportAddressesExcel({
      search: search.value.trim() || undefined,
      addressType: filterType.value || undefined,
      countryCode: filterCountry.value || undefined,
    })
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').slice(0, 14)
    downloadBlob(blob, `仓库地址导出_${ts}.xlsx`)
    message.success(`已导出 ${total.value} 条地址（当前筛选）`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleCopy(row: Address) {
  const text = formatAddressCopyText(row)
  if (!text) {
    message.warning('无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success('已复制地址')
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

const columns: DataTableColumns<Address> = [
  {
    title: '仓库代码',
    key: 'warehouseCode',
    width: 108,
    fixed: 'left',
    ellipsis: { tooltip: true },
    render: (row) => h('span', { class: 'font-mono font-medium text-[var(--color-fg-emphasis)]' }, row.warehouseCode || '—'),
  },
  {
    title: '类型',
    key: 'addressType',
    width: 72,
    render: (row) =>
      row.addressType
        ? h(NTag, { size: 'small', bordered: false, type: row.addressType === 'AMZ' ? 'info' : 'warning' }, () => row.addressType)
        : '—',
  },
  { title: '国家', key: 'countryCode', width: 64 },
  { title: '邮编', key: 'postalCode', width: 112 },
  { title: '州省', key: 'state', width: 120, ellipsis: { tooltip: true } },
  { title: '城市', key: 'city', width: 158, ellipsis: { tooltip: true } },
  {
    title: '地址',
    key: 'addressLine1',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row) => formatAddress(row) || '—',
  },
  { title: '备注一', key: 'note1', width: 150, ellipsis: { tooltip: true } },
  { title: '备注二', key: 'note2', width: 150, ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    width: 168,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => handleCopy(row) }, () => '复制'),
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row) },
          {
            trigger: () =>
              h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, () => '删除'),
            default: () => `删除地址「${row.warehouseCode}」？`,
          },
        ),
      ]),
  },
]
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="page-h2">地址簿</h2>
        <p class="mt-1 text-xs text-[var(--color-muted)]">
          平台仓库地址（AMZ / WFS）；共 {{ total }} 条 · 支持 Excel 导入/导出，地址类型填 AMZ 或 WFS
        </p>
      </div>
      <NSpace>
        <NButton size="small" @click="downloadTemplate">下载模板</NButton>
        <NButton size="small" :loading="importing" @click="triggerImport">导入 Excel</NButton>
        <NButton size="small" :loading="exporting" @click="handleExport">导出 Excel</NButton>
        <NButton type="primary" @click="openCreate">新增地址</NButton>
      </NSpace>
      <input ref="fileInputRef" type="file" accept=".xlsx,.xls" class="hidden" @change="onFileSelected" />
    </div>

    <div class="panel grid shrink-0 grid-cols-[7rem_10rem_minmax(12rem,1fr)] items-center gap-2 p-3">
      <NSelect
        v-model:value="filterType"
        :options="typeOptions"
        clearable
        placeholder="类型"
        size="small"
      />
      <NSelect
        v-model:value="filterCountry"
        :options="countryOptions"
        clearable
        filterable
        placeholder="国家"
        size="small"
      />
      <NInput
        v-model:value="search"
        clearable
        placeholder="搜索仓库代码、公司、收件人、城市、地址、邮编…"
        size="small"
      />
    </div>

    <div class="panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable
        :columns="columns"
        :data="items"
        :loading="loading"
        :bordered="false"
        size="small"
        flex-height
        class="h-full"
        :scroll-x="1080"
      />
    </div>

    <div class="flex shrink-0 justify-end">
      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[20, 50, 100]"
        show-size-picker
        size="small"
      />
    </div>

    <AddressFormModal
      :show="modalShow"
      :mode="modalMode"
      :row="editingRow"
      @close="modalShow = false"
      @submit="handleFormSubmit"
    />
  </div>
</template>
