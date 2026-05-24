<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NInputNumber,
  NPagination,
  NSelect,
  NSpace,
  NSpin,
  NSwitch,
  NTag,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  getScheduledTasksOverview,
  listScheduledTaskJobs,
  runScheduledCarrierSync,
  runScheduledInternalSync,
  updateScheduledTasksSettings,
} from '@/api/scheduledTasks'
import type {
  ScheduledSyncSettingsUpdate,
  ScheduledTaskOverview,
  TrackingSyncJobRecord,
} from '@/types/scheduledTasks'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const runningInternal = ref(false)
const runningCarrier = ref(false)
const overview = ref<ScheduledTaskOverview | null>(null)
const jobs = ref<TrackingSyncJobRecord[]>([])
const jobsTotal = ref(0)
const page = ref(1)
const pageSize = ref(20)
const jobSourceFilter = ref<string | null>(null)
const error = ref('')

const form = reactive<ScheduledSyncSettingsUpdate>({
  internalEnabled: true,
  internalIntervalHours: 2,
  carrierEnabled: true,
  carrierIntervalHours: 2,
  initialDelaySec: 60,
})

const SOURCE_LABEL: Record<string, string> = {
  carrier: '承运商轨迹',
  internal: '内部轨迹',
}

const TRIGGER_LABEL: Record<string, string> = {
  scheduled: '定时',
  manual: '手动',
}

const jobSourceOptions = [
  { label: '全部', value: '' },
  { label: '内部轨迹', value: 'internal' },
  { label: '承运商轨迹', value: 'carrier' },
]

function statusTagType(
  status: string,
): 'default' | 'info' | 'success' | 'warning' | 'error' {
  if (status === 'success') return 'success'
  if (status === 'partial') return 'warning'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'info'
  return 'default'
}

const columns: DataTableColumns<TrackingSyncJobRecord> = [
  { title: '开始时间', key: 'startedTime', width: 160, ellipsis: { tooltip: true } },
  { title: '结束时间', key: 'finishedTime', width: 160, ellipsis: { tooltip: true } },
  {
    title: '类型',
    key: 'source',
    width: 108,
    render: (row) => SOURCE_LABEL[row.source] || row.source,
  },
  {
    title: '触发',
    key: 'triggerType',
    width: 72,
    render: (row) => TRIGGER_LABEL[row.triggerType] || row.triggerType,
  },
  {
    title: '状态',
    key: 'status',
    width: 88,
    render: (row) =>
      h(NTag, { size: 'small', bordered: false, type: statusTagType(row.status) }, () => row.status),
  },
  { title: '运单数', key: 'totalShipments', width: 72, align: 'right' },
  { title: '更新', key: 'updatedShipments', width: 72, align: 'right' },
  { title: '新轨迹', key: 'newLogCount', width: 72, align: 'right' },
  { title: '失败', key: 'errorCount', width: 64, align: 'right' },
  {
    title: '错误摘要',
    key: 'errors',
    minWidth: 200,
    ellipsis: { tooltip: true },
    render: (row) => row.errors?.[0] || '—',
  },
]

function applyConfigFromOverview(data: ScheduledTaskOverview) {
  const c = data.config
  form.internalEnabled = c.internalEnabled
  form.internalIntervalHours = c.internalIntervalHours
  form.carrierEnabled = c.carrierEnabled
  form.carrierIntervalHours = c.carrierIntervalHours
  form.initialDelaySec = c.initialDelaySec
}

function syncResultMessage(res: { skipped?: boolean; reason?: string | null; internal?: unknown; carrier?: unknown }) {
  if (res.skipped) {
    return { type: 'warning' as const, text: res.reason || '已跳过' }
  }
  const payload = (res.internal || res.carrier) as Record<string, unknown> | undefined
  const inner = (payload?.internal || payload) as { updated?: number } | undefined
  const updated = inner?.updated ?? (payload as { updated?: number })?.updated ?? 0
  return { type: 'success' as const, text: `完成，更新 ${updated} 单` }
}

