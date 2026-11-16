<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NModal, NInput, NCheckbox, NButton, NPopover, useMessage } from 'naive-ui'
import { startTask, finishTask, type RunningTask } from '@/composables/useRunningTasks'
import { api } from '@/api/client'
defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: []; updated: []; progress: [value: { running: boolean; total: number; done: number; success: number; saved: number; conflict: number; skipped: number; failed: number }] }>()
const message = useMessage()
const text = ref('')
const force = ref(false)
const running = ref(false)
const results = ref<{ line: number; shipmentNo: string; shipmentId: string; referenceId: string; status: string; message: string; existingShipmentId?: string }[]>([])
const batchTotal = ref(0)
let globalTask: RunningTask | null = null
watch(() => [running.value, results.value.length, batchTotal.value], () => {
  const count = (status: string) => results.value.filter(row => row.status === status).length
  if (globalTask) {
    globalTask.progress = batchTotal.value ? results.value.length / batchTotal.value * 100 : 0
    globalTask.message = `已处理 ${results.value.length}/${batchTotal.value} · 成功 ${count('success')} · 未推送成功 ${count('saved')} · 冲突 ${count('conflict')} · 跳过 ${count('skipped')} · 失败 ${count('failed')}`
    globalTask.details = results.value.map(row => `${row.shipmentNo}\t${row.shipmentId}\t${row.referenceId}\t${row.message}${row.existingShipmentId ? '；原货件号：' + row.existingShipmentId : ''}`).join('\n')
  }
  emit('progress', {running: running.value, total: batchTotal.value, done: results.value.length, success: count('success'), saved: count('saved'), conflict: count('conflict'), skipped: count('skipped'), failed: count('failed')})
}, { flush: 'sync' })
const lines = computed(() => text.value.replace(/\\/g, '\n').split(/\r?\n/).filter(x => x.trim()))
const parsed = computed(() => {
  const rows = lines.value.map((line, index) => {
    const parts = line.trim().split(/[\s=＝]+/)
    return { line: index + 1, shipmentNo: parts[0] || '', shipmentId: parts[1] || '', referenceId: parts[2] || '', status: 'preview', message: parts.length !== 3 ? '格式错误，应为运单号 货件号 预约号' : parts[1] === '1' || parts[2] === '1' ? '货件号或预约号无效' : '解析正常，执行时校验系统货件号', existingShipmentId: '' }
  })
  const counts = new Map<string, number>()
  rows.forEach(row => counts.set(row.shipmentNo, (counts.get(row.shipmentNo) || 0) + 1))
  return rows.map(row => (counts.get(row.shipmentNo) || 0) > 1 ? { ...row, message: '重复运单号，将跳过' } : row)
})
const displayRows = computed(() => parsed.value.map((row, index) => results.value[index] || row))
watch(text, () => { if (!running.value) results.value = [] })
const summary = computed(() => ['success', 'saved', 'conflict', 'skipped', 'failed'].map(status => `${({success:'推送成功',saved:'已保存未推送成功',conflict:'冲突',skipped:'跳过',failed:'失败'} as Record<string,string>)[status]} ${results.value.filter(x => x.status === status).length}`).join('，'))
async function run() {
  if (running.value || !lines.value.length || lines.value.length > 200) return
  globalTask = startTask('批量推送货件号 / 预约号')
  results.value = []
  batchTotal.value = lines.value.length
  running.value = true
  const input = text.value
  const forceThisBatch = force.value
  try {
    for (let index = 0; index < lines.value.length; index++) {
      try {
        const result = await api<(typeof results.value)[number]>('/api/v1/shipment-amazon-refs/batch-row', { method: 'POST', body: { text: input, lineIndex: index, force: forceThisBatch, taskId: globalTask?.id }, timeout: 60000, retry: 0 })
        results.value.push(result)
      } catch {
        results.value.push({line:index+1,shipmentNo:lines.value[index]?.trim().split(/[\s=＝]+/)[0] || '',shipmentId:'',referenceId:'',status:'failed',message:'请求异常，结果可能已保存或推送，请核对后重试'})
      }
    }
  } finally {
    running.value = false
    force.value = false
    if (globalTask) finishTask(globalTask, results.value.some(row => row.status !== 'success'))
    emit('updated')
    message.info('批量处理完成，可重新打开窗口查看或复制结果')
  }
}
async function copy() {
  try {
    await navigator.clipboard.writeText(summary.value + '\n' + results.value.map(x => `${x.shipmentNo}\t${x.shipmentId}\t${x.referenceId}\t${x.message}${x.existingShipmentId ? '；系统货件号：' + x.existingShipmentId : ''}`).join('\n'))
    message.success('已复制结果')
  } catch { message.error('复制失败') }
}
</script>
<template>
  <NModal :show="show" preset="card" title="批量补货件号 / 预约号" :style="{width:'900px',maxWidth:'95vw'}" :mask-closable="true" :closable="true" @update:show="v => { if (!v) emit('close') }">
    <p class="mb-3 text-sm">每行：运单号 = 货件号 预约号（也支持空格分隔及行尾反斜杠），最多 200 票。默认跳过货件号冲突票，可勾选强制覆盖；其他票保存并推送，失败不回滚已保存数据。</p>
    <NInput v-model:value="text" type="textarea" :disabled="running" :autosize="{minRows:5,maxRows:12}" placeholder="EXAMPLE-001 = FBA-EXAMPLE REF-EXAMPLE" />
    <div class="mt-3">
      <NCheckbox v-model:checked="force" :disabled="running">强制覆盖冲突货件号并推送（仅本批次）</NCheckbox>
      <p v-if="force" class="mt-1 text-xs text-amber-600">冲突票将使用输入的货件号和预约号覆盖本地数据并推送；推送失败不会回滚。结果保留原货件号供核对。</p>
    </div>
    <div class="my-3 flex gap-2">
      <NButton type="primary" :loading="running" :disabled="running || !lines.length || lines.length > 200" @click="run">批量保存并推送（{{ lines.length }} 票）</NButton>
      <NButton :disabled="!results.length" @click="copy">复制结果</NButton>
      <NButton @click="emit('close')">{{ running ? '收起，继续处理' : '关闭' }}</NButton>
    </div>
    <p v-if="running" class="mb-2 text-xs text-[var(--color-muted)]">可关闭窗口继续处理，重新打开可查看进度；请勿刷新或关闭浏览器页面。</p>
    <p class="mb-2 text-xs text-[var(--color-muted)]">输入后即时解析，系统货件号冲突在执行时校验。{{ lines.length > 200 ? '超过 200 票，请拆分批次' : '' }}</p>
    <p>{{ summary }}<span v-if="running">（处理中 {{ results.length }}/{{ lines.length }}）</span></p>
    <div class="mt-3 max-h-96 overflow-auto text-sm">
      <table class="batch-results">
        <colgroup><col style="width:180px"><col style="width:155px"><col style="width:115px"><col></colgroup>
        <thead><tr><th>运单号</th><th>输入货件号</th><th>预约号</th><th>结果 / 原因</th></tr></thead>
        <tbody>
          <tr v-for="row in displayRows" :key="row.line">
            <td class="batch-id" :title="row.shipmentNo">{{ row.shipmentNo }}</td>
            <td class="batch-id" :title="row.shipmentId">{{ row.shipmentId }}</td>
            <td class="batch-id" :title="row.referenceId">{{ row.referenceId }}</td>
            <td>
              <div class="batch-result-cell" :class="row.status === 'success' ? 'text-green-600' : 'text-amber-600'">
                <NPopover trigger="hover" placement="top" :style="{ maxWidth: 'min(520px, 85vw)' }">
                  <template #trigger><span class="batch-reason">{{ row.message }}{{ row.existingShipmentId ? '；系统货件号：' + row.existingShipmentId : '' }}</span></template>
                  <div class="batch-detail">{{ row.message }}<div v-if="row.existingShipmentId">系统货件号：{{ row.existingShipmentId }}</div></div>
                </NPopover>
                <NPopover trigger="click" placement="top" :style="{ maxWidth: 'min(520px, 85vw)' }">
                  <template #trigger><button type="button" class="batch-detail-button">详情</button></template>
                  <div class="batch-detail">{{ row.message }}<div v-if="row.existingShipmentId">系统货件号：{{ row.existingShipmentId }}</div></div>
                </NPopover>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </NModal>
</template>

<style scoped>
.batch-results { width: 100%; min-width: 780px; table-layout: fixed; text-align: left; border-collapse: collapse; }
.batch-results th { position: sticky; top: 0; z-index: 1; background: var(--color-surface); color: var(--color-muted); font-size: 12px; font-weight: 500; }
.batch-results th, .batch-results td { padding: 10px 12px; border-bottom: 1px solid var(--color-border); }
.batch-id { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.batch-result-cell { display: flex; align-items: center; gap: 8px; min-width: 0; }
.batch-reason { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: help; }
.batch-detail-button { flex-shrink: 0; color: var(--color-accent); font-size: 12px; cursor: pointer; }
.batch-detail-button:hover { text-decoration: underline; }
.batch-detail { max-height: 280px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.6; }
</style>
