<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDataTable,
  NInput,
  NPagination,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NTag,
  NTooltip,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { Copy, CircleHelp, ScanBarcode } from 'lucide-vue-next'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ExceptionStatusBadge from '@/components/common/ExceptionStatusBadge.vue'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import { getShipment, getShipmentFilterOptions, type ShipmentFilterOptions } from '@/api/shipments'
import {
  followUpShipmentSlaAlert,
  batchFollowUpShipmentSlaAlerts,
  batchResolveShipmentSlaAlerts,
  ignoreShipmentSlaAlert,
  convertShipmentSlaAlert,
  evaluateShipmentSlaAlerts,
  listShipmentSlaAlerts,
  getShipmentSlaSummary,
  resolveShipmentSlaAlert,
  slaRelatedAlertIds,
  type ShipmentSlaAlert,
  type SlaAlertStatus,
  type SlaRiskLevel,
} from '@/api/shipmentSla'
import type { Shipment } from '@/types/shipment'
import { formatAbsoluteDateTime, formatRelativeTime } from '@/utils/formatDateTime'
import { buildChannelSelectOptions } from '@/utils/channelFilterOptions'
import { ICON_STROKE } from '@/constants/icons'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'
import { usePendingShipmentSlaAlertCount } from '@/composables/usePendingShipmentSlaAlertCount'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const { refreshPendingShipmentSlaAlertCount } = usePendingShipmentSlaAlertCount()

const loading = ref(false)
const scanning = ref(false)
const batchSubmitting = ref(false)
const items = ref<ShipmentSlaAlert[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const checkedRowKeys = ref<string[]>([])
const pendingOpenCount = ref(0)
const severeOverdueCount = ref(0)
const overdueCount = ref(0)
const warningSoonCount = ref(0)

const filterTimelinessStatus = ref<string | null>(null)
const filterStatus = ref<string | null>(null)
const filterHasException = ref<string | null>(null)
const filterExceptionCode = ref<string | null>(null)
const filterChannelCode = ref<string | null>(null)
const filterShowHistory = ref(false)
const search = ref('')
const trackingDrawerShow = ref(false)
const trackingDrawerShipment = ref<Shipment | null>(null)
const trackingDrawerTab = ref<'internal' | 'carrier'>('internal')
const exceptionLabelByCode = ref<Record<string, string>>({})
const filterOptions = ref<ShipmentFilterOptions>({
  customers: [],
  carriers: [],
  carrierCodes: [],
  channels: [],
  countryCodes: [],
  channelCodes: [],
  channelNameZhs: [],
  channelCategories: [],
  statusCodes: [],
  exceptionCodes: [],
  exceptionTypes: [],
  groups: [],
})

const timelinessStatusOptions = [
  { label: '即将超时', value: 'warning_soon' },
  { label: '已超时', value: 'overdue' },
  { label: '严重超时', value: 'severe_overdue' },
  { label: '入库未开船', value: 'WAREHOUSE_NO_DEPARTURE' },
  { label: '到港未送仓', value: 'ARRIVAL_NO_DELIVERY' },
]

const STAGE_ALERT_TYPES = new Set(['WAREHOUSE_NO_DEPARTURE', 'ARRIVAL_NO_DELIVERY'])

function timelinessListParams(status: string | null) {
  if (!status) return {}
  if (STAGE_ALERT_TYPES.has(status)) return { alertType: status }
  return { riskLevel: status }
}

const statusOptions = [
  { label: '待处理', value: 'open' },
  { label: '已跟进', value: 'acknowledged' },
  { label: '已转异常', value: 'converted' },
  { label: '已解决', value: 'resolved' },
  { label: '已忽略', value: 'ignored' },
]

const hasExceptionOptions = [
  { label: '有异常', value: 'true' },
  { label: '无异常', value: 'false' },
]

const exceptionFilterOptions = computed(() =>
  Object.entries(exceptionLabelByCode.value).map(([code, nameZh]) => ({
    label: nameZh,
    value: code,
  })),
)

const channelCodeOptions = computed(() =>
  buildChannelSelectOptions(filterOptions.value.channels, filterOptions.value.channelCodes),
)

const selectedRows = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)),
)

const selectedCount = computed(() => selectedRows.value.length)

const selectedShipmentNos = computed(() => selectedRows.value.map((row) => row.shipmentNo))

const actionableSelectedRows = computed(() =>
  selectedRows.value.filter((row) => ['open', 'acknowledged'].includes(row.status)),
)

function rowKey(row: ShipmentSlaAlert) {
  return row.id
}

function syncSelectionWithItems() {
  const visible = new Set(items.value.map((row) => row.id))
  checkedRowKeys.value = checkedRowKeys.value.filter((id) => visible.has(id))
}

function clearSelection() {
  checkedRowKeys.value = []
}

