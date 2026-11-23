<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NAlert, NButton, NInput, NModal, NRadioButton, NRadioGroup, useMessage } from 'naive-ui'
import { Copy } from 'lucide-vue-next'
import { updateShipmentRemarks, type ShipmentRemarkMode, type ShipmentRemarkResult } from '@/api/shipments'
import { trackTask } from '@/composables/useRunningTasks'
import type { Shipment } from '@/types/shipment'

const props = defineProps<{ show: boolean; shipments: Shipment[]; batch?: boolean }>()
const emit = defineEmits<{ close: []; updated: [] }>()
const message = useMessage()
const remark = ref('')
const busy = ref(false)
const isSingle = computed(() => !props.batch && props.shipments.length === 1)
const mode = ref<ShipmentRemarkMode>('append')
const appending = computed(() => !isSingle.value && mode.value === 'append')
const appendResults = ref<ShipmentRemarkResult[] | null>(null)
const submissionUncertain = ref(false)
const resultById = computed(() => new Map(appendResults.value?.map(row => [row.id, row])))
const failedIds = computed(() => appendResults.value?.filter(row => row.status === 'failed').map(row => row.id) ?? [])
const statusLabels = { success: '成功', failed: '失败', unknown: '待核对' }
const missingWaybill = computed(() => props.shipments.filter((row) => !row.waybillId?.trim()))
const originalRemark = computed(() => props.shipments[0]?.remark || '')
const unchanged = computed(() => isSingle.value && remark.value.trim() === originalRemark.value.trim())
const canSubmit = computed(() => !busy.value && !submissionUncertain.value && props.shipments.length > 0 &&
  props.shipments.length <= 200 && (appending.value ? !!remark.value.trim() : !missingWaybill.value.length && !unchanged.value))

function appendPreview(row: Shipment) {
  const previous = (row.remark || '').replace(/\r\n?/g, '\n')
  const addition = remark.value.replace(/\r\n?/g, '\n').trim()
  if (!addition) return previous
  if (!previous.trim()) return addition
  return `${previous}${previous.endsWith('\n') ? '' : '\n'}${addition}`
}

function destinationLabel(row: Shipment) {
  const warehouse = row.addressCode?.trim()
  if (warehouse) return `仓库地址：${warehouse}`
  const zipcode = row.zipcode?.trim()
  return zipcode ? `邮编：${zipcode}` : '仓库地址／邮编：—'
}

watch(
  () => props.show,
  (open) => {
    if (!open) return
    mode.value = 'append'
    appendResults.value = null
    submissionUncertain.value = false
    remark.value = isSingle.value ? originalRemark.value : ''
  },
)

function close() {
  if (!busy.value) emit('close')
}

async function submit(retry = false) {
  if (!canSubmit.value || retry !== (appendResults.value !== null)) return
  const ids = retry ? failedIds.value : props.shipments.map(row => row.id)
  if (!ids.length) return
  const append = appending.value
  busy.value = true
  try {
    const result = await trackTask(
      append ? '内部备注 · 批量追加' : isSingle.value ? '内部备注 · 单票覆盖' : '内部备注 · 批量覆盖',
      taskId => updateShipmentRemarks(ids, remark.value, taskId, append ? 'append' : 'replace'),
    )
    if (append) {
      if (!result.remarkResults) {
        submissionUncertain.value = true
        emit('updated')
        return
      }
      const merged = new Map(resultById.value)
      for (const row of result.remarkResults) merged.set(row.id, row)
      appendResults.value = [...merged.values()]
      const summary = `成功 ${result.updated} 票，失败 ${result.failed} 票，待核对 ${result.unknown ?? 0} 票`
      if (result.failed || result.unknown) message.warning(summary)
      else message.success(summary)
    } else {
      message.success(`已覆盖 ${result.updated} 票内部备注`)
      emit('close')
    }
    emit('updated')
  } catch (error) {
    const status = (error as { status?: number })?.status
    if (append && (!status || status >= 500 || status === 408)) submissionUncertain.value = true
    message.error(
      (error as { data?: { detail?: string } })?.data?.detail ||
        (error instanceof Error ? error.message : '内部备注更新失败，请核对 DPS 结果'),
    )
  } finally {
    busy.value = false
  }
}

