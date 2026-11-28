<script setup lang="ts">
import { computed, h, ref, watch } from 'vue'
import { NButton, NDataTable, NPagination, NSelect, NTag, type DataTableColumns } from 'naive-ui'
import { useRouter } from 'vue-router'
import { listBillsOfLading, type BillOfLading } from '@/api/billsOfLading'
import { formatPortDisplay } from '@/utils/portDisplay'
import type { VoyagePortCall } from '@/types/vesselSchedule'

const props = defineProps<{ voyageId: string; portCalls: VoyagePortCall[]; portCallId: string | null }>()
const emit = defineEmits<{ 'update:portCallId': [value: string | null] }>()
const router = useRouter()
const items = ref<BillOfLading[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 30
const loading = ref(false)
const error = ref('')
const options = computed(() => props.portCalls.flatMap(port => port.id
  ? [{ label: `${port.sequence} · ${formatPortDisplay(port)}`, value: port.id }]
  : []))

let revision = 0
async function load() {
  const current = ++revision
  loading.value = true
  error.value = ''
  try {
    const result = await listBillsOfLading({
      country: '', voyage_id: props.voyageId, port_call_id: props.portCallId ?? undefined,
      limit: pageSize, offset: (page.value - 1) * pageSize,
    })
    if (current !== revision) return
    items.value = result.items
    total.value = result.total
    const lastPage = Math.max(1, Math.ceil(total.value / pageSize))
    if (page.value > lastPage) page.value = lastPage
  } catch (e) {
    if (current === revision) error.value = e instanceof Error ? e.message : '提单加载失败'
  } finally {
    if (current === revision) loading.value = false
  }
}

watch(() => [props.voyageId, props.portCallId], () => {
  page.value = 1
  items.value = []
  total.value = 0
}, { flush: 'sync' })
watch([page, () => props.voyageId, () => props.portCallId], load, { immediate: true })

function hasInspection(container: BillOfLading['containers'][number]) {
  return Object.values(container.customs).some(evidence => evidence?.status === 'inspection')
}

const rows = computed(() => items.value.flatMap(bill => bill.containers.map(container => ({ bill, container })))
  .sort((a, b) => Number(hasInspection(b.container)) - Number(hasInspection(a.container))))
type Row = (typeof rows.value)[number]
const phases = [{ key: 'export', label: '出口' }, { key: 'import', label: '进口' }] as const

function openBill(row: Row) {
  void router.push({
    name: 'bills-of-lading',
    query: { billNo: row.bill.billNo, container: row.container.containerNo ?? '' },
  })
}

const columns: DataTableColumns<Row> = [
  { title: '提单号', key: 'bill', width: 190, render: row => h(NButton, {
    text: true, type: 'primary', onClick: () => openBill(row),
  }, () => row.bill.billNo) },
  { title: '柜号', key: 'container', width: 160, render: row => row.container.containerNo || (row.container.unassigned ? '待核对' : '—') },
  { title: '票数', key: 'count', width: 70, align: 'right', render: row => row.container.shipmentCount },
  { title: '起运港', key: 'origin', width: 160, ellipsis: { tooltip: true }, render: row => row.bill.binding?.originPort || '—' },
  { title: '目的港', key: 'destination', width: 160, ellipsis: { tooltip: true }, render: row => row.bill.binding?.destinationPort || '—' },
  { title: '清关', key: 'customs', minWidth: 180, render: row => {
    const tags = phases.flatMap(({ key, label }) => {
      const evidence = row.container.customs[key]
      if (!evidence) return []
      const inspection = evidence.status === 'inspection'
      return [h(NTag, { size: 'small', bordered: false, type: inspection ? 'warning' : 'success' }, () =>
        `${label}${inspection ? '查验' : '已放行'}`
      )]
    })
    return tags.length ? h('div', { class: 'flex flex-wrap gap-1' }, tags) : '—'
  } },
]
</script>

<template>
  <div class="space-y-2">
    <div class="flex flex-wrap items-center gap-2">
      <NSelect :value="portCallId" :options="options" size="small" clearable filterable
        placeholder="全部挂靠" aria-label="筛选挂靠港" class="w-56" @update:value="emit('update:portCallId', $event)" />
      <span class="text-sm text-[var(--color-muted)]">{{ total }} 个提单</span>
    </div>
    <p v-if="error" role="alert" class="text-sm text-red-600">{{ error }} <NButton text @click="load">重试</NButton></p>
    <NDataTable :columns="columns" :data="rows" :loading="loading"
      :row-key="row => JSON.stringify([row.bill.billNo, row.container.containerNo])" :bordered="false" size="small" :scroll-x="920" />
    <NPagination v-if="total > pageSize" v-model:page="page" :item-count="total" :page-size="pageSize" />
  </div>
</template>
