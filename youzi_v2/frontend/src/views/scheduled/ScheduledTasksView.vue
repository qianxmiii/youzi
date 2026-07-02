<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NDatePicker,
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
  runGroupAutoArchive,
  runScheduledCarrierSync,
  runScheduledInternalSync,
  runZipcodeBackfill,
  runExceptionFollowup,
  runDpsShipmentSync,
  updateScheduledTasksSettings,
} from '@/api/scheduledTasks'
import type {
  ScheduledSyncSettingsUpdate,
  ScheduledTaskOverview,
  TrackingSyncJobRecord,
} from '@/types/scheduledTasks'
import {
  dateOnlyToTimestamp,
  formatDateEndOfDayForApi,
  formatDateOnlyForApi,
} from '@/utils/formatDateTime'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const runningInternal = ref(false)
const runningCarrier = ref(false)
const runningGroupArchive = ref(false)
const runningZipcodeBackfill = ref(false)
const runningExceptionFollowup = ref(false)
const runningDpsShipmentSync = ref(false)
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
  groupAutoArchiveEnabled: false,
  zipcodeBackfillEnabled: false,
  dpsShipmentSyncEnabled: false,
  dpsShipmentSyncTransitTimeStart: '',
  dpsShipmentSyncTransitTimeEnd: '',
  exceptionFollowupEnabled: false,
})

/** DPS 发运时间范围（日期控件，提交时转为 API 时间串） */
const dpsTransitTimeStartTs = ref<number | null>(null)
const dpsTransitTimeEndTs = ref<number | null>(null)

function dpsTransitTimeStartForApi(): string | null {
  if (dpsTransitTimeStartTs.value == null) return null
  return formatDateOnlyForApi(dpsTransitTimeStartTs.value)
}

function dpsTransitTimeEndForApi(): string | null {
  if (dpsTransitTimeEndTs.value == null) return null
  return formatDateEndOfDayForApi(dpsTransitTimeEndTs.value)
}

function applyDpsTransitTimePickers(c: ScheduledTaskOverview['config']) {
  dpsTransitTimeStartTs.value = dateOnlyToTimestamp(
    c.dpsShipmentSyncTransitTimeStart || c.dpsShipmentSyncTransitTimeStartDefault,
  )
  dpsTransitTimeEndTs.value = dateOnlyToTimestamp(
    c.dpsShipmentSyncTransitTimeEnd || c.dpsShipmentSyncTransitTimeEndDefault,
  )
}

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
  form.groupAutoArchiveEnabled = c.groupAutoArchiveEnabled ?? false
  form.zipcodeBackfillEnabled = c.zipcodeBackfillEnabled ?? false
  form.dpsShipmentSyncEnabled = c.dpsShipmentSyncEnabled ?? false
  form.dpsShipmentSyncTransitTimeStart = c.dpsShipmentSyncTransitTimeStart ?? ''
  form.dpsShipmentSyncTransitTimeEnd = c.dpsShipmentSyncTransitTimeEnd ?? ''
  form.exceptionFollowupEnabled = c.exceptionFollowupEnabled ?? false
  applyDpsTransitTimePickers(c)
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
    await updateScheduledTasksSettings({
      ...form,
      dpsShipmentSyncTransitTimeStart: dpsTransitTimeStartForApi(),
      dpsShipmentSyncTransitTimeEnd: dpsTransitTimeEndForApi(),
    })
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

async function onRunGroupArchive() {
  runningGroupArchive.value = true
  try {
    const res = await runGroupAutoArchive()
    if (res.skipped) {
      message.warning(res.reason || '已跳过')
    } else if (res.archived > 0) {
      message.success(`已自动归档 ${res.archived} 个分组（候选 ${res.total} 个）`)
    } else {
      message.info('暂无符合自动归档条件的分组')
    }
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    runningGroupArchive.value = false
  }
}