async function loadJobs() {
  const res = await listScheduledTaskJobs({
    source: jobSourceFilter.value || undefined,
    limit: pageSize.value,
    offset: (page.value - 1) * pageSize.value,
  })
  jobs.value = res.items
  jobsTotal.value = res.total
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    overview.value = await getScheduledTasksOverview()
    applyConfigFromOverview(overview.value)
    await loadJobs()
  } catch (e) {
    overview.value = null
    jobs.value = []
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function onSave() {
  saving.value = true
  try {
    await updateScheduledTasksSettings({ ...form })
    message.success('配置已保存，后台轮询将按新间隔执行（无需重启）')
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function onRunInternal() {
  runningInternal.value = true
  try {
    const res = await runScheduledInternalSync()
    const msg = syncResultMessage(res)
    if (msg.type === 'warning') message.warning(msg.text)
    else message.success(`内部轨迹：${msg.text}`)
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    runningInternal.value = false
  }
}

async function onRunCarrier() {
  runningCarrier.value = true
  try {
    const res = await runScheduledCarrierSync()
    const msg = syncResultMessage(res)
    if (msg.type === 'warning') message.warning(msg.text)
    else message.success(`承运商轨迹：${msg.text}`)
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    runningCarrier.value = false
  }
}

function onPageChange(p: number) {
  page.value = p
  void loadJobs()
}

function onJobSourceChange() {
  page.value = 1
  void loadJobs()
}

const statusCards = computed(() => {
  if (!overview.value) return []
  const c = overview.value.config
  const it = overview.value.internalToday
  const ct = overview.value.carrierToday
  return [
    {
      label: '调度总开关',
      value: c.schedulerActive ? '至少一项已启用' : '全部关闭',
      hint: `启动后 ${c.initialDelaySec}s 首次检查，每 ${c.pollIntervalSec ?? 60}s 轮询`,
    },
    {
      label: '内部 · 上次全库',
      value: c.lastInternalFinished || '尚无',
      hint: `今日 ${it.jobCount} 次 · 更新 ${it.updatedShipments} 单`,
    },
    {
      label: '承运商 · 上次全库',
      value: c.lastCarrierFinished || '尚无',
      hint: `今日 ${ct.jobCount} 次 · 更新 ${ct.updatedShipments} 单`,
    },
  ]
})

onMounted(load)
</script>

<template>
  <div class="scrollbar-subtle flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-white">计划任务</h2>
        <p class="mt-1 text-xs text-zinc-500">
          内部轨迹与承运商轨迹分开配置、分开触发；保存后立即生效（后台每 60 秒检查是否到期）。
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <NButton size="small" :loading="loading" @click="load">刷新</NButton>
        <NButton size="small" type="primary" :loading="saving" @click="onSave">保存配置</NButton>
      </div>
    </div>

    <NSpin :show="loading">
      <div v-if="error" class="panel px-4 py-6 text-sm text-red-400">{{ error }}</div>
      <template v-else-if="overview">
        <div class="grid gap-3 sm:grid-cols-3">
          <article v-for="card in statusCards" :key="card.label" class="panel p-4">
            <p class="text-xs text-zinc-500">{{ card.label }}</p>
            <p class="mt-1 text-sm font-medium text-zinc-100">{{ card.value }}</p>
            <p class="mt-1 text-[10px] leading-relaxed text-zinc-600">{{ card.hint }}</p>
          </article>
        </div>

        <section class="panel p-4">
          <h3 class="mb-4 text-sm font-medium text-white">定时配置</h3>
          <NForm label-placement="left" label-width="120" size="small">
            <NFormItem label="内部轨迹">
              <NSpace align="center">
                <NSwitch v-model:value="form.internalEnabled" />
                <span class="text-xs text-zinc-500">启用定时</span>
                <span class="text-xs text-zinc-600">间隔（小时）</span>
                <NInputNumber
                  v-model:value="form.internalIntervalHours"
                  :min="0.25"
                  :max="168"
                  :step="0.5"
                  :disabled="!form.internalEnabled"
                  class="w-28"
                />
                <NButton size="tiny" :loading="runningInternal" @click="onRunInternal">
                  立即执行
                </NButton>
              </NSpace>
            </NFormItem>
            <NFormItem label="承运商轨迹">
              <NSpace align="center">
                <NSwitch v-model:value="form.carrierEnabled" />
                <span class="text-xs text-zinc-500">启用定时</span>
                <span class="text-xs text-zinc-600">间隔（小时）</span>
                <NInputNumber
                  v-model:value="form.carrierIntervalHours"
                  :min="0.25"
                  :max="168"
                  :step="0.5"
                  :disabled="!form.carrierEnabled"
                  class="w-28"
                />
                <NButton size="tiny" :loading="runningCarrier" @click="onRunCarrier">
                  立即执行
                </NButton>
              </NSpace>
            </NFormItem>
            <NFormItem label="启动延迟">
              <NSpace align="center">
                <NInputNumber
                  v-model:value="form.initialDelaySec"
                  :min="0"
                  :max="86400"
                  :step="10"
                  class="w-28"
                />
                <span class="text-xs text-zinc-500">秒（仅后端进程启动后首次检查）</span>
              </NSpace>
            </NFormItem>
          </NForm>
        </section>

        <section class="panel p-4">
          <h3 class="mb-3 text-sm font-medium text-white">任务说明</h3>
          <div class="space-y-3">
            <article
              v-for="task in overview.tasks"
              :key="task.id"
              class="rounded-lg border border-[var(--color-border)] bg-zinc-900/40 px-4 py-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-zinc-100">{{ task.name }}</span>
                <NTag size="small" :bordered="false" type="info">{{ task.schedule }}</NTag>
              </div>
              <p class="mt-2 text-xs leading-relaxed text-zinc-400">{{ task.description }}</p>
            </article>
          </div>
          <p
            v-if="overview.config.scriptPath"
            class="mt-3 font-mono text-[10px] text-zinc-600 break-all"
          >
            外部计划任务脚本：{{ overview.config.scriptPath }}
          </p>
        </section>

        <section class="panel flex min-h-0 flex-col p-4">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 class="text-sm font-medium text-white">执行记录</h3>
            <NSelect
              v-model:value="jobSourceFilter"
              :options="jobSourceOptions"
              size="small"
              class="w-36"
              placeholder="类型"
              clearable
              @update:value="onJobSourceChange"
            />
          </div>
          <NDataTable
            :columns="columns"
            :data="jobs"
            :bordered="false"
            size="small"
            :scroll-x="960"
            class="min-h-[200px]"
          />
          <div class="mt-3 flex justify-end">
            <NPagination
              v-model:page="page"
              :page-size="pageSize"
              :item-count="jobsTotal"
              size="small"
              @update:page="onPageChange"
            />
          </div>
        </section>
      </template>
    </NSpin>
  </div>
</template>
