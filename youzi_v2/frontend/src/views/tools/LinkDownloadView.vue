<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { NInput, NButton, NProgress, NPopover, useMessage } from 'naive-ui'
import { api } from '@/api/client'
import { loadTaskHistory } from '@/composables/useRunningTasks'
import { parseLinkText, checkLinkRow, type LinkRow, type LinkRule, defaultLinkRules } from '@/utils/linkDownload'
type Job = { id:string; created:number; status:string; expired?:boolean; rows:(LinkRow & {status:string; message:string; filename?:string})[] }
const route = useRoute()
const message = useMessage()
const rules = ref<LinkRule[]>(defaultLinkRules)
const text = ref('')
const rows = ref<LinkRow[]>([{shipmentNo:'',url:''}])
const dirty = ref(false)
const pending = ref(false)
const submitting = ref(false)
const job = ref<Job | null>(null)
const history = ref<Job[]>([])
const error = ref('')
const checking = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let alive = true
const rowErrors = computed(() => rows.value.map(row => checkLinkRow(row,rows.value,rules.value)))
const valid = computed(() => rows.value.filter((_,i) => !rowErrors.value[i]))
const done = computed(() => job.value?.rows.filter(r => ['success','failed'].includes(r.status)).length || 0)
const success = computed(() => job.value?.rows.filter(r => r.status === 'success').length || 0)
const failures = computed(() => job.value?.rows.filter(r => r.status === 'failed') || [])
watch(text, value => {
  if (dirty.value) { pending.value = true; return }
  rows.value = parseLinkText(value)
})
function applyPaste(append: boolean) {
  const parsed = parseLinkText(text.value)
  rows.value = append ? [...rows.value.filter(r => r.shipmentNo || r.url), ...parsed] : parsed
  pending.value = false
  dirty.value = true
}
function viewUrl(row:LinkRow) {
  if (checkLinkRow(row,[row],rules.value)) return undefined
  const url = new URL(row.url.replace(/\\:/g, ':'))
  const rule = rules.value.find(r => url.hostname === r.host && url.port === String(r.port) && r.paths.includes(url.pathname))
  url.pathname = rule?.paths[0] || url.pathname
  return url.toString()
}
async function histories() {
  const data = await api<{items:Job[]}>('/api/v1/tools/link-download/jobs')
  history.value = data.items
}
async function openJob(id:string) {
  if (checking.value) return
  checking.value = true
  try { job.value = await api<Job>(`/api/v1/tools/link-download/jobs/${encodeURIComponent(id)}`); error.value = '' }
  catch { error.value = '任务读取失败，请刷新重试' }
  finally { checking.value = false }
}
async function start(retry = false) {
  if (submitting.value) return
  submitting.value = true
  try {
    if (!retry && (rows.value.length > 100 || !valid.value.length)) return
    job.value = retry && job.value ? await api<Job>(`/api/v1/tools/link-download/jobs/${job.value.id}/retry`, {method:'POST',retry:0}) : await api<Job>('/api/v1/tools/link-download/jobs',{method:'POST',body:{rows:valid.value},retry:0})
    error.value = ''
    message.success('后端任务已创建，可切换页面或刷新后查看')
    await histories()
    await loadTaskHistory()
  } catch (e) { message.error((e as {data?:{detail?:string}})?.data?.detail || '创建失败，请先查看历史，确认是否已创建') }
  finally { submitting.value = false }
}
async function copyFailures() {
  try { await navigator.clipboard.writeText(failures.value.map(r => r.shipmentNo).join('\n')); message.success('已复制失败单号') }
  catch { message.error('复制失败') }
}
async function download(index?:number) {
  if (!job.value) return
  try {
    const blob = await api<Blob, 'blob'>(`/api/v1/tools/link-download/jobs/${job.value.id}/download`,{query:index == null ? {} : {index},responseType:'blob',timeout:600000})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = index == null ? `照片下载_${job.value.id.slice(0,8)}.zip` : `${job.value.rows[index]?.shipmentNo}.zip`; a.click()
    setTimeout(() => URL.revokeObjectURL(url),60000)
  } catch { message.error('文件不可下载或已过期，请刷新任务后查看') }
}
watch(() => route.query.job, id => { if (typeof id === 'string') void openJob(id) })
async function poll() {
  try { if (job.value?.status === 'running') await openJob(job.value.id); await histories(); await loadTaskHistory() }
  catch { error.value = '任务列表加载失败，请稍后重试' }
  if (alive) timer = setTimeout(poll,2500)
}
onMounted(async () => {
  try { rules.value = (await api<{items:LinkRule[]}>('/api/v1/tools/link-download/rules')).items; await histories(); const id = typeof route.query.job === 'string' ? route.query.job : history.value[0]?.id; if (id) await openJob(id) }
  catch { error.value = '历史加载失败，请刷新重试' }
  void poll()
})
onUnmounted(() => { alive = false; if (timer) clearTimeout(timer) })
</script>
<template>
  <div class="flex min-h-0 flex-col gap-4 overflow-auto pb-6">
    <div><h1 class="page-h2">链接批量下载</h1><p class="page-subtitle mt-1">粘贴运单号与提货照片链接，或直接填写列表。下载后按运单号命名，不修改运单数据。</p></div>
    <section class="panel p-4">
      <NInput v-model:value="text" type="textarea" :autosize="{minRows:3,maxRows:7}" placeholder="每行：运单号 = 查看链接（支持空格分隔）" />
      <div v-if="pending" class="mt-2 flex flex-wrap items-center gap-2 text-sm"><span>列表已手工修改，粘贴内容不会自动覆盖。</span><NButton size="small" @click="applyPaste(true)">追加到列表</NButton><NButton size="small" @click="applyPaste(false)">替换列表</NButton></div>
      <div class="my-3 flex flex-wrap items-center justify-between gap-2"><strong class="text-sm">待下载列表 · {{ valid.length }} 票有效 / {{ rows.length }} 行</strong><NButton size="small" :disabled="rows.length >= 100" @click="rows.push({shipmentNo:'',url:''}); dirty = true">添加一行</NButton></div>
      <div class="max-h-80 overflow-auto"><table class="link-table"><colgroup><col style="width:190px"><col><col style="width:200px"><col style="width:110px"></colgroup><thead><tr><th>运单号</th><th>查看链接</th><th>校验 / 下载规则</th><th>操作</th></tr></thead><tbody>
        <tr v-for="(row,index) in rows" :key="index"><td><NInput v-model:value="row.shipmentNo" size="small" placeholder="运单号" @update:value="dirty = true" /></td><td><NInput v-model:value="row.url" size="small" placeholder="粘贴查看链接" @update:value="dirty = true" /></td><td :class="rowErrors[index] ? 'text-amber-600' : 'text-green-600'">{{ rowErrors[index] || '可下载' }}</td><td><a v-if="viewUrl(row)" :href="viewUrl(row)" target="_blank" rel="noopener noreferrer" class="text-[var(--color-accent)] mr-2">查看</a><button class="text-[var(--color-muted)]" @click="rows.splice(index,1); dirty = true">删除</button></td></tr>
      </tbody></table></div>
      <div class="mt-4 flex flex-wrap items-center gap-3"><NButton type="primary" :loading="submitting" :disabled="!valid.length || rows.length > 100 || submitting" @click="start()">开始下载 {{ valid.length }} 票</NButton><span class="text-xs text-[var(--color-muted)]">仅提交有效行；每批最多 100 票，文件 7 天内可下载。无效行不会提交。</span></div>
    </section>
    <p v-if="error" class="text-sm text-amber-600">{{ error }}</p>
    <section v-if="job" class="panel p-4">
      <div class="flex flex-wrap justify-between gap-3"><h2 class="font-semibold">{{ job.status === 'running' ? '下载中' : '下载结果' }} · {{ new Date(job.created*1000).toLocaleString() }}</h2><NButton size="small" :loading="checking" @click="openJob(job.id)">刷新</NButton></div>
      <p class="my-2 text-sm">已处理 {{ done }}/{{ job.rows.length }} · 成功 {{ success }} · 失败 {{ failures.length }}<span v-if="job.expired" class="text-amber-600"> · 文件已过期，需重新下载</span></p>
      <NProgress type="line" :percentage="Math.round(done/job.rows.length*100)" :show-indicator="false" />
      <div class="my-3 flex flex-wrap gap-2"><NButton :disabled="job.status === 'running' || !success || job.expired" @click="download()">下载成功项汇总包</NButton><NButton :disabled="job.status === 'running' || !failures.length || submitting" @click="start(true)">仅重试失败项</NButton><NButton :disabled="!failures.length" @click="copyFailures">复制失败单号</NButton><NButton v-if="job.expired" @click="rows = job.rows.map(r => ({shipmentNo:r.shipmentNo,url:r.url})); dirty = true">填回列表重新下载</NButton></div>
      <div class="max-h-96 overflow-auto"><table class="link-table"><colgroup><col style="width:190px"><col style="width:100px"><col><col style="width:90px"></colgroup><thead><tr><th>运单号</th><th>状态</th><th>说明</th><th>文件</th></tr></thead><tbody><tr v-for="(row,index) in job.rows" :key="row.shipmentNo"><td class="whitespace-nowrap font-mono">{{ row.shipmentNo }}</td><td :class="row.status === 'success' ? 'text-green-600' : row.status === 'failed' ? 'text-amber-600' : ''">{{ row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : '等待 / 下载中' }}</td><td><NPopover trigger="hover"><template #trigger><div class="truncate">{{ row.message }}</div></template><div class="max-w-sm break-words">{{ row.message }}</div></NPopover></td><td><NButton size="tiny" :disabled="row.status !== 'success' || job.expired" @click="download(index)">下载</NButton></td></tr></tbody></table></div>
    </section>
    <section class="panel p-4"><h2 class="font-semibold mb-2">最近任务</h2><p v-if="!history.length" class="text-sm text-[var(--color-muted)]">暂无下载记录</p><button v-for="item in history" :key="item.id" class="block w-full border-b border-[var(--color-border)] p-2 text-left text-sm" @click="openJob(item.id)">{{ new Date(item.created*1000).toLocaleString() }} · {{ item.rows.length }} 票 · {{ item.status === 'running' ? '运行中' : item.status === 'failed' ? '有异常' : '已完成' }}{{ item.expired ? ' · 文件已过期' : '' }}</button></section>
  </div>
</template>
<style scoped>
.link-table { width:100%; min-width:760px; table-layout:fixed; text-align:left; border-collapse:collapse; font-size:13px; }
.link-table td,.link-table th { padding:9px 8px; border-bottom:1px solid var(--color-border); }
.link-table th { position:sticky; top:0; background:var(--color-surface); z-index:1; color:var(--color-muted); font-weight:500; }
</style>
