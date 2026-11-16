<script setup lang="ts">
import { NButton, NDataTable, NModal, useMessage, type DataTableColumns } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import {
  checkShipmentProductCtns,
  type ProductCtnsCheckIssue,
  type ProductCtnsCheckResult,
} from '@/api/shipments'

const props = defineProps<{ show: boolean; ids: string[] }>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()

function errorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'data' in error) {
    const detail = (error as { data?: { detail?: unknown } }).data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  if (error instanceof Error && error.message.trim()) return error.message
  return '核对件数失败'
}

const message = useMessage()
const mismatchNos = computed(() => [...new Set((result.value?.issues ?? [])
  .filter(row => row.kind === 'mismatch')
  .map(row => row.shipmentNo.trim())
  .filter(Boolean))])
async function copyMismatchNos() {
  if (loading.value || !mismatchNos.value.length) return
  try {
    await navigator.clipboard.writeText(mismatchNos.value.join('\n'))
    message.success(`已复制 ${mismatchNos.value.length} 个件数不一致单号`)
  } catch {
    message.error('复制失败，请检查浏览器剪贴板权限')
  }
}

const loading = ref(false)
const errorText = ref('')
const result = ref<ProductCtnsCheckResult | null>(null)
let revision = 0

const showModel = computed({
  get: () => props.show,
  set: (value: boolean) => emit('update:show', value),
})

function countText(value: number | null): string {
  return value == null ? '—' : String(value)
}

function diffText(value: number | null): string {
  if (value == null) return '—'
  if (value > 0) return `+${value}`
  return String(value)
}

const columns: DataTableColumns<ProductCtnsCheckIssue> = [
  { title: '运单号', key: 'shipmentNo', width: 168, ellipsis: { tooltip: true } },
  {
    title: '运单件数',
    key: 'shipmentCtns',
    width: 88,
    align: 'right',
    render: (row) => countText(row.shipmentCtns),
  },
  {
    title: '产品总箱数',
    key: 'productCtns',
    width: 104,
    align: 'right',
    render: (row) => countText(row.productCtns),
  },
  {
    title: '差额',
    key: 'diff',
    width: 72,
    align: 'right',
    render: (row) => diffText(row.diff),
  },
  {
    title: '说明',
    key: 'message',
    ellipsis: { tooltip: true },
    render: (row) => row.message || (row.kind === 'mismatch' ? '不一致' : '—'),
  },
]

const summaryText = computed(() => {
  const data = result.value
  if (!data) return ''
  return `${data.matched} 票一致`
})

watch(
  () => [props.show, props.ids.join('\n')] as const,
  async ([open]) => {
    const current = ++revision
    result.value = null
    errorText.value = ''
    if (!open || !props.ids.length) return
    loading.value = true
    try {
      const data = await checkShipmentProductCtns(props.ids)
      if (current === revision) result.value = data
    } catch (error) {
      if (current === revision) errorText.value = errorMessage(error)
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
    title="核对件数"
    :style="{ width: 'min(720px, calc(100vw - 2rem))' }"
    :auto-focus="false"
  >
    <p v-if="errorText" class="text-sm text-red-600">{{ errorText }}</p>
    <template v-else>
      <p v-if="!loading && result" class="mb-2 text-sm text-[var(--color-muted)]">
        {{ summaryText }}
        <template v-if="result.issues.length">，下面 {{ result.issues.length }} 票需要看一下</template>
      </p>
      <div class="mb-3 flex justify-end">
        <NButton size="small" :disabled="loading || !mismatchNos.length" @click="copyMismatchNos">复制不一致单号（{{ mismatchNos.length }}）</NButton>
      </div>
      <NDataTable
        size="small"
        :loading="loading"
        :columns="columns"
        :data="result?.issues ?? []"
        :pagination="false"
        :max-height="360"
        :row-class-name="(row: ProductCtnsCheckIssue) => (row.kind === 'mismatch' ? 'product-ctns-mismatch' : '')"
      >
        <template #empty>
          <span class="text-sm text-[var(--color-muted)]">没有不一致或查询失败的票</span>
        </template>
      </NDataTable>
    </template>
  </NModal>
</template>

<style scoped>
:global(.product-ctns-mismatch td) {
  background: #fffbeb;
  color: #78350f;
}

:global([data-theme='dark'] .product-ctns-mismatch td) {
  background: rgb(69 26 3 / 0.45);
  color: #fef3c7;
}
</style>
