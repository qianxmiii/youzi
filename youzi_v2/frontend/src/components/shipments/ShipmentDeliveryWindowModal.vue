<script setup lang="ts">
import { NAlert, NButton, NDatePicker, NForm, NFormItem, NModal, NSelect, useMessage } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { getDeliveryWindow, getDeliveryWindowHistory, previewDeliveryWindow, saveDeliveryWindow, type DeliveryHistory, type HistoryMetric, type DeliveryWindow, type WindowMode } from '@/api/deliveryWindow'
import type { Shipment } from '@/types/shipment'
import { formatShipmentDWCopyText } from '@/utils/deliveryWindowCopy'

const props = defineProps<{ show: boolean; shipment: Shipment | null }>()
const emit = defineEmits<{ 'update:show': [value: boolean] }>()
const message = useMessage()
const loading = ref(false)
const mode = ref<WindowMode>('auto')
const manualStart = ref<string | null>(null)
const manualEnd = ref<string | null>(null)
const result = ref<DeliveryWindow | null>(null)
const history = ref<DeliveryHistory | null>(null)
const historyLoading = ref(false)
const historyError = ref('')
const metricRows = [{ key: 'full' as const, label: '离港至送仓' }, { key: 'postArrival' as const, label: '到港后送仓' }]
const metricText = (metric: HistoryMetric) => metric.p50Days == null ? '暂无可识别批次' : `${metric.p50Days}—${metric.p90Days}天 / ${metric.batchCount}批次 · ${metric.ticketCount}票`
let historyRevision = 0
watch([() => props.show, () => props.shipment?.id, mode], async ([open, id, selectedMode]) => {
  const current = ++historyRevision
  history.value = null
  historyError.value = ''
  historyLoading.value = false
  if (!open || !id) return
  historyLoading.value = true
  try {
    const data = await getDeliveryWindowHistory(String(id), selectedMode)
    if (current === historyRevision) history.value = data
  } catch {
    if (current === historyRevision) historyError.value = '历史参考加载失败，可继续使用配置窗口。'
  } finally { if (current === historyRevision) historyLoading.value = false }
})
const options = [
  { label: '按地址类型（AMZ使用周窗口）', value: 'auto' },
  { label: '普通日期范围', value: 'range' },
  { label: 'Amazon单周窗口（周日—周六）', value: 'amazon' },
]
const payload = computed(() => ({ mode: mode.value, manualStart: manualStart.value, manualEnd: manualEnd.value }))
let revision = 0
watch([() => props.show, () => props.shipment?.id], async ([open, id]) => {
  const current = ++revision
  mode.value = 'auto'
  manualStart.value = null
  manualEnd.value = null
  result.value = null
  if (!open || !id) return
  loading.value = true
  try {
    const data = await getDeliveryWindow(String(id))
    if (revision !== current) return
    mode.value = data.requestedMode
    manualStart.value = data.manualStart
    manualEnd.value = data.manualEnd
    result.value = data
  } catch { if (revision === current) message.error('DW加载失败，请重试') }
  finally { if (revision === current) loading.value = false }
})
// Any edit invalidates the previous preview; do not copy a stale window.
watch(payload, () => { result.value = null }, { flush: 'sync' })
async function calculate(save: boolean) {
  if (!props.shipment || loading.value) return
  if (!!manualStart.value !== !!manualEnd.value || (manualStart.value && manualEnd.value! < manualStart.value)) {
    message.warning('请填写完整且顺序正确的人工日期范围'); return
  }
  const current = revision
  loading.value = true
  try {
    const action = save ? saveDeliveryWindow : previewDeliveryWindow
    const data = await action(props.shipment.id, payload.value)
    if (current !== revision) return
    result.value = data
    if (save) message.success('DW设置已保存')
  } catch { if (current === revision) message.error('DW处理失败，请检查日期后重试') }
  finally { if (current === revision) loading.value = false }
}
async function copy() {
  if (!result.value?.copyText || !props.shipment) return
  try { await navigator.clipboard.writeText(formatShipmentDWCopyText(props.shipment, result.value.copyText)); message.success('已复制运单明细及DW') }
  catch { message.error('复制失败，请检查浏览器权限') }
}
async function adoptHistory() {
  if (!history.value?.prediction || loading.value) return
  manualStart.value = history.value.prediction.start
  manualEnd.value = history.value.prediction.end
  await calculate(false)
  message.info('已填入历史参考，请核对后保存；尚未修改原有设置。')
}
</script>

