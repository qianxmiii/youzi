<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NAlert, NButton, NInput, NModal, NPopconfirm, useMessage } from 'naive-ui'
import { Copy } from 'lucide-vue-next'
import { updateShipmentRemarks } from '@/api/shipments'
import { trackTask } from '@/composables/useRunningTasks'
import type { Shipment } from '@/types/shipment'

const props = defineProps<{ show: boolean; shipments: Shipment[] }>()
const emit = defineEmits<{ close: []; updated: [] }>()
const message = useMessage()
const remark = ref('')
const busy = ref(false)
const isSingle = computed(() => props.shipments.length === 1)
const missingWaybill = computed(() => props.shipments.filter((row) => !row.waybillId?.trim()))
const originalRemark = computed(() => props.shipments[0]?.remark || '')
const unchanged = computed(() => isSingle.value && remark.value.trim() === originalRemark.value.trim())

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
    remark.value = isSingle.value ? originalRemark.value : ''
  },
)

function close() {
  if (!busy.value) emit('close')
}

async function submit() {
  if (busy.value || !props.shipments.length || props.shipments.length > 200 || missingWaybill.value.length) return
  busy.value = true
  try {
    const ids = props.shipments.map((row) => row.id)
    const result = await trackTask(
      isSingle.value ? '内部备注 · 单票覆盖' : '内部备注 · 批量覆盖',
      (taskId) => updateShipmentRemarks(ids, remark.value, taskId),
    )
    message.success(`已覆盖 ${result.updated} 票内部备注`)
    emit('updated')
    emit('close')
  } catch (error) {
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
    :title="isSingle ? '修改内部备注' : '批量覆盖内部备注'"
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
      <p class="mb-3 text-sm">已选择 {{ shipments.length }} 票，以下运单将统一覆盖为同一条备注。</p>
      <div class="mb-4 max-h-56 overflow-auto rounded border border-[var(--color-border)]">
        <table class="remark-table w-full table-fixed text-sm">
          <thead class="text-left">
            <tr><th class="w-44 px-3 py-2" scope="col">运单号</th><th class="px-3 py-2" scope="col">修改前 <span class="readonly-label">只读</span></th><th class="w-16 px-3 py-2" scope="col">操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="row in shipments" :key="row.id" class="border-t border-[var(--color-border)] align-top">
              <td class="break-all px-3 py-2">
                <div>{{ row.shipmentNo }}</div>
                <div class="mt-1 text-xs text-[var(--color-muted)]">件数：{{ row.ctns ?? '—' }}</div>
                <div class="mt-1 text-xs text-[var(--color-muted)]">{{ destinationLabel(row) }}</div>
              </td>
              <td class="px-3 py-2"><div class="original-remark original-remark--cell">{{ row.remark || '暂无内部备注' }}</div></td>
              <td class="px-3 py-2"><NButton size="tiny" quaternary circle type="primary" :title="`复制 ${row.shipmentNo} 备注`" :aria-label="`复制 ${row.shipmentNo} 备注`" :disabled="!row.remark" @click="copyRemark(row.remark, `${row.shipmentNo} 备注`)"><template #icon><Copy :size="14" /></template></NButton></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <div class="mb-2 mt-4 flex items-center justify-between">
      <label class="text-sm font-medium">修改后</label>
      <NButton size="tiny" quaternary circle type="primary" title="复制修改后备注" aria-label="复制修改后备注" :disabled="!remark" @click="copyRemark(remark, '修改后备注')"><template #icon><Copy :size="14" /></template></NButton>
    </div>
    <NInput
      v-model:value="remark"
      type="textarea"
      :disabled="busy"
      :maxlength="5000"
      show-count
      :autosize="{ minRows: 4, maxRows: 10 }"
      placeholder="填写新的内部备注；留空并确认表示清空备注"
    />
    <p class="mt-2 text-xs text-amber-600">DPS 更新方式为覆盖，不会追加到原备注；远端成功后才更新本地显示。</p>

    <div class="mt-5 flex justify-end gap-2">
      <NButton :disabled="busy" @click="close">取消</NButton>
      <NPopconfirm @positive-click="submit">
        <template #trigger>
          <NButton
            type="primary"
            :loading="busy"
            :disabled="busy || !shipments.length || shipments.length > 200 || !!missingWaybill.length || unchanged"
          >
            确认覆盖
          </NButton>
        </template>
        将覆盖 {{ shipments.length }} 票现有内部备注，确定继续？
      </NPopconfirm>
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
