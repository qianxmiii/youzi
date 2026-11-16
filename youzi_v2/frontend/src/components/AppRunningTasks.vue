<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { NPopover, NPopconfirm, NButton, NProgress, NModal, NTag, NDataTable, useMessage, type DataTableColumns } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useNow } from '@vueuse/core'
import { api } from '@/api/client'
import { LoaderCircle, ListTodo, RefreshCw, Trash2, EyeOff, History, ChevronRight, Clock3, CircleCheck, CircleAlert, Info, Inbox } from 'lucide-vue-next'
import { useRunningTasks, loadTaskHistory, persistTask, deleteTaskHistory, type RunningTask } from '@/composables/useRunningTasks'
const { tasks, hiddenTaskIds, clearFinished, historyError, historyLoading, historyMore } = useRunningTasks()
const running = computed(() => tasks.filter(t => t.state === 'running' && !t.historical))
const showHistory = ref(false)
const deletingId = ref('')
async function removeRecord(task: RunningTask) {
  deletingId.value = task.id
  try { await deleteTaskHistory(task); message.success('记录及关联操作明细已删除') }
  catch (error) { message.error((error as {data?:{detail?:string}})?.data?.detail || '删除失败，请重试') }
  finally { deletingId.value = '' }
}
const completed = computed(() => tasks.filter(t => (t.state !== 'running' || t.historical) && (showHistory.value || !hiddenTaskIds.value.includes(t.id))).sort((a,b) => b.started-a.started))
const groups = computed(() => [{label:'正在进行',items:running.value},{label:showHistory.value ? '全部历史' : '最近记录',items:completed.value}].filter(group => group.items.length))
const now = useNow({interval:1000})
function stateOf(task: RunningTask) { return task.historical && task.state === 'running' ? 'unknown' : task.state }
function statusText(task: RunningTask) { return ({running:'进行中',done:'已完成',failed:'需关注',unknown:'待确认'})[stateOf(task)] }
function taskName(task: RunningTask) { return task.source && task.title.startsWith(task.source + ' · ') ? task.title.slice(task.source.length + 3) : task.title }
function duration(task: RunningTask) {
  if (stateOf(task) === 'unknown') return '结果待核对'
  const seconds = Math.max(0, Math.floor(((task.finished || now.value.getTime()) - task.started) / 1000))
  const value = seconds < 60 ? `${seconds}秒` : seconds < 3600 ? `${Math.floor(seconds / 60)}分${seconds % 60}秒` : `${Math.floor(seconds / 3600)}小时${Math.floor(seconds % 3600 / 60)}分`
  return `${task.state === 'running' ? '已运行' : '耗时'} ${value}`
}
function startedLabel(task: RunningTask) { return new Date(task.started).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}) }
function hasSummary(task: RunningTask) { return task.message && !['处理中','正在处理','处理完成'].includes(task.message.trim()) }
const issue = computed(() => tasks.some(t => t.unseen && t.state === 'failed' && !hiddenTaskIds.value.includes(t.id)))
const selected = ref<RunningTask | null>(null)
const detailShow = ref(false)
const message = useMessage()
const auditText = ref('')
const router = useRouter()
let historyTimer: ReturnType<typeof setInterval> | undefined
onMounted(() => { void loadTaskHistory(); historyTimer = setInterval(() => { if (tasks.some(t => t.state === 'running' || (t.managedBy === 'request' && Date.now() - (t.finished || 0) < 10000))) void loadTaskHistory() }, 3000) })
onUnmounted(() => { if (historyTimer) clearInterval(historyTimer) })
async function open(task: RunningTask) {
  if (task.managedBy === 'server' && task.href?.startsWith('/tools/link-download?job=')) { task.unseen = false; await router.push(task.href); return }
  auditText.value = '';  filter.value = 'all'; selected.value = task; task.unseen = false; detailShow.value = true
  try {
    const result = await api<{items:{shipmentNo:string; recordedAt:string; before:Record<string,unknown>; after:Record<string,unknown>; result:Record<string,unknown>}[]}>(`/api/v1/task-history/${encodeURIComponent(task.id)}/events`)
    if (selected.value?.id !== task.id) return
    auditText.value = result.items.map(row => 'marks' in row.before ? `${row.shipmentNo} · ${row.recordedAt}\n原标识：${JSON.stringify(row.before.marks)}\n操作：${['增加','移除','编辑'][Number(row.after.type)] || '标识更新'}\n标识 ID：${JSON.stringify(row.after.markIds)}\n${row.result.message || '已登记操作，结果需核对'}` : `${row.shipmentNo} · ${row.recordedAt}\n货件号：${row.before.shipmentId || '空'} → ${row.after.shipmentId || '空'}\n预约号：${row.before.referenceId || '空'} → ${row.after.referenceId || '空'}\n港口：${row.before.originPort || '空'} / ${row.before.destinationPort || '空'} → ${row.after.originPort || '空'} / ${row.after.destinationPort || '空'}\n${row.after.force ? '强制覆盖 · ' : ''}${row.result.message || '已登记修改计划，最终保存及推送结果待确认'}`).join('\n\n')
  } catch { if (selected.value?.id === task.id) auditText.value = '操作明细加载失败，请重新打开重试' }
}
const filter = ref('all')
const visibleRows = computed(() => (selected.value?.rows || []).filter(row => filter.value === 'all' || (filter.value === 'mismatch' ? row.kind === 'mismatch' : row.kind !== 'mismatch')))
const mismatchNos = computed(() => [...new Set((selected.value?.rows || []).filter(row => row.kind === 'mismatch').map(row => row.shipmentNo).filter(no => no && no !== '—'))])
const issueNos = computed(() => [...new Set((selected.value?.rows || []).filter(row => row.kind !== 'mismatch').map(row => row.shipmentNo).filter(no => no && no !== '—'))])
const columns = computed<DataTableColumns<NonNullable<RunningTask['rows']>[number]>>(() => [
  { title:'运单号', key:'shipmentNo', width:180, ellipsis:{tooltip:true} },
  ...(selected.value?.resultKind === 'ctns' ? [
    {title:'运单件数', key:'shipmentCtns', width:90, render:(row: NonNullable<RunningTask['rows']>[number]) => row.shipmentCtns ?? '—'},
    {title:'产品箱数', key:'productCtns', width:90, render:(row: NonNullable<RunningTask['rows']>[number]) => row.productCtns ?? '—'},
    {title:'差额', key:'diff', width:70, render:(row: NonNullable<RunningTask['rows']>[number]) => row.diff == null ? '—' : row.diff > 0 ? `+${row.diff}` : row.diff},
  ] : []),
  { title:'原因', key:'message', minWidth:180, ellipsis:{tooltip:true}, render:row => row.message || (row.kind === 'mismatch' ? '件数不一致' : '查询异常') },
])
async function copyNos(nos: string[]) { try { await navigator.clipboard.writeText(nos.join('\n')); message.success(`已复制 ${nos.length} 个单号`) } catch { message.error('复制失败') } }
async function copy() { try { await navigator.clipboard.writeText([selected.value?.details || selected.value?.message || '', auditText.value].filter(Boolean).join('\n\n')); message.success('已复制结果') } catch { message.error('复制失败') } }
</script>
<template>
  <NPopover trigger="click" placement="bottom-end" :width="420" :style="{maxWidth: 'calc(100vw - 24px)'}" :show-arrow="false">
    <template #trigger><button type="button" class="header-ghost-btn relative" :aria-label="running.length ? `任务：${running.length} 项处理中` : '任务'" :title="running.length ? `${running.length} 项任务处理中，点击查看` : '任务，点击查看'">
      <ListTodo :size="18" aria-hidden="true" />
      <LoaderCircle v-if="running.length" :size="26" class="pointer-events-none absolute animate-spin opacity-50" aria-hidden="true" />
      <span v-if="running.length" class="absolute -right-1 -top-1 min-w-3.5 rounded-full bg-violet-600 px-1 text-center text-[10px] leading-3.5 text-white">{{ running.length }}</span>
      <span v-if="issue" class="absolute bottom-0 right-0 h-1.5 w-1.5 rounded-full bg-amber-500" />
    </button></template>
    <div class="task-center">
      <div class="task-center__head">
        <div><h2>任务中心</h2><p>{{ running.length ? `${running.length} 项任务进行中` : '当前没有运行中的任务' }}</p></div>
        <div class="task-center__actions">
          <NButton size="small" quaternary circle :loading="historyLoading" title="刷新历史" aria-label="刷新历史" @click="loadTaskHistory()"><template #icon><RefreshCw :size="15" /></template></NButton>
          <NButton size="small" quaternary circle :type="showHistory ? 'primary' : 'default'" :title="showHistory ? '返回最近任务' : '查看完整历史（含隐藏记录）'" aria-label="切换任务历史" @click="showHistory = !showHistory; showHistory && loadTaskHistory()"><template #icon><History :size="15" /></template></NButton>
          <NButton size="small" quaternary circle :disabled="showHistory || !completed.some(task => task.state !== 'running')" title="隐藏已完成（刷新后保持隐藏）" aria-label="隐藏已完成" @click="clearFinished"><template #icon><EyeOff :size="15" /></template></NButton>
        </div>
      </div>
      <div v-if="!groups.length" class="task-center__empty"><Inbox :size="30" :stroke-width="1.3" /><strong>{{ tasks.length ? '已完成记录已隐藏' : '暂无处理任务' }}</strong><span>点击右上方历史图标，可查看完整记录</span></div>
      <div v-else class="task-center__list">
        <section v-for="group in groups" :key="group.label" class="task-center__group">
          <div class="task-center__section-title">{{ group.label }}<span>{{ group.items.length }}</span></div>
          <div v-for="task in group.items" :key="task.id" class="task-card-shell">
          <button class="task-card" :class="`task-card--${stateOf(task)}`" @click="open(task)">
            <div class="task-card__top"><span class="task-card__source">{{ task.source || '处理任务' }}</span><span class="task-card__status"><LoaderCircle v-if="stateOf(task) === 'running'" :size="12" class="animate-spin" /><CircleCheck v-else-if="stateOf(task) === 'done'" :size="12" /><CircleAlert v-else :size="12" />{{ statusText(task) }}</span></div>
            <div class="task-card__title"><strong :title="taskName(task)">{{ taskName(task) }}</strong><ChevronRight :size="15" /></div>
            <div v-if="task.progress != null && stateOf(task) === 'running'" class="task-card__progress"><NProgress type="line" :percentage="Math.max(0, Math.min(100, Math.round(task.progress)))" :show-indicator="false" :height="4" /><span>{{ Math.round(task.progress) }}%</span></div>
            <p v-if="hasSummary(task)" class="task-card__summary" :title="task.message">{{ task.message }}</p>
            <p v-if="task.saveError" class="task-card__warning">记录未保存，点击重试</p>
            <div class="task-card__meta"><span><Clock3 :size="11" />{{ startedLabel(task) }}</span><span>{{ duration(task) }}</span></div>
          </button>
          <NPopconfirm v-if="showHistory && task.state !== 'running'" @positive-click="removeRecord(task)" positive-text="确认删除" negative-text="取消">
            <template #trigger><NButton class="task-card-delete" size="tiny" quaternary :loading="deletingId === task.id" :disabled="!!deletingId" title="永久删除此记录" aria-label="永久删除此记录"><template #icon><Trash2 :size="13" /></template></NButton></template>
            删除此任务记录及关联操作明细？不可恢复。不会删除下载文件，也不会撤销运单更新或推送。
          </NPopconfirm>
          </div>
        </section>
      </div>
      <p v-if="historyError" class="task-card__warning">{{ historyError }}</p>
      <div class="task-center__footer"><span>{{ showHistory ? '完整历史 · 可删除已结束记录' : '隐藏状态仅保存在当前浏览器' }}</span><div class="task-center__actions"><NButton v-if="historyMore" size="tiny" quaternary :loading="historyLoading" @click="loadTaskHistory(false)">更多历史</NButton><span class="task-center__info" tabindex="0" aria-label="任务记录说明" title="隐藏已完成会记住当前浏览器的隐藏状态；历史视图可真正删除已结束记录及关联操作明细。历史待确认任务需核对结果；刷新不会恢复前端任务执行。"><Info :size="14" /></span></div></div>
    </div>
  </NPopover>
  <NModal v-model:show="detailShow" preset="card" :title="selected?.title" :style="{width:'min(900px,95vw)'}">
    <p v-if="selected?.saveError" class="mb-3 text-amber-600">记录保存失败。<NButton size="tiny" @click="selected && persistTask(selected).then(() => { if (selected) selected.saveError = false }).catch(() => message.error('保存失败'))">重试保存</NButton></p>
    <p v-if="selected?.historical && selected.state === 'running'" class="mb-3 text-amber-600">这是未收到结束结果的历史记录，当前是否仍在执行需核对；请勿直接重复推送。</p>
    <div class="mb-5 flex flex-wrap items-center gap-2 text-xs text-[var(--color-muted)]">
      <NTag size="small" :bordered="false" :type="selected?.state === 'running' ? 'info' : selected?.state === 'failed' ? 'warning' : 'success'">{{ selected?.historical && selected.state === 'running' ? '结果待确认' : selected?.state === 'running' ? '正在处理' : selected?.state === 'failed' ? '已完成 · 需处理异常' : '已完成' }}</NTag>
      <span v-if="selected?.source">来源：{{ selected.source }}</span>
      <span v-if="selected">开始于 {{ new Date(selected.started).toLocaleString() }}</span>
    </div>
    <div v-if="selected?.stats?.length" class="task-stat-grid">
      <div v-for="stat in selected.stats" :key="stat.label" class="task-stat" :class="stat.tone ? `task-stat--${stat.tone}` : ''">
        <span class="text-xs text-[var(--color-muted)]">{{ stat.label }}</span><strong class="mt-1 block text-2xl font-semibold">{{ stat.value }}</strong>
      </div>
    </div>
    <p v-else class="mb-4 text-sm">{{ selected?.message }}</p>
    <NProgress v-if="selected?.state === 'running' && selected.progress != null" type="line" :percentage="Math.round(selected.progress)" class="my-3" />
    <div class="mb-3 mt-5 flex flex-wrap items-center justify-between gap-2">
      <div class="flex gap-1" v-if="selected?.resultKind === 'ctns'">
        <NButton size="small" :type="filter === 'all' ? 'primary' : 'default'" secondary @click="filter = 'all'">全部异常</NButton>
        <NButton size="small" :type="filter === 'mismatch' ? 'primary' : 'default'" secondary @click="filter = 'mismatch'">件数不一致</NButton>
        <NButton size="small" :type="filter === 'error' ? 'primary' : 'default'" secondary @click="filter = 'error'">查询异常</NButton>
      </div>
      <div class="flex flex-wrap gap-2">
        <NButton v-if="selected?.resultKind === 'ctns'" size="small" :disabled="!mismatchNos.length" @click="copyNos(mismatchNos)">复制不一致单号</NButton>
        <NButton v-if="selected?.resultKind === 'ctns'" size="small" :disabled="!issueNos.length" @click="copyNos(issueNos)">复制查询异常单号</NButton>
        <NButton size="small" @click="copy">复制完整结果</NButton>
      </div>
    </div>
    <template v-if="selected?.rows">
      <NDataTable size="small" :columns="columns" :data="visibleRows" :pagination="false" :max-height="360" :scroll-x="selected.resultKind === 'ctns' ? 720 : 400">
        <template #empty>{{ selected.state === 'running' ? '正在核对，请稍候…' : filter === 'all' ? '没有需要处理的异常' : filter === 'mismatch' ? '没有件数不一致的运单' : '没有查询异常的运单' }}</template>
      </NDataTable>
      <p v-if="selected.resultKind === 'ctns' && issueNos.length" class="mt-3 text-xs text-[var(--color-muted)]">查询异常（如没有产品）不代表件数不一致，请补齐产品数据或检查查询结果后重新核对。</p>
    </template>
    <div v-else class="task-text-result">{{ selected?.details || (selected?.state === 'running' ? '正在处理，结果会自动更新。' : selected?.message) }}</div>
    <details v-if="auditText" class="mt-4"><summary class="cursor-pointer text-sm">修改前后值与推送记录</summary><div class="task-text-result mt-2">{{ auditText }}</div></details>
  </NModal>
