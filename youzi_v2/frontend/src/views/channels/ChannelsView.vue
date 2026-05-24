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
import ChannelFormModal from '@/components/channels/ChannelFormModal.vue'
import {
  createChannel,
  deleteChannel,
  getChannelMeta,
  listChannels,
  seedDefaultChannels,
  updateChannel,
  type Channel,
  type ChannelPayload,
} from '@/api/channels'

const message = useMessage()
const loading = ref(false)
const seeding = ref(false)
const items = ref<Channel[]>([])
const total = ref(0)
const search = ref('')
const filterCountry = ref<string | null>(null)
const filterCategory = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(50)
const categories = ref<string[]>(['空运', '海运', '快递', '卡航', '铁路'])
const COMMON_COUNTRIES = ['美国', '加拿大', '英国', '欧洲', '澳大利亚', '墨西哥']

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('create')
const editingRow = ref<Channel | null>(null)

const countryOptions = computed(() => {
  const set = new Set([...COMMON_COUNTRIES, ...items.value.map((x) => x.country).filter(Boolean)])
  return [...set].sort().map((c) => ({ label: c, value: c }))
})

const categoryTagType = (cat: string): 'default' | 'info' | 'success' | 'warning' | 'error' => {
  if (cat === '空运') return 'info'
  if (cat === '海运') return 'success'
  if (cat === '卡航') return 'warning'
  if (cat === '快递') return 'error'
  return 'default'
}

async function loadMeta() {
  try {
    const res = await getChannelMeta()
    if (res.categories.length) categories.value = res.categories
  } catch {
    /* 使用本地默认 */
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listChannels({
      search: search.value.trim() || undefined,
      country: filterCountry.value || undefined,
      category: filterCategory.value || undefined,
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

async function handleSeed() {
  seeding.value = true
  try {
    const res = await seedDefaultChannels()
    message.success(`内置渠道：新增 ${res.inserted}，更新 ${res.updated}，共 ${res.total} 条`)
    page.value = 1
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    seeding.value = false
  }
}

function openCreate() {
  modalMode.value = 'create'
  editingRow.value = null
  modalShow.value = true
}

function openEdit(row: Channel) {
  modalMode.value = 'edit'
  editingRow.value = row
  modalShow.value = true
}

async function handleFormSubmit(payload: ChannelPayload) {
  try {
    if (modalMode.value === 'create') {
      await createChannel(payload)
      message.success('已新增渠道')
    } else {
      const { code: _c, ...body } = payload
      await updateChannel(editingRow.value!.code, body)
      message.success('已更新')
    }
    modalShow.value = false
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  }
}

async function handleDelete(row: Channel) {
  try {
    await deleteChannel(row.code)
    await load()
    message.success('已删除')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除失败')
  }
}

const columns: DataTableColumns<Channel> = [
  {
    title: '渠道（英文）',
    key: 'code',
    minWidth: 220,
    ellipsis: { tooltip: true },
  },
  {
    title: '中文',
    key: 'nameZh',
    width: 120,
    ellipsis: { tooltip: true },
  },
  {
    title: '国家',
    key: 'country',
    width: 88,
  },
  {
    title: '大类',
    key: 'category',
    width: 72,
    render: (row) =>
      row.category
        ? h(NTag, { size: 'small', bordered: false, type: categoryTagType(row.category) }, () => row.category)
        : h('span', { class: 'text-zinc-500' }, '—'),
  },
  {
    title: '备注',
    key: 'note',
    minWidth: 100,
    ellipsis: { tooltip: true },
    render: (row) => row.note || '—',
  },
  {
    title: '排序',
    key: 'sortOrder',
    width: 64,
    align: 'center',
  },
  {
    title: '状态',
    key: 'isActive',
    width: 72,
    align: 'center',
    render: (row) =>
      h(
        NTag,
        { size: 'tiny', bordered: false, type: row.isActive ? 'success' : 'default' },
        () => (row.isActive ? '启用' : '停用'),
      ),
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => openEdit(row) }, () => '编辑'),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row) },
          {
            trigger: () =>
              h(NButton, { size: 'tiny', quaternary: true, type: 'error' }, () => '删除'),
            default: () => `删除渠道「${row.code}」？`,
          },
        ),
      ]),
  },
]

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
})
watch([filterCountry, filterCategory], () => {
  page.value = 1
  load()
})
watch([page, pageSize], load)

onMounted(async () => {
  await loadMeta()
  await load()
})
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-4">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-lg font-semibold text-white">渠道管理</h1>
        <p class="mt-1 text-sm text-zinc-500">
          配置渠道中英文、国家/地区、大类（空运/海运/快递/卡航/铁路）与备注；运单
          <code class="text-zinc-400">channel_code</code> 与此处编码一致。
        </p>
      </div>
      <NSpace>
        <NButton :loading="seeding" @click="handleSeed">导入内置渠道</NButton>
        <NButton type="primary" @click="openCreate">新增渠道</NButton>
      </NSpace>
    </div>

    <div
      class="panel grid shrink-0 grid-cols-[7.5rem_7.5rem_minmax(12rem,1fr)] items-center gap-2 p-3"
    >
      <NSelect
        v-model:value="filterCategory"
        :options="categories.map((c) => ({ label: c, value: c }))"
        clearable
        placeholder="大类"
        size="small"
        class="min-w-0"
      />
      <NSelect
        v-model:value="filterCountry"
        :options="countryOptions"
        clearable
        placeholder="国家"
        size="small"
        class="min-w-0"
      />
      <NInput
        v-model:value="search"
        clearable
        placeholder="搜索渠道编码、中文、国家、备注…"
        class="min-w-0"
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
        :scroll-x="900"
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

    <ChannelFormModal
      :show="modalShow"
      :mode="modalMode"
      :row="editingRow"
      :categories="categories"
      :countries="countryOptions.map((o) => o.value)"
      @close="modalShow = false"
      @submit="handleFormSubmit"
    />
  </div>
</template>
