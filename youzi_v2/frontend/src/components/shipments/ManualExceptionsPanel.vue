<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { NButton, NDataTable, NInput, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import { api } from '@/api/client'

interface Row {
  id: string; shipment_no: string; customer: string; exception_name_zh: string
  exception_opened_time: string; daysOpen: number; nextFollowup: string | null; followupDue: boolean
  transportDays: number | null; trackingDays: number | null
}
const emit = defineEmits<{ open: [shipmentId: string] }>()
const message = useMessage()
const items = ref<Row[]>([])
const busy = ref(false)
const search = ref('')
const submitting = ref<string[]>([])
const filtered = computed(() => items.value.filter(row => `${row.shipment_no} ${row.customer || ''} ${row.exception_name_zh}`.toLowerCase().includes(search.value.trim().toLowerCase())))
async function load() {
  busy.value = true
  try { items.value = (await api<{ items: Row[] }>('/api/v1/shipment-sla-alerts/manual-exceptions')).items }
  catch (e) { message.error(e instanceof Error ? e.message : '加载失败') }
  finally { busy.value = false }
}
async function follow(row: Row) {
  if (submitting.value.includes(row.id)) return
  submitting.value.push(row.id)
  try {
    await api(`/api/v1/shipment-sla-alerts/manual-exceptions/${row.id}/follow-up`, { method: 'POST' })
    message.success('已记录跟进，下次关注时间为 7 天后')
    await load()
  } catch (e) { message.error(e instanceof Error ? e.message : '跟进失败') }
  finally { submitting.value = submitting.value.filter(id => id !== row.id) }
}
const columns: DataTableColumns<Row> = [
  { title: '运单号', key: 'shipment_no', render: row => h(NButton, { text: true, type: 'primary', onClick: () => emit('open', row.id) }, () => row.shipment_no) },
  { title: '客户', key: 'customer' },
  { title: '人工异常', key: 'exception_name_zh' },
  { title: '异常开始时间', key: 'exception_opened_time' },
  { title: '已持续', key: 'daysOpen', render: row => `${row.daysOpen} 天` },
  { title: '运输天数', key: 'transportDays', render: row => row.transportDays == null ? '—' : `${row.transportDays} 天` },
  { title: '内部轨迹未更新', key: 'trackingDays', render: row => row.trackingDays == null ? '无内部轨迹' : `${row.trackingDays} 天` },
  { title: '下次关注', key: 'nextFollowup', render: row => row.nextFollowup || '缺少异常开始时间' },
  { title: '跟进状态', key: 'followupDue', render: row => h(NTag, { type: row.followupDue ? 'warning' : 'default', bordered: false }, () => row.followupDue ? '待跟进' : '未到跟进日') },
  { title: '操作', key: 'actions', render: row => h(NButton, { size: 'small', loading: submitting.value.includes(row.id), onClick: () => follow(row) }, () => '已跟进，7 天后提醒') },
]
onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <p class="text-sm text-secondary">人工异常单独管理，每 7 个自然日跟进一次。未关闭期间不进入运输关注；到期待跟进的运单排在前面。</p>
    <div class="flex gap-3"><NInput v-model:value="search" placeholder="搜索运单号、客户、异常" clearable /><NButton :loading="busy" @click="load">刷新</NButton></div>
    <NDataTable :columns="columns" :data="filtered" :loading="busy" :row-key="row => row.id" :pagination="{ pageSize: 30 }" :scroll-x="1000" />
  </div>
</template>
