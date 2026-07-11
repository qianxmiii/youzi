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
import { Copy } from 'lucide-vue-next'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ExceptionStatusBadge from '@/components/common/ExceptionStatusBadge.vue'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import { getShipment, getShipmentFilterOptions, type ShipmentFilterOptions } from '@/api/shipments'
import {
  followUpShipmentSlaAlert,
  ignoreShipmentSlaAlert,
  convertShipmentSlaAlert,
  evaluateShipmentSlaAlerts,
  listShipmentSlaAlerts,
  resolveShipmentSlaAlert,
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
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : `${label}失败`)
  } finally {
    batchSubmitting.value = false
  }
}

function handleBatchFollowUp() {
  void runBatchAction('跟进', actionableSelectedRows.value, (row) => followUpShipmentSlaAlert(row.id))
}

function handleBatchResolve() {
  void runBatchAction('解决', actionableSelectedRows.value, (row) => resolveShipmentSlaAlert(row.id))
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

function riskTagLabel(row: ShipmentSlaAlert): string {
  const t = (row.alertType || '').trim()
  if (t === 'WAREHOUSE_NO_DEPARTURE') return '入库未开船'
  if (t === 'ARRIVAL_NO_DELIVERY') return '到港未送仓'
  return riskLabel(row.riskLevel)
}

function riskDueSuffix(row: ShipmentSlaAlert): string {
  if (row.daysUntilDue == null) return ''
  if (row.daysUntilDue >= 0) return `剩 ${row.daysUntilDue} 天`
  return `超 ${row.overdueDays} 天`
}

function renderRiskDueCell(row: ShipmentSlaAlert) {
  const suffix = riskDueSuffix(row)
  const dueHint = row.dueDate ? `截止 ${row.dueDate.slice(0, 10)}` : ''
  const title = [dueHint, suffix].filter(Boolean).join(' · ')
  return h(
    NTooltip,
    { disabled: !title },
    {
      trigger: () =>
        h('span', { class: 'inline-flex flex-wrap items-center gap-1' }, [
          h(
            NTag,
            { size: 'small', type: riskTagType(row.riskLevel), bordered: false },
            () => riskTagLabel(row),
          ),
          suffix
            ? h('span', { class: 'text-xs tabular-nums text-zinc-500 whitespace-nowrap' }, suffix)
            : null,
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
    void refreshPendingShipmentSlaAlertCount()
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
    await load()
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
    await followUpShipmentSlaAlert(row.id)
    message.success(row.status === 'acknowledged' ? '已记录跟进' : '已标记跟进')
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function handleResolve(row: ShipmentSlaAlert) {
  try {
    await resolveShipmentSlaAlert(row.id)
    message.success('已标记解决')
    await load()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

async function handleIgnore(row: ShipmentSlaAlert) {
  try {
    await ignoreShipmentSlaAlert(row.id)
    message.success('已忽略')
    await load()
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
        await load()
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
  { title: '入库时间', key: 'warehouseEntryTime', width: 108, render: (row) => (row.warehouseEntryTime || '—').slice(0, 10) },
  { title: 'ATD', key: 'atd', width: 108, render: (row) => (row.atd || '—').slice(0, 10) },
  { title: 'ATA', key: 'ata', width: 108, render: (row) => (row.ata || '—').slice(0, 10) },
  { title: '截止日', key: 'dueDate', width: 108 },
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
    title: '时效状态',
    key: 'riskDue',
    width: 128,
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
  load()
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
      <div>
        <h1 class="page-h2">异常跟踪</h1>
        <p class="mt-1 text-sm text-zinc-500">运输时效预警与人工异常集中处理</p>
      </div>
      <NSpace>
        <NButton :loading="scanning" @click="runScan">立即扫描</NButton>
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
        :scroll-x="1848"
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