async function onRunZipcodeBackfill() {
  runningZipcodeBackfill.value = true
  try {
    const res = await runZipcodeBackfill()
    if (res.skipped) {
      message.warning(res.reason || '已跳过')
    } else if (res.updated > 0) {
      message.success(`已回写 ${res.updated} 单邮编（候选 ${res.total} 单，未匹配 ${res.unmatched}）`)
    } else if (res.total > 0) {
      message.info(`共 ${res.total} 单缺邮编，地址库未匹配到可回写数据`)
    } else {
      message.info('暂无需要回写邮编的运单')
    }
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    runningZipcodeBackfill.value = false
  }
}

async function onRunExceptionFollowup() {
  runningExceptionFollowup.value = true
  try {
    const res = await runExceptionFollowup()
    if (res.skipped) {
      message.warning(res.reason || '已跳过')
    } else if (res.created > 0) {
      message.success(`已生成 ${res.created} 条异常跟进待办（扫描 ${res.scanned} 单）`)
    } else {
      message.info(`已扫描 ${res.scanned} 单，暂无到期需跟进的异常`)
    }
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    runningExceptionFollowup.value = false
  }
}

async function onRunDpsShipmentSync() {
  runningDpsShipmentSync.value = true
  try {
    const res = await runDpsShipmentSync({
      transitTimeStart: dpsTransitTimeStartForApi(),
      transitTimeEnd: dpsTransitTimeEndForApi(),
    })
    if (res.skipped) {
      message.warning(res.reason || '已跳过')
    } else if (res.error) {
      message.error(res.error)
    } else {
      message.success(
        `DPS 同步完成：新增 ${res.created}、更新 ${res.updated}（远程 ${res.remoteTotal ?? res.total} 单）`,
      )
    }
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '执行失败')
  } finally {
    runningDpsShipmentSync.value = false
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
    {
      label: '分组 · 上次自动归档',
      value: c.groupAutoArchiveLastFinished || '尚无',
      hint: c.groupAutoArchiveEnabled ? '每日批处理已启用' : '自动归档默认关闭',
    },
    {
      label: '邮编 · 上次回写',
      value: c.zipcodeBackfillLastFinished || '尚无',
      hint: c.zipcodeBackfillEnabled ? '每日批处理已启用' : '邮编回写默认关闭',
    },
    {
      label: 'DPS · 上次运单同步',
      value: c.dpsShipmentSyncLastFinished || '尚无',
      hint: c.dpsShipmentSyncEnabled
        ? `已启用 · ${c.dpsShipmentSyncTransitTimeStartEffective ?? ''} ~ ${c.dpsShipmentSyncTransitTimeEndEffective ?? ''}`
        : 'DPS 运单同步默认关闭',
    },
    {
      label: '异常 · 上次跟进扫描',
      value: c.exceptionFollowupLastFinished || '尚无',
      hint: c.exceptionFollowupEnabled ? '每日批处理已启用' : '异常跟进默认关闭',
    },
  ]
})

onMounted(load)
</script>

