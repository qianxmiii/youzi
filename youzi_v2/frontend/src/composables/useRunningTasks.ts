import { reactive, ref, watch } from 'vue'
import { useStorage } from '@vueuse/core'
import router from '@/router'
import { api } from '@/api/client'
export type TaskStat = { label: string; value: number; tone?: 'success' | 'warning' }
export type TaskRow = { shipmentNo: string; message: string; kind?: string; shipmentCtns?: number | null; productCtns?: number | null; diff?: number | null }
export type RunningTask = { id: string; title: string; started: number; finished?: number; state: 'running' | 'done' | 'failed'; progress?: number; message: string; details: string; unseen: boolean; stats?: TaskStat[]; rows?: TaskRow[]; resultKind?: string; historical?: boolean; saveError?: boolean; managedBy?: 'server' | 'request'; href?: string; source?: string; sourcePath?: string }
const tasks = reactive<RunningTask[]>([])
const hiddenTaskIds = useStorage<string[]>('youzi.tasks.hiddenIds', [])
const deletedTaskIds = new Set<string>()
const historyError = ref('')
const historyLoading = ref(false)
const historyOffset = ref(0)
const historyMore = ref(true)
export function persistTask(task: RunningTask) {
  if (deletedTaskIds.has(task.id)) return Promise.resolve()
  if (task.managedBy === 'server' || task.managedBy === 'request') return Promise.resolve()
  const { historical, saveError, unseen, ...payload } = task
  return api(`/api/v1/task-history/${encodeURIComponent(task.id)}`, {method:'PUT',body:payload,retry:0})
}
export async function loadTaskHistory(reset = true) {
  if (historyLoading.value) return
  historyLoading.value = true
  historyError.value = ''
  if (reset) historyOffset.value = 0
  try {
    const result = await api<{items:RunningTask[]; activeRequestIds?:string[]}>('/api/v1/task-history', {query:{limit:50,offset:historyOffset.value}})
    for (const row of result.items) {
      if (deletedTaskIds.has(row.id)) continue
      const existing = tasks.find(task => task.id === row.id)
      const activeRequest = row.managedBy === 'request' && result.activeRequestIds?.includes(row.id)
      const historical = row.managedBy !== 'server' && !activeRequest
      if (existing?.managedBy === 'server' || existing?.managedBy === 'request' || (existing?.historical && row.managedBy === 'request')) {
        const justFinished = existing.state === 'running' && row.state !== 'running'
        Object.assign(existing,row,{historical,unseen:existing.unseen || justFinished})
      } else if (!existing) tasks.push({...row, historical, unseen:false})
    }
    historyOffset.value += result.items.length
    historyMore.value = result.items.length === 50
  } catch { historyError.value = '历史记录加载失败，请重试' }
  finally { historyLoading.value = false }
}
let serial = 0
export function startTask(title: string) {
  // 发起时保存来源，后续切换菜单不改变任务归属。
  const route = router.currentRoute.value
  const source = typeof route.meta.title === 'string' ? route.meta.title : ''
  const sourcePath = route.path
  const taskTitle = source && !title.startsWith(`${source} · `) ? `${source} · ${title.replace(/^运单 · /, '')}` : title
  const task: RunningTask = reactive({ id: `${crypto.randomUUID()}-${++serial}`, title: taskTitle, source, sourcePath, started: Date.now(), state: 'running', message: '处理中', details: '', unseen: false })
  tasks.unshift(task)
  let queue = Promise.resolve()
  let timer: ReturnType<typeof setTimeout> | undefined
  const save = () => {
    const snapshot = JSON.parse(JSON.stringify(task)) as RunningTask
    queue = queue.then(async () => {
      try { await persistTask(snapshot); task.saveError = false }
      catch { task.saveError = true }
    })
  }
  save()
  watch(() => [task.state, task.message, task.details, task.progress], () => {
    if (timer) clearTimeout(timer)
    if (task.state !== 'running') save()
    else timer = setTimeout(save, 500)
  }, {flush:'sync'})
  return task
}
export function finishTask(task: RunningTask, failed = false) {
  task.finished = Date.now()
  task.state = failed ? 'failed' : 'done'
  task.finished = Date.now()
  task.unseen = true
  if (!failed) task.progress = 100
}
export async function trackTask<T>(title: string, operation: (taskId: string) => Promise<T>): Promise<T> {
  const task = startTask(title)
  try {
    await persistTask(task)
    task.managedBy = 'request'
    const result = await operation(task.id)
    const data = result as Record<string, unknown>
    const labels: Record<string, string> = {checked:'已核对', matched:'件数一致', total:'总票数', updated:'已更新', skipped:'跳过', empty:'无轨迹', notFound:'未找到', logCount:'轨迹条数', created:'新增', unchanged:'无变化', failed:'失败', remoteTotal:'远端票数'}
    const counts = Object.entries(labels).filter(([key]) => typeof data[key] === 'number').map(([key, label]) => `${label} ${data[key]}`)
    const issues = Array.isArray(data.issues) ? data.issues as TaskRow[] : []
    const remarkRows = Array.isArray(data.remarkResults)
      ? (data.remarkResults as (TaskRow & { status: 'success' | 'failed' | 'unknown' })[]).map(row => ({
        shipmentNo: row.shipmentNo,
        message: `${{ success: '成功', failed: '失败', unknown: '待核对' }[row.status]} · ${row.message}`,
      }))
      : []
    const errors = Array.isArray(data.errors) ? data.errors.map(String) : []
    if (typeof data.error === 'string' && data.error.trim()) errors.push(data.error)
    if (data.skipped === true) errors.push(typeof data.reason === 'string' ? data.reason : '任务已跳过，未执行')
    const steps = Array.isArray(data.steps) ? data.steps as {label:string; skipped?:boolean; reason?:string; error?:string; created?:number; updated?:number; failed?:number}[] : []
    const stepDetails = steps.map(step => `${step.label}：${step.skipped ? step.reason || '已跳过' : step.error || `新增 ${step.created || 0} · 更新 ${step.updated || 0} · 失败 ${step.failed || 0}`}`)
    for (const step of steps) if (step.error || step.skipped) errors.push(`${step.label}：${step.error || step.reason || '已跳过'}`)
    task.stats = Object.entries(labels).filter(([key]) => typeof data[key] === 'number').map(([key, label]) => ({ label, value: data[key] as number, tone: key === 'matched' || key === 'updated' ? 'success' : undefined }))
    if (Array.isArray(data.issues)) {
      task.resultKind = 'ctns'
      task.rows = issues.map(row => ({ ...row }))
      task.stats.push({label:'件数不一致', value:issues.filter(row => row.kind === 'mismatch').length, tone:'warning'}, {label:'查询异常', value:issues.filter(row => row.kind !== 'mismatch').length, tone:'warning'})
    } else if (remarkRows.length) {
      task.rows = remarkRows
      task.stats.push({ label: '待核对', value: Number(data.unknown || 0), tone: 'warning' })
      counts.push(`待核对 ${Number(data.unknown || 0)}`)
    } else if (errors.length) {
      task.rows = errors.map(message => ({shipmentNo:'—',message}))
    }
    if (steps.length) {
      for (const key of ['created','updated','failed'] as const) task.stats.push({label:labels[key]!,value:steps.reduce((sum,step) => sum + (step[key] || 0),0)})
    }
    task.message = counts.join(' · ') || (steps.length ? task.stats.map(stat => `${stat.label} ${stat.value}`).join(' · ') : '处理完成')
    if (issues.length) task.message += ` · 需核对 ${issues.length}`
    if (errors.length) task.message += ` · 错误 ${errors.length}`
    task.details = [task.message, ...stepDetails, ...issues.map(row => `${row.shipmentNo}：${row.message || (row.kind === 'mismatch' ? `件数不一致，差额 ${row.diff}` : '查询失败')}`), ...errors].join('\n')
    finishTask(task, issues.length > 0 || errors.length > 0 || Number(data.failed || 0) > 0 || Number(data.unknown || 0) > 0 || steps.some(step => (step.failed || 0) > 0))
    return result
  } catch (error) {
    task.message = error instanceof Error ? error.message : '处理失败'
    finishTask(task, true)
    throw error
  } finally {
    void loadTaskHistory()
  }
}
export async function deleteTaskHistory(task: RunningTask) {
  await api(`/api/v1/task-history/${encodeURIComponent(task.id)}`,{method:'DELETE',retry:0})
  deletedTaskIds.add(task.id)
  const index = tasks.findIndex(row => row.id === task.id)
  if (index >= 0) tasks.splice(index,1)
  hiddenTaskIds.value = hiddenTaskIds.value.filter(id => id !== task.id)
}
export function useRunningTasks() {
  return { tasks, hiddenTaskIds, historyError, historyLoading, historyMore,
    clearFinished: () => { hiddenTaskIds.value = [...new Set([...hiddenTaskIds.value, ...tasks.filter(t => t.state !== 'running').map(t => t.id)])] },
  }
}