async function copyRemark(value: string | null | undefined, label = '备注') {
  const text = value || ''
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制${label}`)
  } catch {
    message.error('复制失败')
  }
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="isSingle ? '修改内部备注' : '批量内部备注'"
    :style="{ width: '760px', maxWidth: '95vw' }"
    :closable="!busy"
    :mask-closable="!busy"
    @update:show="(value) => { if (!value) close() }"
  >
    <NAlert v-if="missingWaybill.length" type="warning" class="mb-4">
      {{ missingWaybill.map((row) => row.shipmentNo).join('、') }} 缺少 DPS 运单 ID，请先更新运单。
    </NAlert>

    <template v-if="isSingle">
      <div v-if="shipments[0]" class="mb-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-[var(--color-muted)]">
        <span>运单号：{{ shipments[0].shipmentNo }}</span>
        <span>件数：{{ shipments[0].ctns ?? '—' }}</span>
        <span class="break-words">{{ destinationLabel(shipments[0]) }}</span>
      </div>
      <div class="mb-2 flex items-center justify-between">
        <span id="original-remark-label" class="text-sm font-medium">修改前 <span class="readonly-label">只读</span></span>
        <NButton size="tiny" quaternary circle type="primary" title="复制修改前备注" aria-label="复制修改前备注" :disabled="!originalRemark" @click="copyRemark(originalRemark, '修改前备注')"><template #icon><Copy :size="14" /></template></NButton>
      </div>
      <div class="original-remark" role="textbox" aria-readonly="true" aria-multiline="true" aria-labelledby="original-remark-label" tabindex="0">{{ originalRemark || '暂无内部备注' }}</div>
    </template>

    <template v-else>
      <div class="mb-3 flex flex-wrap items-center gap-3 text-sm">
        <span>已选择 {{ shipments.length }} 票</span>
        <NRadioGroup v-model:value="mode" size="small" aria-label="备注更新方式" :disabled="busy || appendResults !== null || submissionUncertain">
          <NRadioButton value="append">追加</NRadioButton>
          <NRadioButton value="replace">覆盖</NRadioButton>
        </NRadioGroup>
      </div>
      <div class="mb-4 max-h-56 overflow-auto rounded border border-[var(--color-border)]">
        <table class="remark-table w-full table-fixed text-sm">
          <thead class="text-left">
            <tr>
              <th class="w-44 px-3 py-2" scope="col">运单号</th>
              <th class="px-3 py-2" scope="col">修改前 <span class="readonly-label">只读</span></th>
              <th v-if="appending" class="px-3 py-2" scope="col">{{ appendResults ? '追加结果' : '追加预览' }}</th>
              <th class="w-16 px-3 py-2" scope="col">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in shipments" :key="row.id" class="border-t border-[var(--color-border)] align-top">
              <td class="break-all px-3 py-2">
                <div>{{ row.shipmentNo }}</div>
                <div class="mt-1 text-xs text-[var(--color-muted)]">件数：{{ row.ctns ?? '—' }}</div>
                <div class="mt-1 text-xs text-[var(--color-muted)]">{{ destinationLabel(row) }}</div>
              </td>
              <td class="px-3 py-2"><div class="original-remark original-remark--cell">{{ row.remark || '暂无内部备注' }}</div></td>
              <td v-if="appending" class="px-3 py-2">
                <template v-if="resultById.get(row.id)">
                  <strong>{{ statusLabels[resultById.get(row.id)!.status] }}</strong>
                  <p class="mt-1 break-words">{{ resultById.get(row.id)?.message }}</p>
                </template>
                <div v-else class="original-remark original-remark--cell">{{ appendPreview(row) || '—' }}</div>
              </td>
              <td class="px-3 py-2"><NButton size="tiny" quaternary circle type="primary" :title="`复制 ${row.shipmentNo} 备注`" :aria-label="`复制 ${row.shipmentNo} 备注`" :disabled="!row.remark" @click="copyRemark(row.remark, `${row.shipmentNo} 备注`)"><template #icon><Copy :size="14" /></template></NButton></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div class="mb-2 mt-4 flex items-center justify-between">
      <label class="text-sm font-medium">{{ appending ? '追加内容' : '修改后' }}</label>
      <NButton size="tiny" quaternary circle type="primary" title="复制修改后备注" aria-label="复制修改后备注" :disabled="!remark" @click="copyRemark(remark, '修改后备注')"><template #icon><Copy :size="14" /></template></NButton>
    </div>
    <NInput
      v-model:value="remark"
      type="textarea"
      :disabled="busy || submissionUncertain || (appendResults !== null && !failedIds.length)"
      :maxlength="5000"
      show-count
      :autosize="{ minRows: 4, maxRows: 10 }"
      :placeholder="appending ? '输入要另起一行追加的内容' : '填写新的内部备注（留空保存将清空原备注）'"
    />
    <p v-if="appending && !appendResults" class="mt-2 text-xs text-[var(--color-muted)]">预览基于列表中的备注，提交时以 DPS 最新备注为准。</p>
    <p v-else-if="!appending" class="mt-2 text-xs text-amber-600">保存会覆盖原备注，留空保存会清空原备注。</p>
    <NAlert v-if="submissionUncertain" type="warning" class="mt-3">未收到完整提交结果，请先到任务中心或 DPS 核对。</NAlert>

    <div class="mt-5 flex justify-end gap-2">
      <NButton :disabled="busy" @click="close">{{ appendResults || submissionUncertain ? '关闭' : '取消' }}</NButton>
      <NButton
        v-if="!appendResults || failedIds.length"
        type="primary"
        :loading="busy"
        :disabled="!canSubmit"
        @click="submit(appendResults !== null)"
      >
        {{ appending ? appendResults ? `重试失败的 ${failedIds.length} 票` : `追加到 ${shipments.length} 票` : '保存' }}
      </NButton>
    </div>
  </NModal>
</template>

<style scoped>
.remark-table {
  border-collapse: separate;
  border-spacing: 0;
}

.remark-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-panel);
  box-shadow: 0 1px 0 var(--color-border);
}

.remark-table tbody td {
  border-top: 1px solid var(--color-border);
}

.readonly-label {
  display: inline-block;
  padding: 1px 6px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-border-subtle);
  color: var(--color-fg-secondary);
  font-size: 12px;
  font-weight: 400;
  white-space: nowrap;
}

.original-remark {
  min-height: 88px;
  max-height: 200px;
  overflow: auto;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-border-subtle);
  color: var(--color-fg-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  cursor: text;
  user-select: text;
}

.original-remark--cell {
  min-height: auto;
  max-height: none;
  padding: 8px 10px;
}
</style>