<template>
  <NModal :show="show" preset="card" :title="`DW · ${shipment?.shipmentNo || ''}`" class="w-[min(560px,calc(100vw-2rem))]" @update:show="emit('update:show', $event)">
    <NForm label-placement="top" :disabled="loading">
      <NFormItem label="窗口类型"><NSelect v-model:value="mode" :options="options" /></NFormItem>
      <NFormItem label="人工确认窗口（可选，优先使用；清空两项恢复自动预测）">
        <div class="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
          <NDatePicker v-model:formatted-value="manualStart" type="date" value-format="yyyy-MM-dd" clearable placeholder="开始日期" aria-label="人工窗口开始日期" />
          <NDatePicker v-model:formatted-value="manualEnd" type="date" value-format="yyyy-MM-dd" clearable placeholder="结束日期" aria-label="人工窗口结束日期" />
        </div>
      </NFormItem>
    </NForm>
    <div aria-live="polite" class="space-y-3">
      <template v-if="result">
        <p class="text-xl font-semibold text-[var(--color-fg)]">{{ result.copyText || '暂无法生成DW' }}</p>
        <p class="text-sm text-[var(--color-fg-secondary)]">{{ result.start }} {{ result.end ? `至 ${result.end}` : '' }}</p>
        <p class="text-sm">{{ result.reason || result.basis }}</p>
        <p class="text-xs text-[var(--color-fg-secondary)]">当前复制使用：{{ result.source === 'manual' ? '人工确认／未保存的人工预览' : '渠道配置' }}</p>
        <NAlert v-if="result.warnings.length" type="warning" :show-icon="false"><p v-for="warning in result.warnings" :key="warning">{{ warning }}</p></NAlert>
      </template>
      <p v-else class="text-sm text-[var(--color-fg-secondary)]">{{ loading ? '正在计算…' : '设置已改变，请重新预览或保存后复制。' }}</p>
      <p class="text-xs text-[var(--color-fg-secondary)]">自动值仅作参考；Amazon人工日期须为同一周周日至周六，其他范围请选普通模式。复制包含运单明细和月日范围，跨年也不附年份。预览不会保存设置。</p>
      <section class="space-y-2 border-t border-[var(--color-border)] pt-3" aria-label="历史送仓时效参考">
        <h3 class="font-semibold">近期历史参考（不自动覆盖配置或人工窗口）</h3>
        <p v-if="historyLoading" class="text-sm" role="status">正在读取历史时效…</p>
        <p v-else-if="historyError" class="text-sm">{{ historyError }}</p>
        <template v-else-if="history">
          <p class="text-xs text-[var(--color-fg-secondary)]">{{ history.scope }} · 近{{ history.lookbackDays }}天签收{{ history.completedCount }}票 / {{ history.independentBatchCount }}个可识别批次</p>
          <div class="overflow-x-auto">
            <table class="w-full whitespace-nowrap text-left text-xs">
              <caption class="pb-2 text-left">批次P50—P90（自然日）</caption>
              <thead><tr><th scope="col" class="p-2">时效段</th><th scope="col" class="p-2">实际含异常</th><th scope="col" class="p-2">正常参考</th><th scope="col" class="p-2">近30天含异常</th></tr></thead>
              <tbody><tr v-for="item in metricRows" :key="item.key"><th scope="row" class="p-2">{{ item.label }}</th><td class="p-2">{{ metricText(history.metrics[item.key].actual) }}</td><td class="p-2">{{ metricText(history.metrics[item.key].normal) }}</td><td class="p-2">{{ metricText(history.metrics[item.key].recent30) }}</td></tr></tbody>
            </table>
          </div>
          <template v-if="history.prediction">
            <p class="font-semibold">历史参考DW：{{ history.prediction.copyText }}</p>
            <p class="text-xs">{{ history.prediction.basis }}</p>
            <p v-for="warning in history.prediction.warnings" :key="warning" class="text-xs text-[var(--color-fg-secondary)]">{{ warning }}</p>
            <NButton size="small" :disabled="loading" @click="adoptHistory">填入历史窗口（需核对保存）</NButton>
          </template>
          <p v-else class="text-sm">{{ history.reason }}</p>
          <details class="text-xs text-[var(--color-fg-secondary)]"><summary class="cursor-pointer">数据说明与限制</summary>
            <p>同渠道、国家和地址类型下，近90天离港仍未签收{{ history.inTransitCount }}票（不含本票，尚未按承运商或目的港细分）；未知批次{{ history.unknownBatchTickets }}票，长异常{{ history.longExceptionCount }}票。</p>
            <p>正常参考排除当前异常及历史单次异常超过7天的票。每个可识别批次先取中位数，再计算分位数。</p>
            <p v-for="warning in history.warnings" :key="warning">{{ warning }}</p>
          </details>
        </template>
      </section>
    </div>
    <template #footer>
      <div class="flex flex-wrap justify-end gap-2">
        <NButton :disabled="loading" @click="calculate(false)">预览</NButton>
        <NButton :disabled="loading" @click="calculate(true)">保存设置</NButton>
        <NButton type="primary" :disabled="loading || !result?.copyText" @click="copy">复制DW</NButton>
      </div>
    </template>
  </NModal>
</template>
