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
  NSwitch,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { h, onMounted, ref, watch } from 'vue'
import {
  createCustomer,
  deleteCustomer,
  listCustomers,
  syncCustomersFromShipments,
  updateCustomer,
  type Customer,
  type CustomerLang,
} from '@/api/customers'
import VipStarBadge from '@/components/common/VipStarBadge.vue'

const message = useMessage()
const loading = ref(false)
const syncing = ref(false)
const submitting = ref(false)
const items = ref<Customer[]>([])
const total = ref(0)
const search = ref('')
const filterVipOnly = ref(false)
const newName = ref('')
const newCustomerLang = ref<CustomerLang>('zh')
const newNote = ref('')
const page = ref(1)
const pageSize = ref(50)

const customerLangOptions = [
  { label: '中文', value: 'zh' as const },
  { label: '英文', value: 'en' as const },
]

async function load() {
  loading.value = true
  try {
    const res = await listCustomers({
      search: search.value.trim() || undefined,
      vipOnly: filterVipOnly.value || undefined,
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

async function handleSync() {
  syncing.value = true
  try {
    const res = await syncCustomersFromShipments()
    message.success(
      `已同步：运单中 ${res.fromShipments} 个客户，新增 ${res.added} 个，库内共 ${res.total} 个`,
      { duration: 6000 },
    )
    page.value = 1
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '同步失败')
  } finally {
    syncing.value = false
  }
}

async function handleAdd() {
  const name = newName.value.trim()
  if (!name) {
    message.warning('请输入客户名')
    return
  }
  submitting.value = true
  try {
    await createCustomer(name, {
      note: newNote.value,
      customerLang: newCustomerLang.value,
    })
    newName.value = ''
    newCustomerLang.value = 'zh'
    newNote.value = ''
    page.value = 1
    await load()
    message.success('已添加客户')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '添加失败')
  } finally {
    submitting.value = false
  }
}

function replaceRow(updated: Customer) {
  const idx = items.value.findIndex((x) => x.id === updated.id)
  if (idx >= 0) items.value[idx] = updated
}

async function patchRow(row: Customer, patch: Parameters<typeof updateCustomer>[1]) {
  try {
    const updated = await updateCustomer(row.id, patch)
    replaceRow(updated)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
    await load()
  }
}

async function toggleVip(row: Customer, isVip: boolean) {
  try {
    const updated = await updateCustomer(row.id, { isVip })
    replaceRow(updated)
    message.success(isVip ? '已设为 VIP' : '已取消 VIP')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新失败')
    await load()
  }
}

async function handleDelete(row: Customer) {
  try {
    await deleteCustomer(row.id)
    await load()
    message.success('已删除')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除失败')
  }
}

const columns: DataTableColumns<Customer> = [
  {
    title: '运单用户名',
    key: 'customerName',
    minWidth: 120,
    ellipsis: { tooltip: true },
    render: (row) =>
      h('span', { class: 'inline-flex items-center gap-1.5' }, [
        h('span', row.customerName),
        row.isVip ? h(VipStarBadge) : null,
      ]),
  },
  {
    title: '客户语言',
    key: 'customerLang',
    width: 96,
    render: (row) =>
      h(NSelect, {
        size: 'small',
        value: row.customerLang,
        options: customerLangOptions,
        onUpdateValue: (v: CustomerLang) => {
          row.customerLang = v
          void patchRow(row, { customerLang: v })
        },
      }),
  },
  {
    title: 'VIP',
    key: 'isVip',
    width: 72,
    align: 'center',
    render: (row) =>
      h(NSwitch, {
        size: 'small',
        value: row.isVip,
        onUpdateValue: (v: boolean) => toggleVip(row, v),
      }),
  },
  {
    title: '运单数',
    key: 'shipmentCount',
    width: 72,
    align: 'center',
  },
  {
    title: '备注',
    key: 'note',
    minWidth: 120,
    ellipsis: { tooltip: true },
    render: (row) =>
      h(NInput, {
        size: 'small',
        value: row.note,
        placeholder: '—',
        onUpdateValue: (v: string) => {
          row.note = v
        },
        onBlur: () => {
          void patchRow(row, { note: row.note })
        },
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 72,
    render: (row) =>
      h(
        NPopconfirm,
        { onPositiveClick: () => handleDelete(row) },
        {
          trigger: () =>
            h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, () => '删除'),
          default: () => `确定删除客户「${row.customerName}」？`,
        },
      ),
  },
]

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
})

watch(filterVipOnly, () => {
  page.value = 1
  load()
})

watch([page, pageSize], load)

onMounted(async () => {
  await load()
  if (total.value === 0) {
    await handleSync()
  }
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-white">客户管理</h2>
        <p class="text-xs text-zinc-500">
          运单用户名为同步键。客户语言用于 UPS/FedEx 等官网跳转（中文/英文站）。
        </p>
      </div>
      <NButton size="small" type="primary" :loading="syncing" @click="handleSync">
        从运单同步客户
      </NButton>
    </div>

    <div class="panel shrink-0 px-3 py-3">
      <div class="mb-2 text-xs text-zinc-400">手动添加客户</div>
      <NSpace align="center" wrap>
        <NInput
          v-model:value="newName"
          placeholder="运单用户名"
          clearable
          size="small"
          class="w-40"
          @keydown.enter="handleAdd"
        />
        <NSelect
          v-model:value="newCustomerLang"
          :options="customerLangOptions"
          size="small"
          class="w-24"
        />
        <NInput
          v-model:value="newNote"
          placeholder="备注（可选）"
          clearable
          size="small"
          class="w-48"
          @keydown.enter="handleAdd"
        />
        <NButton size="small" :loading="submitting" @click="handleAdd">添加</NButton>
      </NSpace>
    </div>

    <div class="panel flex min-h-0 flex-1 flex-col gap-2 px-3 py-2">
      <div class="flex flex-wrap items-center gap-2">
        <NInput
          v-model:value="search"
          placeholder="搜索用户名 / 备注"
          clearable
          size="small"
          class="max-w-xs"
        />
        <NCheckbox v-model:checked="filterVipOnly" size="small">仅 VIP</NCheckbox>
      </div>
      <NDataTable
        :columns="columns"
        :data="items"
        :loading="loading"
        size="small"
        flex-height
        class="min-h-0 flex-1"
        :bordered="false"
        :scroll-x="720"
      />
      <div class="flex justify-end border-t border-[var(--color-border)] pt-2">
        <NPagination
          v-model:page="page"
          v-model:page-size="pageSize"
          :item-count="total"
          :page-sizes="[20, 50, 100]"
          show-size-picker
          size="small"
        />
      </div>
    </div>
  </div>
</template>
