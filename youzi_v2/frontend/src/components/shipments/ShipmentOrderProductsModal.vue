<script setup lang="ts">
import { NDataTable, NModal, type DataTableColumns } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { getShipmentOrderProducts, type ShipmentOrderProduct } from '@/api/shipments'
import type { Shipment } from '@/types/shipment'

const props = defineProps<{ show: boolean; shipment: Shipment | null }>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()

function errorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'data' in error) {
    const detail = (error as { data?: { detail?: unknown } }).data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  if (error instanceof Error && error.message.trim()) return error.message
  return '获取运单产品失败'
}
const loading = ref(false)
const errorText = ref('')
const rows = ref<ShipmentOrderProduct[]>([])
let revision = 0

const showModel = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

const title = computed(() => {
  const no = props.shipment?.shipmentNo?.trim()
  return no ? `运单产品 · ${no}` : '运单产品'
})

const totalCtns = computed(() => {
  const numbers = rows.value.map((row) => row.ctns).filter((value): value is number => value != null)
  if (!numbers.length) return null
  return numbers.reduce((sum, value) => sum + value, 0)
})

const shipmentCtns = computed(() => {
  const value = props.shipment?.ctns
  return typeof value === 'number' && Number.isFinite(value) ? value : null
})

const totalCtnsText = computed(() => (totalCtns.value == null ? '—' : String(totalCtns.value)))
const shipmentCtnsText = computed(() => (shipmentCtns.value == null ? '—' : String(shipmentCtns.value)))
const ctnsMismatch = computed(
  () => totalCtns.value != null && shipmentCtns.value != null && totalCtns.value !== shipmentCtns.value,
)

const columns: DataTableColumns<ShipmentOrderProduct> = [
  { title: '中文品名', key: 'cnName', ellipsis: { tooltip: true }, render: (row) => row.cnName || '—' },
  { title: '英文品名', key: 'enName', ellipsis: { tooltip: true }, render: (row) => row.enName || '—' },
  {
    title: '箱数',
    key: 'ctns',
    width: 80,
    align: 'right',
    render: (row) => (row.ctns == null ? '—' : String(row.ctns)),
  },
]

watch(
  () => [props.show, props.shipment?.id] as const,
  async ([open, id]) => {
    const current = ++revision
    rows.value = []
    errorText.value = ''
    if (!open || !id) return
    loading.value = true
    try {
      const data = await getShipmentOrderProducts(String(id))
      if (current === revision) rows.value = data
    } catch (e) {
      if (current === revision) {
        errorText.value = errorMessage(e)
      }
    } finally {
      if (current === revision) loading.value = false
    }
  },
)
</script>

<template>
  <NModal
    v-model:show="showModel"
    preset="card"
    :title="title"
    :style="{ width: 'min(600px, calc(100vw - 2rem))' }"
    :auto-focus="false"
  >
    <p v-if="errorText" class="text-sm text-red-600">{{ errorText }}</p>
    <template v-else>
      <NDataTable
        size="small"
        :loading="loading"
        :columns="columns"
        :data="rows"
        :pagination="false"
        :max-height="360"
      >
        <template #empty>
          <span class="text-sm text-[var(--color-muted)]">该运单没有产品</span>
        </template>
      </NDataTable>
      <div
        v-if="!loading"
        class="mt-2 flex items-center justify-end gap-4 rounded px-2 py-1.5 text-sm"
        :class="
          ctnsMismatch
            ? 'bg-amber-50 font-medium text-amber-900 ring-1 ring-amber-200 dark:bg-amber-950/40 dark:text-amber-100 dark:ring-amber-800'
            : ''
        "
      >
        <span>
          总箱数
          <b class="ml-2 tabular-nums">{{ totalCtnsText }}</b>
        </span>
        <span :class="ctnsMismatch ? '' : 'text-[var(--color-muted)]'">
          运单件数
          <b class="ml-2 tabular-nums">{{ shipmentCtnsText }}</b>
        </span>
        <span v-if="ctnsMismatch">不一致</span>
      </div>
    </template>
  </NModal>
</template>