async function copySelectedShipmentNos() {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选记录')
    return
  }
  try {
    await navigator.clipboard.writeText(nos.join('\n'))
    message.success(`已复制 ${nos.length} 个运单号`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

async function runBatchAction(
  label: string,
  rows: ShipmentSlaAlert[],
  action: (row: ShipmentSlaAlert) => Promise<void>,
) {
  if (!rows.length) {
    message.warning(`所选记录均不可${label}`)
    return
  }
  batchSubmitting.value = true
  try {
    const results = await Promise.allSettled(rows.map((row) => action(row)))
    const ok = results.filter((r) => r.status === 'fulfilled').length
    const fail = results.length - ok
    if (fail) message.warning(`${label}成功 ${ok} 条，失败 ${fail} 条`)
    else message.success(`已${label} ${ok} 条`)
    clearSelection()
    await Promise.all([load(), loadSummary()])
  } catch (e) {
    message.error(e instanceof Error ? e.message : `${label}失败`)
  } finally {
    batchSubmitting.value = false
  }
}

function handleBatchFollowUp() {
  void runBatchAction('跟进', actionableSelectedRows.value, async (row) => {
    const ids = slaRelatedAlertIds(row)
    if (ids.length > 1) {
      const res = await batchFollowUpShipmentSlaAlerts(ids)
      if (res.failed?.length) throw new Error(res.failed[0]?.message || '部分跟进失败')
      return
    }
    await followUpShipmentSlaAlert(row.id)
  })
}

function handleBatchResolve() {
  void runBatchAction('解决', actionableSelectedRows.value, async (row) => {
    const ids = slaRelatedAlertIds(row)
    if (ids.length > 1) {
      const res = await batchResolveShipmentSlaAlerts(ids)
      if (res.failed?.length) throw new Error(res.failed[0]?.message || '部分解决失败')
      return
    }
    await resolveShipmentSlaAlert(row.id)
  })
}

function handleBatchIgnore() {
  void runBatchAction('忽略', actionableSelectedRows.value, (row) => ignoreShipmentSlaAlert(row.id))
}

function riskTagType(level: SlaRiskLevel): 'default' | 'info' | 'warning' | 'error' {
  if (level === 'severe_overdue') return 'error'
  if (level === 'overdue') return 'warning'
  return 'info'
}

function riskLabel(level: SlaRiskLevel): string {
  if (level === 'severe_overdue') return '严重超时'
  if (level === 'overdue') return '已超时'
  return '即将超时'
}

function alertTypeLabel(row: ShipmentSlaAlert): string {
  const labels = (row.alertTypeLabels || []).filter(Boolean)
  if (labels.length) return labels[0]!
  const t = (row.alertType || '').trim()
  if (t === 'WAREHOUSE_NO_DEPARTURE') return '入库未开船'
  if (t === 'ARRIVAL_NO_DELIVERY') return '到港未送仓'
  if (t === 'DELIVERY_TIME') return '运输时效'
  return t || '运输时效'
}

function overdueSignedDays(row: ShipmentSlaAlert): number | null {
  if (row.daysUntilDue == null) return null
  if (row.daysUntilDue < 0) return row.overdueDays || Math.abs(row.daysUntilDue)
  return -row.daysUntilDue
}

function overdueDaysText(days: number): string {
  if (days > 0) return `+${days} 天`
  if (days < 0) return `${days} 天`
  return '0 天'
}

function overdueDaysClass(days: number): string {
  if (days >= 21) return 'sla-overdue-days sla-overdue-days--severe'
  if (days > 0) return 'sla-overdue-days sla-overdue-days--overdue'
  if (days < 0) return 'sla-overdue-days sla-overdue-days--ahead'
  return 'sla-overdue-days sla-overdue-days--due'
}

function renderOverdueDaysHeader() {
  return h('span', { class: 'inline-flex items-center gap-1' }, [
    '超时天数',
    h(
      NTooltip,
      { trigger: 'hover' },
      {
        trigger: () =>
          h(CircleHelp, {
            class: 'h-3.5 w-3.5 shrink-0 text-zinc-400',
            strokeWidth: ICON_STROKE,
            'aria-label': '超时天数说明',
          }),
        default: () =>
          '正数=已超过截止日的天数；负数=距截止日还剩天数。颜色：绿=未超时，橙=已超时，红=超时较多（≥21 天）。',
      },
    ),
  ])
}

function renderOverdueDaysCell(row: ShipmentSlaAlert) {
  const days = overdueSignedDays(row)
  if (days == null) return h('span', { class: 'text-zinc-400' }, '—')
  return h('span', { class: overdueDaysClass(days) }, overdueDaysText(days))
}

function riskDueTooltip(row: ShipmentSlaAlert): string {
  const dueHint = row.dueDate ? `截止 ${formatMonthDay(row.dueDate) || row.dueDate.slice(0, 10)}` : ''
  const types = (row.alertTypeLabels || []).filter(Boolean)
  const typeHint = types.length > 1 ? `合并类型：${types.join('、')}` : ''
  return [dueHint, typeHint].filter(Boolean).join(' · ')
}

function renderRiskDueCell(row: ShipmentSlaAlert) {
  const title = riskDueTooltip(row)
  const typeLabel = alertTypeLabel(row)
  return h(
    NTooltip,
    { disabled: !title },
    {
      trigger: () =>
        h('span', { class: 'inline-flex flex-wrap items-center gap-1' }, [
          h(
            NTag,
            { size: 'small', type: 'default', bordered: false },
            () => typeLabel,
          ),
          h(
            NTag,
            { size: 'small', type: riskTagType(row.riskLevel), bordered: false },
            () => riskLabel(row.riskLevel),
          ),
        ]),
      default: () => title || '—',
    },
  )
}

function carrierDisplayLabel(row: ShipmentSlaAlert): string {
  const zh = row.carrierNameZh?.trim()
  if (zh) return zh
  return row.carrierCode?.trim() || '—'
}

function statusLabel(status: SlaAlertStatus): string {
  const map: Record<SlaAlertStatus, string> = {
    open: '待处理',
    acknowledged: '已跟进',
    converted: '已转异常',
    resolved: '已解决',
    ignored: '已忽略',
  }
  return map[status] || status
}

function statusTagType(status: SlaAlertStatus): 'default' | 'info' | 'warning' | 'error' | 'success' {
  if (status === 'open') return 'warning'
  if (status === 'acknowledged') return 'info'
  if (status === 'resolved') return 'success'
  if (status === 'converted') return 'error'
  return 'default'
}

function followUpStatusLabel(row: ShipmentSlaAlert): string {
  const base = statusLabel(row.status)
  if (row.status === 'acknowledged') {
    const count = row.followUpCount ?? 0
    if (count > 0) return `${base} · ${count}次`
  }
  return base
}

function followUpTooltip(row: ShipmentSlaAlert): string | null {
  if (row.status !== 'acknowledged') return null
  const count = row.followUpCount ?? 0
  if (count <= 0 && !row.lastFollowUpTime) return null
  const rel = row.lastFollowUpTime ? formatRelativeTime(row.lastFollowUpTime) : null
  const abs = rel?.absolute || row.lastFollowUpTime || '—'
  const ago =
    rel?.relative ||
    (row.lastFollowUpDaysAgo != null && row.lastFollowUpDaysAgo > 0
      ? `${row.lastFollowUpDaysAgo}天前`
      : '刚刚')
  return `上次跟进：${abs}\n${ago} · 共跟进 ${count || 1} 次`
}

function renderStatusCell(row: ShipmentSlaAlert) {
  const tag = h(
    NTag,
    {
      size: 'small',
      type: statusTagType(row.status),
      bordered: false,
    },
    () => followUpStatusLabel(row),
  )
  if (row.status === 'acknowledged') {
    const tip = followUpTooltip(row)
    if (tip) {
      return h(
        NTooltip,
        { placement: 'top' },
        {
          trigger: () => h('span', { class: 'inline-flex cursor-default' }, [tag]),
          default: () => h('span', { class: 'whitespace-pre-line text-xs' }, tip),
        },
      )
    }
  }
  return tag
}

function onFollowTabChange(value: string | null) {
  filterStatus.value = value || null
}

type SummaryBadgeKey = 'pending' | 'warning_soon' | 'overdue' | 'severe_overdue'

const SUMMARY_RISK_KEYS = new Set<string>(['warning_soon', 'overdue', 'severe_overdue'])

const activeSummaryBadge = computed<SummaryBadgeKey | null>(() => {
  const ts = filterTimelinessStatus.value
  if (ts && SUMMARY_RISK_KEYS.has(ts)) return ts as SummaryBadgeKey
  if (!ts) return 'pending'
  return null
})

function onSummaryBadgeClick(key: SummaryBadgeKey) {
  if (key === 'pending') {
    if (filterTimelinessStatus.value) filterTimelinessStatus.value = null
    return
  }
  filterTimelinessStatus.value = filterTimelinessStatus.value === key ? null : key
}

function applyRouteQuery() {
  const q = route.query
  const ts =
    typeof q.timelinessStatus === 'string'
      ? q.timelinessStatus
      : typeof q.riskLevel === 'string'
        ? q.riskLevel
        : null
  filterTimelinessStatus.value = ts
  filterStatus.value = typeof q.status === 'string' ? q.status : null
  if (q.hasException === 'true') filterHasException.value = 'true'
  else if (q.hasException === 'false') filterHasException.value = 'false'
  else filterHasException.value = null
  filterExceptionCode.value = typeof q.exceptionCode === 'string' ? q.exceptionCode : null
  filterChannelCode.value = typeof q.channelCode === 'string' ? q.channelCode : null
}

async function loadSummary() {
  try {
    const summary = await getShipmentSlaSummary()
    pendingOpenCount.value = summary.pendingOpen ?? 0
    severeOverdueCount.value = summary.severeOverdue ?? 0
    overdueCount.value = summary.overdue ?? 0
    warningSoonCount.value = summary.warningSoon ?? 0
    void refreshPendingShipmentSlaAlertCount()
  } catch {
    /* 保留上次统计 */
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listShipmentSlaAlerts({
      scope: filterShowHistory.value ? 'all' : 'todo',
      ...timelinessListParams(filterTimelinessStatus.value),
      status: filterStatus.value || undefined,
      hasException:
        filterHasException.value === 'true'
          ? true
          : filterHasException.value === 'false'
            ? false
            : undefined,
      exceptionCode: filterExceptionCode.value || undefined,
      channelCode: filterChannelCode.value || undefined,
      search: search.value.trim() || undefined,
      limit: pageSize.value,
      offset: (page.value - 1) * pageSize.value,
    })
    items.value = res.items
    total.value = res.total
    syncSelectionWithItems()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

async function runScan() {
  scanning.value = true
  try {
    const res = await evaluateShipmentSlaAlerts()
    if (res.skipped) {
      message.info(res.reason || '扫描已跳过')
    } else {
      message.success(`扫描 ${res.scanned} 单，新建 ${res.created}，更新 ${res.updated}`)
    }
    await Promise.all([load(), loadSummary()])
  } catch (e) {
    message.error(e instanceof Error ? e.message : '扫描失败')
  } finally {
    scanning.value = false
  }
}

function formatTrackingTime(value: string | null | undefined): string {
  const text = (value || '').trim()
  if (!text) return '—'
  return formatAbsoluteDateTime(text) || text.slice(0, 16)
}

function shipmentStub(row: ShipmentSlaAlert): Shipment {
  return {
    id: row.shipmentId,
    shipmentNo: row.shipmentNo || '',
    customer: row.customer ?? null,
    channelCode: row.channelCode ?? null,
    channelNameZh: row.channelNameZh ?? null,
    carrierCode: row.carrierCode ?? null,
    carrierNameZh: row.carrierNameZh ?? null,
    atd: row.atd ?? null,
    expectedDeliveryTime: row.expectedDeliveryTime ?? null,
    deliveredTime: row.deliveredTime ?? null,
    exceptionCode: row.exceptionCode ?? null,
    latestTrackingTime: row.latestTrackingTime ?? null,
    latestTrackingDesc: row.latestTrackingDesc ?? null,
    trackingLogCount: 0,
    carrierLogCount: 0,
    createdTime: row.createdTime || '',
    updatedTime: row.updatedTime || '',
  } as Shipment
}

async function openTrackingDrawer(row: ShipmentSlaAlert, tab: 'internal' | 'carrier' = 'internal') {
  const sid = row.shipmentId?.trim()
  if (!sid) {
    message.warning('缺少运单 ID')
    return
  }
  trackingDrawerTab.value = tab
  trackingDrawerShow.value = true
  trackingDrawerShipment.value = shipmentStub(row)
  try {
    trackingDrawerShipment.value = await getShipment(sid)
  } catch {
    /* 列表行数据兜底 */
  }
}

function handleTrackingDrawerShipmentUpdated(row: Shipment) {
  trackingDrawerShipment.value = row
  const idx = items.value.findIndex((it) => it.shipmentId === row.id)
  if (idx >= 0) {
    items.value[idx] = {
      ...items.value[idx],
      latestTrackingTime: row.latestTrackingTime,
      latestTrackingDesc: row.latestTrackingDesc,
      deliveredTime: row.deliveredTime,
      exceptionCode: row.exceptionCode,
      exceptionDurationLabel: row.exceptionDurationLabel,
    }
  }
}

function renderTrackingCell(row: ShipmentSlaAlert) {
  const has = hasEffectiveInternalTracking(row)
  const time = formatTrackingTime(row.latestTrackingTime)
  const desc = (row.latestTrackingDesc || '').trim()
  const block = has
    ? h('div', { class: 'min-w-0 flex-1' }, [
        h('div', { class: 'sla-tracking-time text-xs tabular-nums leading-tight' }, time),
        h(
          'div',
          {
            class: 'sla-tracking-desc text-xs leading-snug truncate',
            title: desc,
          },
          desc || '—',
        ),
      ])
    : h('span', { class: 'text-xs text-zinc-500' }, '查看轨迹')

  const btn = h(
    'button',
    {
      type: 'button',
      class: 'sla-tracking-btn w-full min-w-0 cursor-pointer rounded px-1 py-0.5 text-left transition-colors',
      onClick: (e: MouseEvent) => {
        e.stopPropagation()
        void openTrackingDrawer(row, 'internal')
      },
    },
    [block],
  )
  const tip = [time, desc].filter((x) => x && x !== '—').join('\n')
  if (tip.length > 36) {
    return h(NTooltip, { trigger: 'hover' }, { trigger: () => btn, default: () => tip })
  }
  return btn
}

function goShipment(row: ShipmentSlaAlert) {
  void router.push({ name: 'shipments', query: { shipmentNo: row.shipmentNo } })
}

async function handleFollowUp(row: ShipmentSlaAlert) {
  try {
    const ids = slaRelatedAlertIds(row)
    if (ids.length > 1) {
      const res = await batchFollowUpShipmentSlaAlerts(ids)
      message.success(`已跟进 ${res.updated} 条`)
    } else {
      await followUpShipmentSlaAlert(row.id)
      message.success(row.status === 'acknowledged' ? '已记录跟进' : '已标记跟进')
    }
    await Promise.all([load(), loadSummary()])
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function handleResolve(row: ShipmentSlaAlert) {
  try {
    const ids = slaRelatedAlertIds(row)
    if (ids.length > 1) {
      const res = await batchResolveShipmentSlaAlerts(ids)
      message.success(`已解决 ${res.updated} 条`)
    } else {
      await resolveShipmentSlaAlert(row.id)
      message.success('已标记解决')
    }
    await Promise.all([load(), loadSummary()])
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function handleIgnore(row: ShipmentSlaAlert) {
  try {
    await ignoreShipmentSlaAlert(row.id)
    message.success('已忽略')
    await Promise.all([load(), loadSummary()])
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

function handleConvert(row: ShipmentSlaAlert) {
  dialog.warning({
    title: '转为人工异常',
    content: `确认将运单 ${row.shipmentNo} 标记为「运输超时」？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await convertShipmentSlaAlert(row.id, { exceptionCode: 'TRANSIT_TIMEOUT' })
        message.success('已转为人工异常')
        await Promise.all([load(), loadSummary()])
      } catch (e) {
        message.error(e instanceof Error ? e.message : '操作失败')
      }
    },
  })
}

async function copyRowShipmentNo(row: ShipmentSlaAlert) {
  const sn = row.shipmentNo?.trim()
  if (!sn) return
  try {
    await navigator.clipboard.writeText(sn)
    message.success('已复制运单号')
  } catch {
    message.error('复制失败')
  }
}

function renderShipmentNoCell(row: ShipmentSlaAlert) {
  const sn = row.shipmentNo || '—'
  const noCell = h('span', { class: 'sla-shipment-no-cell' }, [
    h(
      'button',
      {
        type: 'button',
        class: 'text-left text-[var(--color-accent-text)] hover:underline shrink-0',
        onClick: () => goShipment(row),
      },
      sn,
    ),
    row.shipmentNo
      ? h(
          NTooltip,
          { trigger: 'hover', showArrow: false },
          {
            trigger: () =>
              h(
                'button',
                {
                  type: 'button',
                  class: 'sla-shipment-no-copy-btn',
                  'aria-label': '复制运单号',
                  onClick: (e: MouseEvent) => {
                    e.stopPropagation()
                    void copyRowShipmentNo(row)
                  },
                },
                [
                  h(Copy, {
                    class: 'h-3.5 w-3.5',
                    strokeWidth: ICON_STROKE,
                    'aria-hidden': 'true',
                  }),
                ],
              ),
            default: () => '复制运单号',
          },
        )
      : null,
  ])
  const children = [noCell]
  if (row.exceptionCode) {
    children.push(
      h(ExceptionStatusBadge, {
        code: row.exceptionCode,
        label: row.exceptionNameZh || row.exceptionCode,
        durationLabel: row.exceptionDurationLabel,
        class: 'shrink-0',
      }),
    )
  }
  return h('span', { class: 'inline-flex flex-nowrap items-center gap-1.5' }, children)
}

/** 列表展示用 MM-DD（去掉年） */
function formatMonthDay(value: string | null | undefined): string {
  const v = (value || '').trim()
  if (!v) return ''
  const datePart = v.slice(0, 10)
  if (datePart.length >= 10 && datePart[4] === '-' && datePart[7] === '-') {
    return datePart.slice(5)
  }
  return v
}

function formatDateFull(value: string | null | undefined): string {
  const v = (value || '').trim()
  return v ? v.slice(0, 10) : ''
}

function renderTransitTimeHeader() {
  return h('div', { class: 'leading-tight text-center' }, [
    h('div', '运输时间'),
    h('div', { class: 'text-[11px] font-normal text-zinc-400 whitespace-nowrap' }, '起运 - 到港 / 截止日'),
  ])
}

function renderTransitTimeCell(row: ShipmentSlaAlert) {
  const startMd = formatMonthDay(row.atd)
  const endMd = formatMonthDay(row.ata)
  const dueMd = formatMonthDay(row.dueDate)
  const parts = [startMd, endMd]
  const hasAny = parts.some(Boolean)

  const tipParts = [
    formatDateFull(row.atd) ? `起运 ${formatDateFull(row.atd)}` : '',
    formatDateFull(row.ata) ? `到港 ${formatDateFull(row.ata)}` : '',
    formatDateFull(row.dueDate) ? `截止 ${formatDateFull(row.dueDate)}` : '',
  ].filter(Boolean)
  const tip = tipParts.join(' · ')

  const rangeChildren: ReturnType<typeof h>[] = []
  if (!hasAny) {
    rangeChildren.push(h('span', { class: 'font-semibold text-zinc-800' }, '—'))
  } else {
    parts.forEach((part, index) => {
      if (index > 0) {
        rangeChildren.push(
          h('span', { class: 'mx-0.5 font-semibold text-zinc-300' }, '~'),
        )
      }
      rangeChildren.push(
        h('span', { class: 'font-semibold text-zinc-800' }, part || '—'),
      )
    })
  }

  const body = h('div', { class: 'leading-tight' }, [
    h('div', { class: 'tabular-nums whitespace-nowrap' }, rangeChildren),
    dueMd
      ? h(
          'div',
          { class: 'text-xs font-semibold tabular-nums text-zinc-400 whitespace-nowrap' },
          ['截止 ', h('span', { class: 'text-zinc-500' }, dueMd)],
        )
      : null,
  ])

  if (!tip) return body
  return h(
    NTooltip,
    { placement: 'top' },
    {
      trigger: () => h('span', { class: 'inline-flex cursor-default' }, [body]),
      default: () => tip,
    },
  )
}

function renderDaysInTransitCell(row: ShipmentSlaAlert) {
  const total = row.totalDaysInTransit ?? row.daysInTransit
  const net = row.netDaysInTransit ?? total
  if (net == null && total == null) return '—'

  const exc = row.exceptionDurationLabel?.trim()
  const hadPastException = !row.exceptionCode?.trim() && exc && exc !== '—'
  const displayDays = net ?? total

  const body =
    exc && exc !== '—'
      ? h('span', { class: 'tabular-nums' }, [
          `${displayDays} 天 `,
          hadPastException
            ? h(
                NTooltip,
                { trigger: 'hover', showArrow: false },
                {
                  trigger: () =>
                    h('span', { class: 'cursor-default text-xs text-zinc-400' }, `(${exc})`),
                  default: () => '曾发生异常',
                },
              )
            : h('span', { class: 'text-xs text-zinc-400' }, `(${exc})`),
        ])
      : h('span', { class: 'tabular-nums' }, `${displayDays} 天`)

  if (total != null && exc && exc !== '—') {
    return h(
      NTooltip,
      { placement: 'top' },
      {
        trigger: () => h('span', { class: 'inline-flex cursor-default' }, [body]),
        default: () => `总运输天数 ${total} 天`,
      },
    )
  }
  return body
}

const shipmentNoColWidth = computed(() => {
  let maxLen = 10
  let hasException = false
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.shipmentNo || '').length)
    if (row.exceptionCode) hasException = true
  }
  const textW = Math.ceil(maxLen * 7.5) + 21
  const copyW = 26
  const badgeW = hasException ? 30 : 0
  return Math.min(385, Math.max(220, textW + copyW + badgeW))
})

const columns = computed<DataTableColumns<ShipmentSlaAlert>>(() => [
  { type: 'selection', fixed: 'left', width: 40 },
  {
    title: '运单号',
    key: 'shipmentNo',
    width: shipmentNoColWidth.value,
    render: (row) => renderShipmentNoCell(row),
  },
  { title: '客户', key: 'customer', width: 100, ellipsis: { tooltip: true } },
  {
    title: '渠道',
    key: 'channelCode',
    width: 120,
    render: (row) => row.channelNameZh || row.channelCode || '—',
  },
  {
    title: '承运商',
    key: 'carrierCode',
    width: 96,
    ellipsis: { tooltip: true },
    render: (row) => {
      const label = carrierDisplayLabel(row)
      const code = row.carrierCode?.trim()
      if (!code || label === code) return label
      return h(
        NTooltip,
        { placement: 'top' },
        {
          trigger: () => h('span', { class: 'cursor-default' }, label),
          default: () => code,
        },
      )
    },
  },
  {
    title: '入库时间',
    key: 'warehouseEntryTime',
    width: 88,
    align: 'center',
    render: (row) => {
      const md = formatMonthDay(row.warehouseEntryTime)
      if (!md) return '—'
      const full = formatDateFull(row.warehouseEntryTime)
      return h(
        NTooltip,
        { placement: 'top' },
        {
          trigger: () =>
            h('span', { class: 'cursor-default font-semibold tabular-nums text-zinc-800' }, md),
          default: () => full || md,
        },
      )
    },
  },
  {
    title: () => renderTransitTimeHeader(),
    key: 'transitTime',
    width: 132,
    align: 'center',
    render: (row) => renderTransitTimeCell(row),
  },
  {
    title: '已运输天数(异常天数)',
    key: 'daysInTransit',
    width: 108,
    align: 'center',
    render: (row) => renderDaysInTransitCell(row),
  },
  {
    title: '预估时效',
    key: 'estimatedDays',
    width: 88,
    align: 'center',
    render: (row) => (row.estimatedDays != null ? `${row.estimatedDays} 天` : '—'),
  },
  {
    title: () => renderOverdueDaysHeader(),
    key: 'overdueDays',
    width: 100,
    align: 'center',
    render: (row) => renderOverdueDaysCell(row),
  },
  {
    title: '时效状态',
    key: 'riskDue',
    width: 168,
    render: (row) => renderRiskDueCell(row),
  },
  {
    title: '轨迹',
    key: 'latestTracking',
    minWidth: 168,
    ellipsis: { tooltip: false },
    render: (row) => renderTrackingCell(row),
  },
  {
    title: '跟进状态',
    key: 'status',
    width: 96,
    render: (row) => renderStatusCell(row),
  },
  {
    title: '操作',
    key: 'actions',
    width: 260,
    fixed: 'right',
    render: (row) => {
      if (!['open', 'acknowledged'].includes(row.status)) {
        return h('span', { class: 'text-zinc-500' }, '—')
      }
      return h(NSpace, { size: 4 }, () => [
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: row.status !== 'open',
            type: row.status === 'open' ? 'warning' : 'default',
            onClick: () => handleFollowUp(row),
          },
          () => (row.status === 'acknowledged' ? '再跟进' : '已跟进'),
        ),
        h(
          NButton,
          { size: 'tiny', quaternary: true, onClick: () => handleResolve(row) },
          () => '已解决',
        ),
        h(
          NButton,
          { size: 'tiny', quaternary: true, onClick: () => handleConvert(row) },
          () => '转异常',
        ),
        h(NButton, { size: 'tiny', quaternary: true, onClick: () => handleIgnore(row) }, () => '忽略'),
      ])
    },
  },
])

watch([filterTimelinessStatus, filterStatus, filterHasException, filterExceptionCode, filterChannelCode, filterShowHistory], () => {
  page.value = 1
  void router.replace({
    query: {
      ...(filterTimelinessStatus.value ? { timelinessStatus: filterTimelinessStatus.value } : {}),
      ...(filterStatus.value ? { status: filterStatus.value } : {}),
      ...(filterHasException.value ? { hasException: filterHasException.value } : {}),
      ...(filterExceptionCode.value ? { exceptionCode: filterExceptionCode.value } : {}),
      ...(filterChannelCode.value ? { channelCode: filterChannelCode.value } : {}),
    },
  })
  load()
})

watch([page, pageSize], load)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
})

onMounted(() => {
  applyRouteQuery()
  void load()
  void loadSummary()
  void getShipmentFilterOptions()
    .then((opts) => {
      filterOptions.value = opts
      const m: Record<string, string> = {}
      for (const t of opts.exceptionTypes) {
        m[t.code] = t.nameZh
      }
      exceptionLabelByCode.value = m
    })
    .catch(() => {
      /* 异常类型标签可选 */
    })
})
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-4">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3">
      <div class="min-w-0">
        <h1 class="page-h2">异常跟踪</h1>
        <div class="sla-summary-bar mt-1.5" role="toolbar" aria-label="异常摘要筛选">
          <button
            type="button"
            class="sla-summary-bar__badge sla-summary-bar__badge--exception"
            :class="{ 'is-active': activeSummaryBadge === 'pending' }"
            :aria-pressed="activeSummaryBadge === 'pending'"
            @click="onSummaryBadgeClick('pending')"
          >
            <span class="sla-summary-bar__dot sla-summary-bar__dot--exception" aria-hidden="true" />
            <span class="sla-summary-bar__label">异常</span>
            <span class="sla-summary-bar__count">{{ pendingOpenCount }}</span>
          </button>
          <button
            type="button"
            class="sla-summary-bar__badge sla-summary-bar__badge--warning"
            :class="{ 'is-active': activeSummaryBadge === 'warning_soon' }"
            :aria-pressed="activeSummaryBadge === 'warning_soon'"
            @click="onSummaryBadgeClick('warning_soon')"
          >
            <span class="sla-summary-bar__dot sla-summary-bar__dot--warning" aria-hidden="true" />
            <span class="sla-summary-bar__label">即将超时</span>
            <span class="sla-summary-bar__count">{{ warningSoonCount }}</span>
          </button>
          <button
            type="button"
            class="sla-summary-bar__badge sla-summary-bar__badge--overdue"
            :class="{ 'is-active': activeSummaryBadge === 'overdue' }"
            :aria-pressed="activeSummaryBadge === 'overdue'"
            @click="onSummaryBadgeClick('overdue')"
          >
            <span class="sla-summary-bar__dot sla-summary-bar__dot--overdue" aria-hidden="true" />
            <span class="sla-summary-bar__label">已超时</span>
            <span class="sla-summary-bar__count">{{ overdueCount }}</span>
          </button>
          <button
            type="button"
            class="sla-summary-bar__badge sla-summary-bar__badge--severe"
            :class="{ 'is-active': activeSummaryBadge === 'severe_overdue' }"
            :aria-pressed="activeSummaryBadge === 'severe_overdue'"
            @click="onSummaryBadgeClick('severe_overdue')"
          >
            <span class="sla-summary-bar__dot sla-summary-bar__dot--severe" aria-hidden="true" />
            <span class="sla-summary-bar__label">严重超时</span>
            <span class="sla-summary-bar__count">{{ severeOverdueCount }}</span>
          </button>
          <span class="sla-summary-bar__divider" aria-hidden="true" />
          <span class="sla-summary-bar__total">当前列表 {{ total }} 条</span>
        </div>
      </div>
      <NSpace>
        <NButton type="primary" size="small" :loading="scanning" @click="runScan">
          <template #icon>
            <ScanBarcode class="h-4 w-4" :stroke-width="ICON_STROKE" aria-hidden="true" />
          </template>
          立即扫描
        </NButton>
      </NSpace>
    </div>

    <div class="sla-exceptions-filters panel shrink-0 px-3 py-2">
      <div class="sla-exceptions-filters__row scrollbar-subtle">
        <NRadioGroup
          :value="filterStatus ?? ''"
          size="small"
          class="sla-follow-tabs shrink-0"
          @update:value="onFollowTabChange"
        >
          <NRadioButton value="">全部待办</NRadioButton>
          <NRadioButton value="open">待处理</NRadioButton>
          <NRadioButton value="acknowledged">已跟进</NRadioButton>
        </NRadioGroup>
        <NSelect
          v-model:value="filterTimelinessStatus"
          :options="timelinessStatusOptions"
          clearable
          placeholder="时效状态"
          class="sla-exceptions-filter-select sla-exceptions-filter-select--wide"
          size="small"
        />
        <NSelect
          v-model:value="filterStatus"
          :options="statusOptions"
          clearable
          placeholder="跟进状态"
          class="sla-exceptions-filter-select"
          size="small"
        />
        <NSelect
          v-model:value="filterHasException"
          :options="hasExceptionOptions"
          clearable
          placeholder="有无异常"
          class="sla-exceptions-filter-select"
          size="small"
        />
        <NSelect
          v-model:value="filterExceptionCode"
          :options="exceptionFilterOptions"
          clearable
          filterable
          placeholder="异常类型"
          class="sla-exceptions-filter-select sla-exceptions-filter-select--wide"
          size="small"
        />
        <NSelect
          v-model:value="filterChannelCode"
          :options="channelCodeOptions"
          clearable
          filterable
          placeholder="渠道"
          class="sla-exceptions-filter-select sla-exceptions-filter-select--wide"
          size="small"
        />
        <NInput
          v-model:value="search"
          clearable
          placeholder="运单号 / 客户"
          class="sla-exceptions-filter-search"
          size="small"
        />
        <NCheckbox v-model:checked="filterShowHistory" size="small" class="shrink-0 whitespace-nowrap">
          含已签收/历史
        </NCheckbox>
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-hidden rounded-lg border border-[var(--color-border)]">
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :row-key="rowKey"
        :columns="columns"
        :data="items"
        :loading="loading"
        :bordered="false"
        flex-height
        class="sla-exceptions-table h-full"
        size="small"
        :scroll-x="1720"
      />
    </div>

    <div
      v-if="selectedCount > 0"
      class="sla-exceptions-selection-bar shrink-0 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="sla-exceptions-selection-bar__label text-sm">
          已选
          <strong class="sla-exceptions-selection-bar__count">{{ selectedCount }}</strong>
          条（本页）
        </span>
        <NButton size="small" quaternary @click="clearSelection">取消选择</NButton>
      </div>
      <NSpace size="small">
        <NButton size="small" title="复制选中运单号（换行）" @click="copySelectedShipmentNos">
          复制运单号
        </NButton>
        <NButton
          size="small"
          type="warning"
          :loading="batchSubmitting"
          :disabled="actionableSelectedRows.length === 0"
          @click="handleBatchFollowUp"
        >
          已跟进
        </NButton>
        <NButton
          size="small"
          :loading="batchSubmitting"
          :disabled="actionableSelectedRows.length === 0"
          @click="handleBatchResolve"
        >
          已解决
        </NButton>
        <NButton
          size="small"
          :loading="batchSubmitting"
          :disabled="actionableSelectedRows.length === 0"
          @click="handleBatchIgnore"
        >
          忽略
        </NButton>
      </NSpace>
    </div>

    <ShipmentTrackingDrawer
      v-model:show="trackingDrawerShow"
      :shipment="trackingDrawerShipment"
      :initial-tab="trackingDrawerTab"
      :exception-label-by-code="exceptionLabelByCode"
      @shipment-updated="handleTrackingDrawerShipmentUpdated"
    />

    <div class="flex shrink-0 justify-end">
      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[20, 50, 100]"
        show-size-picker
        size="small"
      />
    </div>
  </div>
</template>

<style scoped>
.sla-summary-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  line-height: 1.25rem;
  color: var(--color-fg);
}

.sla-summary-bar__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  margin: 0;
  padding: 0.25rem 0.625rem;
  border: 1px solid var(--color-border, #e4e4e7);
  border-radius: 9999px;
  background: var(--color-bg-elevated, #fff);
  color: inherit;
  font: inherit;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.sla-summary-bar__badge:hover {
  border-color: #d4d4d8;
  background: #fafafa;
}

.sla-summary-bar__badge:focus-visible {
  outline: 2px solid var(--color-accent, #8b5cf6);
  outline-offset: 2px;
}

.sla-summary-bar__badge.is-active {
  box-shadow: inset 0 0 0 1px transparent;
}

.sla-summary-bar__badge--exception.is-active {
  border-color: #e02020;
  background: #fef2f2;
}

.sla-summary-bar__badge--warning.is-active {
  border-color: #f7b500;
  background: #fffbeb;
}

.sla-summary-bar__badge--overdue.is-active {
  border-color: #fa6400;
  background: #fff7ed;
}

.sla-summary-bar__badge--severe.is-active {
  border-color: #d0021b;
  background: #fef2f2;
}

.sla-summary-bar__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  flex-shrink: 0;
}

.sla-summary-bar__dot--exception {
  background: #e02020;
}

.sla-summary-bar__dot--warning {
  background: #f7b500;
}

.sla-summary-bar__dot--overdue {
  background: #fa6400;
}

.sla-summary-bar__dot--severe {
  background: #d0021b;
}

.sla-summary-bar__label {
  color: var(--color-fg-secondary, #52525b);
}

.sla-summary-bar__count {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis, #18181b);
}

.sla-summary-bar__badge.is-active .sla-summary-bar__label,
.sla-summary-bar__badge.is-active .sla-summary-bar__count {
  color: inherit;
}

.sla-summary-bar__divider {
  width: 1px;
  height: 0.875rem;
  margin: 0 0.25rem;
  background: var(--color-border, #e4e4e7);
  flex-shrink: 0;
}

.sla-summary-bar__total {
  color: #999999;
  font-variant-numeric: tabular-nums;
  padding-left: 0.25rem;
}

.sla-exceptions-table :deep(.sla-overdue-days) {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  white-space: nowrap;
}

.sla-exceptions-table :deep(.sla-overdue-days--severe) {
  color: #d0021b;
}

.sla-exceptions-table :deep(.sla-overdue-days--overdue) {
  color: #fa6400;
}

.sla-exceptions-table :deep(.sla-overdue-days--ahead) {
  color: #16a34a;
}

.sla-exceptions-table :deep(.sla-overdue-days--due) {
  color: #f7b500;
}

.sla-follow-tabs {
  flex-shrink: 0;
}

.sla-exceptions-selection-bar {
  border: 1px solid color-mix(in srgb, var(--color-accent-text) 28%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent-text) 6%, transparent);
}

.sla-exceptions-selection-bar__label {
  color: var(--color-muted);
}

.sla-exceptions-selection-bar__count {
  color: var(--color-text);
}

.sla-exceptions-filters {
  min-width: 0;
}

.sla-exceptions-filters__row {
  display: flex;
  min-width: 0;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5rem;
  overflow-x: auto;
  overflow-y: hidden;
}

.sla-exceptions-filters__row > * {
  flex: 0 0 auto;
}

.sla-exceptions-filter-select {
  width: 7.25rem;
  min-width: 6.5rem;
}

.sla-exceptions-filter-select--wide {
  width: 10.5rem;
  min-width: 9rem;
}

.sla-exceptions-filter-search {
  width: 11rem;
  min-width: 9rem;
}

.sla-tracking-btn:hover {
  background: color-mix(in srgb, var(--color-accent-text) 8%, transparent);
}

.sla-tracking-time {
  color: var(--color-muted);
}

.sla-tracking-desc {
  color: var(--color-text);
}

.sla-exceptions-table :deep(.sla-shipment-no-cell) {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  flex-shrink: 0;
  white-space: nowrap;
}

.sla-exceptions-table :deep(.sla-shipment-no-copy-btn) {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border: none;
  border-radius: 0.375rem;
  padding: 0;
  background: transparent;
  color: var(--color-muted);
  cursor: pointer;
  opacity: 0;
  transition:
    opacity 0.15s ease,
    background-color 0.15s ease,
    color 0.15s ease;
}

.sla-exceptions-table :deep(.n-data-table-tr:hover .sla-shipment-no-copy-btn),
.sla-exceptions-table :deep(.sla-shipment-no-copy-btn:focus-visible) {
  opacity: 1;
}

.sla-exceptions-table :deep(.sla-shipment-no-copy-btn:hover) {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg);
}
</style>