<template>
  <div class="scrollbar-subtle flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="page-h2">计划任务</h2>
        <p class="mt-1 text-xs text-[var(--color-muted)]">
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
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <article v-for="card in statusCards" :key="card.label" class="panel p-4">
            <p class="text-xs text-[var(--color-muted)]">{{ card.label }}</p>
            <p class="mt-1 text-sm font-medium text-[var(--color-fg-emphasis)]">{{ card.value }}</p>
            <p class="mt-1 text-[10px] leading-relaxed text-[var(--color-fg-secondary)]">{{ card.hint }}</p>
          </article>
        </div>

        <section class="panel p-4">
          <h3 class="mb-4 text-sm font-medium text-[var(--color-fg-emphasis)]">定时配置</h3>
          <NForm label-placement="left" label-width="120" size="small">
            <NFormItem label="内部轨迹">
              <NSpace align="center">
                <NSwitch v-model:value="form.internalEnabled" />
                <span class="text-xs text-[var(--color-muted)]">启用定时</span>
                <span class="text-xs text-[var(--color-fg-secondary)]">间隔（小时）</span>
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
                <span class="text-xs text-[var(--color-muted)]">启用定时</span>
                <span class="text-xs text-[var(--color-fg-secondary)]">间隔（小时）</span>
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
            <NFormItem label="分组自动归档">
              <NSpace align="center">
                <NSwitch v-model:value="form.groupAutoArchiveEnabled" />
                <span class="text-xs text-[var(--color-muted)]">每日批处理（约 24 小时）</span>
                <NButton size="tiny" :loading="runningGroupArchive" @click="onRunGroupArchive">
                  立即执行
                </NButton>
              </NSpace>
            </NFormItem>
            <NFormItem label="邮编回写">
              <NSpace align="center">
                <NSwitch v-model:value="form.zipcodeBackfillEnabled" />
                <span class="text-xs text-[var(--color-muted)]">每日批处理（约 24 小时）</span>
                <NButton size="tiny" :loading="runningZipcodeBackfill" @click="onRunZipcodeBackfill">
                  立即执行
                </NButton>
              </NSpace>
            </NFormItem>
            <NFormItem label="异常跟进提醒">
              <NSpace align="center">
                <NSwitch v-model:value="form.exceptionFollowupEnabled" />
                <span class="text-xs text-[var(--color-muted)]">每日批处理（约 24 小时，默认关闭）</span>
                <NButton size="tiny" :loading="runningExceptionFollowup" @click="onRunExceptionFollowup">
                  立即执行
                </NButton>
              </NSpace>
            </NFormItem>
            <NFormItem label="DPS 运单同步">
              <NSpace vertical :size="8" class="w-full max-w-3xl">
                <NSpace align="center">
                  <NSwitch v-model:value="form.dpsShipmentSyncEnabled" />
                  <span class="text-xs text-[var(--color-muted)]">每日批处理（约 24 小时，默认关闭）</span>
                  <NButton size="tiny" :loading="runningDpsShipmentSync" @click="onRunDpsShipmentSync">
                    立即执行
                  </NButton>
                </NSpace>
                <NSpace align="center" wrap>
                  <span class="text-xs text-[var(--color-fg-secondary)]">发运开始</span>
                  <NDatePicker
                    v-model:value="dpsTransitTimeStartTs"
                    type="date"
                    size="small"
                    clearable
                    class="w-40"
                    placeholder="默认当月首日"
                  />
                  <span class="text-xs text-[var(--color-fg-secondary)]">发运结束</span>
                  <NDatePicker
                    v-model:value="dpsTransitTimeEndTs"
                    type="date"
                    size="small"
                    clearable
                    class="w-40"
                    placeholder="默认当月末日"
                  />
                  <span class="text-[10px] text-[var(--color-muted)]">
                    开始 00:00:00 · 结束 23:59:59
                  </span>
                </NSpace>
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
                <span class="text-xs text-[var(--color-muted)]">秒（仅后端进程启动后首次检查）</span>
              </NSpace>
            </NFormItem>
          </NForm>
        </section>

        <section class="panel p-4">
          <h3 class="mb-3 text-sm font-medium text-[var(--color-fg-emphasis)]">任务说明</h3>
          <div class="space-y-3">
            <article
              v-for="task in overview.tasks"
              :key="task.id"
              class="rounded-lg border border-[var(--color-border)] bg-[var(--color-btn-ghost-bg)] px-4 py-3"
            >
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-[var(--color-fg-emphasis)]">{{ task.name }}</span>
                <NTag size="small" :bordered="false" type="info">{{ task.schedule }}</NTag>
              </div>
              <p class="mt-2 text-xs leading-relaxed text-[var(--color-fg-secondary)]">{{ task.description }}</p>
            </article>
          </div>
          <p
            v-if="overview.config.scriptPath"
            class="mt-3 font-mono text-[10px] text-[var(--color-fg-secondary)] break-all"
          >
            外部计划任务脚本：{{ overview.config.scriptPath }}
          </p>
        </section>

        <section class="panel flex min-h-0 flex-col p-4">
          <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 class="text-sm font-medium text-[var(--color-fg-emphasis)]">执行记录</h3>
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