</template>

<style scoped>
 .task-center { color: var(--color-fg); width:100%; }
.task-center__head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:4px 2px 14px; border-bottom:1px solid var(--color-border); }
.task-center__head h2 { margin:0; font-size:15px; font-weight:650; color:var(--color-fg-emphasis); }
.task-center__head p { margin:4px 0 0; font-size:12px; color:var(--color-muted); }
.task-center__actions { display:flex; align-items:center; gap:4px; flex-shrink:0; }
.task-center__list { max-height:min(480px,65vh); overflow:auto; padding:0 2px 2px; }
.task-center__section-title { display:flex; gap:7px; align-items:center; padding:13px 2px 8px; font-size:11px; color:var(--color-muted); }
.task-center__section-title > span { min-width:17px; padding:0 4px; border-radius:5px; text-align:center; background:var(--color-btn-ghost-bg); font-variant-numeric:tabular-nums; }
.task-card-shell { position:relative; }
.task-card-shell:has(.task-card-delete) .task-card__meta { padding-right:24px; }
.task-card-delete { position:absolute; right:8px; bottom:8px; }
.task-card { display:block; width:100%; margin-bottom:8px; padding:12px; text-align:left; border:1px solid var(--color-border); border-radius:10px; background:var(--color-surface); transition:border-color .15s,background .15s; cursor:pointer; }
.task-card:hover { border-color:color-mix(in srgb,var(--color-accent) 40%,var(--color-border)); background:color-mix(in srgb,var(--color-accent) 4%,var(--color-surface)); }
.task-card:focus-visible { outline:2px solid var(--color-accent); outline-offset:1px; }
.task-card--running { border-color:color-mix(in srgb,var(--color-accent) 25%,var(--color-border)); }
.task-card__top,.task-card__title,.task-card__meta { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.task-card__source { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; font-size:11px; color:var(--color-muted); }
.task-card__status { display:inline-flex; flex-shrink:0; align-items:center; gap:4px; font-size:10px; line-height:18px; border-radius:5px; padding:0 5px; color:var(--color-muted); background:var(--color-btn-ghost-bg); }
.task-card--running .task-card__status { color:var(--color-accent); background:color-mix(in srgb,var(--color-accent) 10%,transparent); }
.task-card--done .task-card__status { color:#15803d; background:rgb(22 163 74 / .08); }
.task-card--failed .task-card__status,.task-card--unknown .task-card__status { color:#b45309; background:rgb(245 158 11 / .1); }
.task-card__title { margin-top:6px; color:var(--color-fg-emphasis); }
.task-card__title strong { min-width:0; font-size:13px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.task-card__title > svg { flex-shrink:0; color:var(--color-muted); }
.task-card__summary { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; margin:8px 0 0; font-size:12px; line-height:1.6; color:var(--color-fg-secondary); font-weight:400; }
.task-card__progress { display:flex; align-items:center; gap:8px; margin-top:10px; }
.task-card__progress > span { font-size:10px; color:var(--color-muted); font-variant-numeric:tabular-nums; }
.task-card__meta { margin-top:10px; padding-top:8px; border-top:1px solid var(--color-border); font-size:10px; color:var(--color-muted); font-weight:400; }
.task-card__meta > span:first-child { display:flex; align-items:center; gap:4px; }
.task-card__warning { margin:6px 0; color:#b45309; font-size:11px; }
.task-center__footer { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:10px 2px 0; margin-top:4px; border-top:1px solid var(--color-border); font-size:11px; color:var(--color-muted); }
.task-center__info { display:inline-flex; cursor:help; padding:4px; }
.task-center__empty { display:flex; flex-direction:column; align-items:center; gap:8px; padding:30px 12px; color:var(--color-muted); font-size:12px; }
.task-center__empty strong { font-weight:500; color:var(--color-fg-secondary); }
[data-theme='dark'] .task-card--done .task-card__status { color:#4ade80; }
[data-theme='dark'] .task-card--failed .task-card__status,[data-theme='dark'] .task-card--unknown .task-card__status,[data-theme='dark'] .task-card__warning { color:#fbbf24; }
@media (prefers-reduced-motion:reduce) { .task-card { transition:none; } .animate-spin { animation:none; } }
.task-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; }
.task-stat { padding: 14px 16px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-surface); }
.task-stat--success strong { color: #15803d; }
.task-stat--warning strong { color: #b45309; }
[data-theme='dark'] .task-stat--success strong { color: #4ade80; }
[data-theme='dark'] .task-stat--warning strong { color: #fbbf24; }
.task-text-result { max-height: 360px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; line-height: 1.8; padding: 16px; border-radius: 8px; border: 1px solid var(--color-border); }
</style>
