<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDataTable,
  NDatePicker,
  NDrawer,
  NDrawerContent,
  NInput,
  NInputNumber,
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
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import {
  batchCreatePaymentReminderFollowups,
  createPaymentReminderFollowup,
  exportPaymentRemindersExcel,
  getPaymentReminderCustomerRanking,
  getPaymentReminderSummary,
  listPaymentReminderFollowups,
  listPaymentReminders,
  setPaymentCollectionTerm,
  type PaymentReminderCustomerRank,
  type PaymentReminderFollowup,
  type PaymentReminderItem,
  type PaymentReminderScope,
} from '@/api/paymentReminders'
import { batchUpdateShipments, getShipment, getShipmentFilterOptions, syncShipmentsFromDps } from '@/api/shipments'
import {
  PAYMENT_FOLLOWUP_STATUS_OPTIONS,
  PAYMENT_REMINDER_TYPE_OPTIONS,
  SETTLEMENT_METHOD_FILTER_OPTIONS,
  paymentReminderDueHint,
  paymentReminderTypeLabel,
  settlementMethodLabel,
} from '@/constants/paymentReminders'
import { ICON_STROKE } from '@/constants/icons'
import { resolveShipmentListStatusDisplay } from '@/constants/shipmentRouteStatus'
import { SHIPMENT_STATUS_LABEL_ZH, shipmentListPathForStatus } from '@/constants/shipmentWorkspace'
import { usePendingPaymentReminderCount } from '@/composables/usePendingPaymentReminderCount'
import { shipmentPaymentStatusLabel } from '@/utils/formatGroupAlertMessage'
import { formatAbsoluteDateTime, formatRelativeTime } from '@/utils/formatDateTime'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'
import type { Shipment } from '@/types/shipment'

const message = useMessage()
const dialog = useDialog()
const route = useRoute()
const router = useRouter()
const { refreshPendingPaymentReminderCount } = usePendingPaymentReminderCount()

const SCOPE_VALUES: PaymentReminderScope[] = [
  'todo',
  'all_unpaid',
  'upcoming_7_days',
  'today',
  'overdue',
  'missing_rule',
  'missing_date',
]

function applyRouteScope() {
  const q = route.query.scope
  const raw = Array.isArray(q) ? q[0] : q
  const text = String(raw || '').trim() as PaymentReminderScope
  if (SCOPE_VALUES.includes(text)) {
    scope.value = text
  }
}

const loading = ref(false)
const exporting = ref(false)
const batchSubmitting = ref(false)
const syncingDps = ref(false)
const items = ref<PaymentReminderItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const checkedRowKeys = ref<string[]>([])
const todoCount = ref(0)
const allUnpaidCount = ref(0)
const overdueCount = ref(0)
const customerRanks = ref<PaymentReminderCustomerRank[]>([])
const receivablePendingCount = ref(0)
const rankExpanded = ref(false)
const rankShowAll = ref(false)
const rankTotal = ref(0)

const scope = ref<PaymentReminderScope>('todo')
const filterCustomer = ref<string | null>(null)
const filterChannelCategory = ref<string | null>(null)
const filterSettlementMethod = ref<string | null>(null)
const filterReminderType = ref<string | null>(null)
const filterFollowupStatus = ref<'unfollowed' | 'followed' | null>(null)
/** 与运单列表一致：未勾选=排除整柜；勾选=仅整柜 */
const filterFclOnly = ref(false)
const filterLargeAmount = ref(false)
const filterReceivablePending = ref(false)
const sortByReceivable = ref(false)
const search = ref('')
const LARGE_RECEIVABLE = 10000

const customerOptions = ref<{ label: string; value: string }[]>([])
const channelCategoryOptions = ref<{ label: string; value: string }[]>([])

const followupDrawerShow = ref(false)
const followupLoading = ref(false)
const followupShipment = ref<PaymentReminderItem | null>(null)
const followupItems = ref<PaymentReminderFollowup[]>([])

const trackingDrawerShow = ref(false)
const trackingDrawerShipment = ref<Shipment | null>(null)
const trackingDrawerTab = ref<'internal' | 'carrier'>('internal')

const selectedRows = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.shipmentId)),
)
const selectedCount = computed(() => selectedRows.value.length)
const selectedReceivableTotal = computed(() =>
  selectedRows.value.reduce((sum, row) => sum + (row.receivableCny ?? 0), 0),
)
const selectedMissingReceivable = computed(
  () => selectedRows.value.filter((row) => row.receivableCny == null).length,
)
const selectedWithReceivable = computed(
  () => selectedCount.value - selectedMissingReceivable.value,
)
const selectedShipmentNos = computed(() =>
  selectedRows.value.map((r) => displayShipmentNo(r)).filter(Boolean),
)

/** DPS 更新必须用真实运单号（非整柜展示用的提单号） */
const selectedRealShipmentNos = computed(() =>
  selectedRows.value.map((r) => (r.shipmentNo || '').trim()).filter(Boolean),
)

function rowKey(row: PaymentReminderItem) {
  return row.shipmentId
}

function isFclRow(row: PaymentReminderItem) {
  return Boolean(row.isFcl)
}

/** 整柜：运单号列展示提单号；否则运单号 */
function displayShipmentNo(row: PaymentReminderItem) {
  if (isFclRow(row)) {
    return (row.billOfLadingNo || '').trim() || (row.shipmentNo || '').trim()
  }
  return (row.shipmentNo || '').trim()
}

/** 整柜：客户单号列展示柜号；否则客户单号 */
function displayCustomerNo(row: PaymentReminderItem) {
  if (isFclRow(row)) {
    return (row.containerNo || '').trim()
  }
  return (row.customerNo || '').trim()
}

function syncSelectionWithItems() {
  const visible = new Set(items.value.map((row) => row.shipmentId))
  checkedRowKeys.value = checkedRowKeys.value.filter((id) => visible.has(id))
}

function clearSelection() {
  checkedRowKeys.value = []
}

function reminderQuery(extra?: { limit?: number; offset?: number }) {
  return {
    scope: scope.value,
    customer: filterCustomer.value || undefined,
    channelCategory: filterChannelCategory.value || undefined,
    settlementMethod: filterSettlementMethod.value || undefined,
    reminderType: filterReminderType.value || undefined,
    followupStatus: filterFollowupStatus.value || undefined,
    search: search.value.trim() || undefined,
    fclOnly: filterFclOnly.value,
    minReceivable: filterLargeAmount.value ? LARGE_RECEIVABLE : undefined,
    receivablePending: filterReceivablePending.value || undefined,
    sortBy: sortByReceivable.value ? ('receivable' as const) : undefined,
    ...extra,
  }
}

function rankingQuery() {
  return {
    ...reminderQuery(),
    customer: undefined,
  }
}

const visibleRanks = computed(() =>
  rankShowAll.value ? customerRanks.value : customerRanks.value.slice(0, 10),
)
const rankMax = computed(() => customerRanks.value.reduce((max, row) => Math.max(max, row.total), 0))

function rankWidth(amount: number) {
  if (rankMax.value <= 0) return '0%'
  return `${Math.max(4, (amount / rankMax.value) * 100)}%`
}

function toggleRankPanel() {
  rankExpanded.value = !rankExpanded.value
  if (!rankExpanded.value) rankShowAll.value = false
}

function toggleRankCustomer(name: string) {
  filterCustomer.value = filterCustomer.value === name ? null : name
}

async function loadRanking() {
  try {
    const res = await getPaymentReminderCustomerRanking({ ...rankingQuery(), limit: 100 })
    customerRanks.value = res.items
    receivablePendingCount.value = res.pendingCount
    rankTotal.value = res.totalReceivable ?? 0
  } catch {
    customerRanks.value = []
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listPaymentReminders(
      reminderQuery({
        limit: pageSize.value,
        offset: (page.value - 1) * pageSize.value,
      }),
    )
    items.value = res.items
    total.value = res.total
    syncSelectionWithItems()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadSummary() {
  try {
    const summary = await getPaymentReminderSummary({ fclOnly: filterFclOnly.value })
    todoCount.value = summary.todoCount ?? 0
    allUnpaidCount.value = summary.allUnpaidCount ?? 0
    overdueCount.value = summary.overdueCount ?? 0
    await refreshPendingPaymentReminderCount()
  } catch {
    /* 保留上次统计 */
  }
}

async function reloadAfterMutation() {
  await Promise.all([load(), loadSummary()])
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleExport() {
  exporting.value = true
  try {
    const blob = await exportPaymentRemindersExcel(
      reminderQuery({
        limit: Math.min(total.value || 10_000, 10_000),
        offset: 0,
      }),
    )
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').slice(0, 14)
    downloadBlob(blob, `催款列表导出_${ts}.xlsx`)
    message.success(`已导出 ${total.value} 条（当前筛选）`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

async function loadFilterOptions() {
  try {
    const opts = await getShipmentFilterOptions()
    customerOptions.value = (opts.customers || []).map((c) => ({ label: c, value: c }))
    channelCategoryOptions.value = (opts.channelCategories || []).map((c) => ({ label: c, value: c }))
  } catch {
    customerOptions.value = []
  }
}

function onScopeTabChange(value: string) {
  scope.value = (value || 'todo') as PaymentReminderScope
}

function promptNote(title: string, onConfirm: (note: string) => Promise<void>) {
  const noteRef = ref('')
  dialog.create({
    title,
    content: () =>
      h(NInput, {
        type: 'textarea',
        placeholder: '催款备注（建议填写，如：已电话催款，客户说明本周五付款）',
        autosize: { minRows: 3, maxRows: 6 },
        value: noteRef.value,
        onUpdateValue: (v: string) => {
          noteRef.value = v
        },
      }),
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      await onConfirm(noteRef.value.trim())
    },
  })
}

async function handleFollowup(row: PaymentReminderItem) {
  promptNote(`已跟进 · ${row.shipmentNo}`, async (note) => {
    await createPaymentReminderFollowup(row.shipmentId, note)
    message.success('已记录跟进')
    await reloadAfterMutation()
  })
}

async function handleBatchFollowup() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  promptNote(`批量已跟进（${rows.length} 条）`, async (note) => {
    batchSubmitting.value = true
    try {
      const res = await batchCreatePaymentReminderFollowups(
        rows.map((r) => r.shipmentId),
        note,
      )
      message.success(`已跟进 ${res.created} 条${res.failed ? `，失败 ${res.failed} 条` : ''}`)
      clearSelection()
      await reloadAfterMutation()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '批量跟进失败')
    } finally {
      batchSubmitting.value = false
    }
  })
}

async function markPaid(ids: string[]) {
  if (!ids.length) return
  batchSubmitting.value = true
  try {
    const res = await batchUpdateShipments(ids, { paymentStatus: 'PAID' })
    const failCount = res.skipped.length + res.errors.length
    message.success(`已标记付款 ${res.updated ?? 0} 条${failCount ? `，失败 ${failCount} 条` : ''}`)
    clearSelection()
    await reloadAfterMutation()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '标记已付款失败')
  } finally {
    batchSubmitting.value = false
  }
}

function handleMarkPaid(row: PaymentReminderItem) {
  dialog.warning({
    title: '标记已付款',
    content: `确认将运单 ${row.shipmentNo} 标记为已付款？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: () => markPaid([row.shipmentId]),
  })
}

function ymdFromTs(ts: number) {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function addDaysYmd(ymd: string, days: number) {
  const [year, month, day] = ymd.split('-').map(Number)
  const date = new Date(year, month - 1, day)
  date.setDate(date.getDate() + days)
  return ymdFromTs(date.getTime())
}

function tsFromYmd(ymd: string) {
  const [year, month, day] = ymd.split('-').map(Number)
  return new Date(year, month - 1, day).getTime()
}

function diffDays(fromYmd: string, toYmd: string) {
  return Math.round((tsFromYmd(toYmd) - tsFromYmd(fromYmd)) / 86400000)
}

function openCollectionTermDialog() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  const startTs = ref<number | null>(Date.now())
  const termDays = ref(21)
  const dueTs = ref<number | null>(tsFromYmd(addDaysYmd(ymdFromTs(Date.now()), 21)))
  const advanceDays = ref(7)

  function syncDueFromDays() {
    if (startTs.value == null) return
    const days = Math.trunc(Number(termDays.value))
    if (!Number.isFinite(days)) return
    dueTs.value = tsFromYmd(addDaysYmd(ymdFromTs(startTs.value), days))
  }

  function syncDaysFromDue() {
    if (startTs.value == null || dueTs.value == null) return
    termDays.value = diffDays(ymdFromTs(startTs.value), ymdFromTs(dueTs.value))
  }

  const Picker = defineComponent({
    setup() {
      return () => {
        const term = Math.trunc(Number(termDays.value))
        const advance = Math.max(0, Math.trunc(Number(advanceDays.value)) || 0)
        const start = startTs.value == null ? '' : ymdFromTs(startTs.value)
        const due = dueTs.value == null ? '' : ymdFromTs(dueTs.value)
        const remind = due ? addDaysYmd(due, -advance) : ''
        return h('div', { class: 'flex flex-col gap-3 text-sm' }, [
          h('p', `选中 ${rows.length} 票。账期天数和收款截止日会互相换算。`),
          h('label', { class: 'flex flex-col gap-1' }, [
            '收款起算日',
            h(NDatePicker, {
              type: 'date',
              value: startTs.value,
              'onUpdate:value': (value: number | null) => {
                startTs.value = value
                syncDueFromDays()
              },
            }),
          ]),
          h('label', { class: 'flex flex-col gap-1' }, [
            '账期天数',
            h(NInputNumber, {
              value: termDays.value,
              min: 1,
              max: 3650,
              'onUpdate:value': (value: number | null) => {
                termDays.value = value ?? 1
                syncDueFromDays()
              },
            }),
          ]),
          h('label', { class: 'flex flex-col gap-1' }, [
            '收款截止日',
            h(NDatePicker, {
              type: 'date',
              value: dueTs.value,
              'onUpdate:value': (value: number | null) => {
                dueTs.value = value
                syncDaysFromDue()
              },
            }),
          ]),
          h('label', { class: 'flex flex-col gap-1' }, [
            '提前几天进入待催',
            h(NInputNumber, {
              value: advanceDays.value,
              min: 0,
              max: 365,
              'onUpdate:value': (value: number | null) => {
                advanceDays.value = value ?? 0
              },
            }),
          ]),
          h('p', due && start ? `应付款日 ${due}，${remind} 起进入待催` : '请选择收款起算日和截止日'),
        ])
      }
    },
  })
  dialog.create({
    title: '设置收款日',
    content: () => h(Picker),
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      if (startTs.value == null || dueTs.value == null) {
        message.warning('请选择收款起算日和截止日')
        return false
      }
      const term = diffDays(ymdFromTs(startTs.value), ymdFromTs(dueTs.value))
      const advance = Math.trunc(Number(advanceDays.value))
      if (!Number.isFinite(term) || term < 1 || term > 3650) {
        message.warning('截止日须晚于起算日，且不超过 3650 天')
        return false
      }
      if (!Number.isFinite(advance) || advance < 0 || advance > 365) {
        message.warning('提前提醒天数须在 0 到 365 天')
        return false
      }
      try {
        const res = await setPaymentCollectionTerm(
          rows.map((row) => row.shipmentId),
          ymdFromTs(startTs.value),
          term,
          advance,
        )
        message.success(`已设置 ${res.updated} 票收款日`)
        clearSelection()
        await reloadAfterMutation()
      } catch (e) {
        message.error(e instanceof Error ? e.message : '设置收款日失败')
        return false
      }
    },
  })
}

function handleBatchMarkPaid() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  dialog.warning({
    title: '批量标记已付款',
    content: `确认将选中的 ${rows.length} 条运单标记为已付款？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: () => markPaid(rows.map((r) => r.shipmentId)),
  })
}

async function openFollowupHistory(row: PaymentReminderItem) {
  followupShipment.value = row
  followupDrawerShow.value = true
  followupLoading.value = true
  try {
    const res = await listPaymentReminderFollowups(row.shipmentId)
    followupItems.value = res.items
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载跟进记录失败')
    followupItems.value = []
  } finally {
    followupLoading.value = false
  }
}

async function copySelectedShipmentNos() {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  try {
    await navigator.clipboard.writeText(nos.join('\n'))
    message.success(`已复制 ${nos.length} 个号码`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

async function handleSyncSelectedFromDps() {
  if (!selectedRows.value.length) {
    message.warning('请先勾选运单')
    return
  }
  const nos = selectedRealShipmentNos.value
  if (!nos.length) {
    message.warning('所选运单无有效运单号')
    return
  }
  syncingDps.value = true
  try {
    const res = await syncShipmentsFromDps(nos)
    if (res.skipped) {
      message.warning(res.reason || 'DPS 更新已跳过')
      return
    }
    if (res.error) {
      message.error(res.error)
      return
    }
    let text = `DPS 更新：新增 ${res.created}，更新 ${res.updated}`
    if (res.unchanged) text += `，无变化 ${res.unchanged}`
    if (res.failed) text += `，失败 ${res.failed}`
    if (res.notFound) text += `，DPS 未返回 ${res.notFound}`
    message.success(text)
    clearSelection()
    await reloadAfterMutation()
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'DPS 更新失败')
  } finally {
    syncingDps.value = false
  }
}

async function copyRowShipmentNo(row: PaymentReminderItem) {
  const sn = displayShipmentNo(row)
  if (!sn) return
  try {
    await navigator.clipboard.writeText(sn)
    message.success(isFclRow(row) ? '已复制提单号' : '已复制运单号')
  } catch {
    message.error('复制失败')
  }
}

function goShipmentList(row: PaymentReminderItem) {
  const shipmentNo = (row.shipmentNo || '').trim()
  if (!shipmentNo) return
  void router.push({
    path: shipmentListPathForStatus(row.statusCode),
    query: { shipmentNo },
  })
}

function formatTrackingTime(value: string | null | undefined): string {
  const text = (value || '').trim()
  if (!text) return '—'
  return formatAbsoluteDateTime(text) || text.slice(0, 16)
}

function shipmentStub(row: PaymentReminderItem): Shipment {
  return {
    id: row.shipmentId,
    shipmentNo: row.shipmentNo || '',
    customer: row.customer ?? null,
    channelCode: row.channelCode ?? null,
    channelNameZh: row.channelNameZh ?? null,
    statusCode: row.statusCode ?? null,
    latestTrackingTime: row.latestTrackingTime ?? null,
    latestTrackingDesc: row.latestTrackingDesc ?? null,
    trackingLogCount: 0,
    carrierLogCount: 0,
    createdTime: '',
    updatedTime: '',
  } as Shipment
}

async function openTrackingDrawer(row: PaymentReminderItem, tab: 'internal' | 'carrier' = 'internal') {
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
      latestTrackingTime: row.latestTrackingTime ?? null,
      latestTrackingDesc: row.latestTrackingDesc ?? '',
    }
  }
}

function renderTrackingCell(row: PaymentReminderItem) {
  const has = hasEffectiveInternalTracking(row)
  const time = formatTrackingTime(row.latestTrackingTime)
  const desc = (row.latestTrackingDesc || '').trim()
  const block = has
    ? h('div', { class: 'min-w-0 flex-1' }, [
        h('div', { class: 'payment-reminders-tracking-time text-xs tabular-nums leading-tight' }, time),
        h(
          'div',
          {
            class: 'payment-reminders-tracking-desc text-xs leading-snug truncate',
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
      class:
        'payment-reminders-tracking-btn w-full min-w-0 cursor-pointer rounded px-1 py-0.5 text-left transition-colors',
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

function renderStatusCell(row: PaymentReminderItem) {
  const { label, toneClass } = resolveShipmentListStatusDisplay({
    statusCode: row.statusCode,
    routeStatus: null,
    coarseStatusLabel: SHIPMENT_STATUS_LABEL_ZH,
  })
  return h('span', { class: ['shipment-status-badge', toneClass] }, label)
}

function formatReceivable(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '—'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function renderReceivable(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return h('span', { class: 'payment-receivable payment-receivable--empty' }, '—')
  }
  return h(
    'span',
    {
      class: [
        'payment-receivable',
        value >= LARGE_RECEIVABLE ? 'payment-receivable--large' : '',
      ],
    },
    formatReceivable(value),
  )
}

function renderSettlementBadge(row: PaymentReminderItem) {
  const key = (row.settlementMethod || '').trim().toUpperCase() || 'UNSET'
  const label = (row.settlementMethodLabel || '').trim() || settlementMethodLabel(row.settlementMethod)
  return h(
    'span',
    { class: ['settlement-badge', `settlement-badge--${key.toLowerCase()}`] },
    label,
  )
}

function renderPaymentStatusCell(row: PaymentReminderItem) {
  const code = (row.paymentStatus || '').trim().toUpperCase()
  const label = shipmentPaymentStatusLabel(row.paymentStatus)
  if (!code) return '—'
  const tone =
    code === 'PAID'
      ? 'shipment-status-badge--success'
      : code === 'UNPAID'
        ? 'shipment-status-badge--warning'
        : 'shipment-status-badge--default'
  return h('span', { class: ['shipment-status-badge', tone] }, label)
}

function reminderTagType(type: string): 'default' | 'info' | 'warning' | 'error' | 'success' {
  if (type === 'overdue') return 'error'
  if (type === 'today' || type === 'monthly') return 'warning'
  if (type === 'upcoming_7_days') return 'info'
  if (type === 'missing_rule' || type === 'missing_date') return 'default'
  return 'default'
}

function reminderDueSuffix(row: PaymentReminderItem): string {
  const hint = paymentReminderDueHint(row)
  return hint === '—' ? '' : hint
}

function renderReminderDueCell(row: PaymentReminderItem) {
  const rt = (row.reminderType || '').trim()
  if (!rt) return '—'
  const suffix = reminderDueSuffix(row)
  const dueHint = row.dueDate ? `应付 ${row.dueDate.slice(0, 10)}` : ''
  const title = [dueHint, suffix].filter(Boolean).join(' · ')
  return h(
    NTooltip,
    { disabled: !title },
    {
      trigger: () =>
        h('span', { class: 'inline-flex flex-wrap items-center gap-1' }, [
          h(
            NTag,
            { size: 'small', type: reminderTagType(rt), bordered: false },
            () => paymentReminderTypeLabel(rt),
          ),
          suffix
            ? h('span', { class: 'text-xs tabular-nums text-zinc-500 whitespace-nowrap' }, suffix)
            : null,
        ]),
      default: () => title || '—',
    },
  )
}

function followUpStatusLabel(row: PaymentReminderItem): string {
  const count = row.followupCount ?? 0
  if (count <= 0) return '未跟进'
  return `已跟进 · ${count}次`
}

function followUpTooltip(row: PaymentReminderItem): string | null {
  const count = row.followupCount ?? 0
  if (count <= 0 && !row.lastFollowupTime) return null
  const rel = row.lastFollowupTime ? formatRelativeTime(row.lastFollowupTime) : null
  const abs = rel?.absolute || row.lastFollowupTime || '—'
  const ago = rel?.relative || '刚刚'
  const note = (row.lastFollowupNote || '').trim()
  const lines = [`上次跟进：${abs}`, `${ago} · 共跟进 ${count || 1} 次`]
  if (note) lines.push(note)
  return lines.join('\n')
}

function renderFollowUpStatusCell(row: PaymentReminderItem) {
  const count = row.followupCount ?? 0
  const tag = h(
    NTag,
    {
      size: 'small',
      type: count > 0 ? 'info' : 'warning',
      bordered: false,
      class: count > 0 ? 'cursor-pointer' : undefined,
      onClick: count > 0 ? () => openFollowupHistory(row) : undefined,
    },
    () => followUpStatusLabel(row),
  )
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
  return tag
}

function renderShipmentNoCell(row: PaymentReminderItem) {
  const sn = displayShipmentNo(row) || '—'
  const copyLabel = isFclRow(row) ? '复制提单号' : '复制运单号'
  return h('span', { class: 'payment-reminders-shipment-no-cell' }, [
    h(
      'button',
      {
        type: 'button',
        class: 'text-left text-[var(--color-accent-text)] hover:underline shrink-0',
        onClick: () => goShipmentList(row),
      },
      sn,
    ),
    displayShipmentNo(row)
      ? h(
          NTooltip,
          { trigger: 'hover', showArrow: false },
          {
            trigger: () =>
              h(
                'button',
                {
                  type: 'button',
                  class: 'payment-reminders-shipment-no-copy-btn',
                  'aria-label': copyLabel,
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
            default: () => copyLabel,
          },
        )
      : null,
  ])
}

function renderCustomerCell(row: PaymentReminderItem) {
  const name = (row.customer || '').trim()
  if (!name) return '—'
  return h(
    'button',
    {
      type: 'button',
      class: 'payment-reminders-customer-link',
      title: '打开客户',
      onClick: () => {
        void router.push({ path: '/customers', query: { search: name } })
      },
    },
    name,
  )
}

const shipmentNoColWidth = computed(() => {
  let maxLen = 10
  for (const row of items.value) {
    maxLen = Math.max(maxLen, displayShipmentNo(row).length)
  }
  const textW = Math.ceil(maxLen * 7.5) + 21
  return Math.min(280, Math.max(148, textW + 26))
})

const columns = computed<DataTableColumns<PaymentReminderItem>>(() => [
  { type: 'selection', fixed: 'left', width: 40 },
  {
    title: '运单号',
    key: 'shipmentNo',
    width: shipmentNoColWidth.value,
    render: (row) => renderShipmentNoCell(row),
  },
  {
    title: '客户单号',
    key: 'customerNo',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => displayCustomerNo(row) || '—',
  },
  {
    title: '关联单号',
    key: 'refShipmentNo',
    width: 140,
    ellipsis: { tooltip: true },
    render: (row) => (row.refShipmentNo || '').trim() || '—',
  },
  { title: '客户', key: 'customer', width: 132, ellipsis: { tooltip: true }, render: (row) => renderCustomerCell(row) },
  {
    title: '渠道',
    key: 'channelCode',
    width: 120,
    render: (row) => row.channelNameZh || row.channelCode || '—',
  },
  {
    title: '状态',
    key: 'statusCode',
    width: 88,
    align: 'center',
    render: (row) => renderStatusCell(row),
  },
  {
    title: '轨迹',
    key: 'latestTracking',
    minWidth: 168,
    ellipsis: { tooltip: false },
    render: (row) => renderTrackingCell(row),
  },
  {
    title: '付款状态',
    key: 'paymentStatus',
    width: 88,
    align: 'center',
    render: (row) => renderPaymentStatusCell(row),
  },
  {
    title: '应收',
    key: 'receivableCny',
    width: 112,
    align: 'right',
    render: (row) => renderReceivable(row.receivableCny),
  },
  {
    title: '结算方式',
    key: 'settlementMethod',
    width: 116,
    render: (row) => renderSettlementBadge(row),
  },
  {
    title: '关键日期',
    key: 'baseDate',
    width: 108,
    render: (row) => (row.baseDate ? row.baseDate.slice(0, 10) : '—'),
  },
  { title: '应付款日', key: 'dueDate', width: 108, render: (row) => (row.dueDate ? row.dueDate.slice(0, 10) : '—') },
  {
    title: '催款状态',
    key: 'reminderDue',
    width: 148,
    render: (row) => renderReminderDueCell(row),
  },
  {
    title: '跟进状态',
    key: 'followupStatus',
    width: 108,
    render: (row) => renderFollowUpStatusCell(row),
  },
  {
    title: '操作',
    key: 'actions',
    width: 168,
    fixed: 'right',
    render: (row) =>
      h(NSpace, { size: 4 }, () => [
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: (row.followupCount ?? 0) > 0,
            type: (row.followupCount ?? 0) > 0 ? 'default' : 'warning',
            onClick: () => handleFollowup(row),
          },
          () => ((row.followupCount ?? 0) > 0 ? '再跟进' : '已跟进'),
        ),
        h(
          NButton,
          { size: 'tiny', quaternary: true, onClick: () => handleMarkPaid(row) },
          () => '已付款',
        ),
      ]),
  },
])

watch(
  [scope, filterCustomer, filterChannelCategory, filterSettlementMethod, filterReminderType, filterFollowupStatus, filterFclOnly, filterLargeAmount, filterReceivablePending, sortByReceivable],
  () => {
    page.value = 1
    clearSelection()
    void load()
    void loadSummary()
    void loadRanking()
  },
)

watch([page, pageSize], () => void load())

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void load(), 300)
})

watch(
  () => route.query.scope,
  () => {
    const before = scope.value
    applyRouteScope()
    if (scope.value !== before) {
      page.value = 1
      void load()
    }
  },
)

onMounted(() => {
  applyRouteScope()
  void loadFilterOptions()
  void load()
  void loadSummary()
  void loadRanking()
})
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-4">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3">
      <div class="min-w-0">
        <h1 class="page-h2">催款管理</h1>
        <div class="payment-summary-bar mt-1.5">
          <span class="payment-summary-bar__item">
            <span class="payment-summary-bar__dot payment-summary-bar__dot--todo" aria-hidden="true" />
            <span class="payment-summary-bar__label">待催</span>
            <span class="payment-summary-bar__count">{{ todoCount }}</span>
          </span>
          <span class="payment-summary-bar__item">
            <span class="payment-summary-bar__dot payment-summary-bar__dot--unpaid" aria-hidden="true" />
            <span class="payment-summary-bar__label">全部未付款</span>
            <span class="payment-summary-bar__count">{{ allUnpaidCount }}</span>
          </span>
          <span class="payment-summary-bar__item">
            <span class="payment-summary-bar__dot payment-summary-bar__dot--overdue" aria-hidden="true" />
            <span class="payment-summary-bar__label">逾期</span>
            <span class="payment-summary-bar__count">{{ overdueCount }}</span>
          </span>
          <span class="payment-summary-bar__divider" aria-hidden="true" />
          <span class="payment-summary-bar__total">当前列表 {{ total }} 条</span>
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <NButton size="small" :loading="loading" @click="reloadAfterMutation">刷新</NButton>
        <NButton size="small" :loading="exporting" :disabled="total <= 0" @click="handleExport">
          导出
        </NButton>
      </div>
    </div>

    <div class="payment-reminders-filters panel shrink-0 px-3 py-2">
      <div class="payment-reminders-filters__row scrollbar-subtle">
        <NRadioGroup
          :value="scope"
          size="small"
          class="payment-reminders-scope-tabs shrink-0"
          @update:value="onScopeTabChange"
        >
          <NRadioButton value="todo" title="不含月结；月结请用「全部未付款」或结算方式筛选">
            待催
          </NRadioButton>
          <NRadioButton value="all_unpaid">全部未付款</NRadioButton>
        </NRadioGroup>
        <NSelect
          v-model:value="filterCustomer"
          :options="customerOptions"
          clearable
          filterable
          placeholder="客户"
          class="payment-reminders-filter-select"
          size="small"
        />
        <NSelect
          v-model:value="filterChannelCategory"
          :options="channelCategoryOptions"
          clearable
          filterable
          placeholder="渠道大类"
          class="payment-reminders-filter-select"
          size="small"
        />
        <NSelect
          v-model:value="filterSettlementMethod"
          :options="[...SETTLEMENT_METHOD_FILTER_OPTIONS]"
          clearable
          placeholder="结算方式"
          class="payment-reminders-filter-select payment-reminders-filter-select--wide"
          size="small"
        />
        <NSelect
          v-model:value="filterReminderType"
          :options="[...PAYMENT_REMINDER_TYPE_OPTIONS]"
          clearable
          placeholder="提醒类型"
          class="payment-reminders-filter-select payment-reminders-filter-select--wide"
          size="small"
        />
        <NSelect
          v-model:value="filterFollowupStatus"
          :options="[...PAYMENT_FOLLOWUP_STATUS_OPTIONS]"
          clearable
          placeholder="跟进状态"
          class="payment-reminders-filter-select"
          size="small"
        />
        <NInput
          v-model:value="search"
          clearable
          placeholder="运单号 / 客户单号 / 关联单号 / 货件号"
          class="payment-reminders-filter-search"
          size="small"
        />
        <NCheckbox v-model:checked="filterFclOnly" size="small" class="shrink-0">
          整柜
        </NCheckbox>
        <NCheckbox v-model:checked="filterLargeAmount" size="small" class="shrink-0">
          1万以上
        </NCheckbox>
        <NCheckbox v-model:checked="filterReceivablePending" size="small" class="shrink-0">
          应收待更新
        </NCheckbox>
        <NCheckbox v-model:checked="sortByReceivable" size="small" class="shrink-0">
          按应收
        </NCheckbox>
      </div>
    </div>

    <section class="payment-rank panel shrink-0 px-3 py-2">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="text-sm font-semibold">客户欠款</h2>
        <div class="flex items-center gap-2">
          <span v-if="rankExpanded" class="text-sm">
            合计欠款
            <strong class="payment-rank__money">{{ formatReceivable(rankTotal) }}</strong>
          </span>
          <NButton
            v-if="rankExpanded && customerRanks.length > 10"
            size="tiny"
            quaternary
            @click="rankShowAll = !rankShowAll"
          >
            {{ rankShowAll ? '只看前十' : '展开全部' }}
          </NButton>
          <NButton size="tiny" quaternary @click="toggleRankPanel">
            {{ rankExpanded ? '收起' : '展开' }}
          </NButton>
        </div>
      </div>
      <div v-show="rankExpanded">
        <div class="mt-2 flex items-center gap-3 text-xs text-[var(--color-muted)]">
          <span class="payment-rank__legend payment-rank__legend--overdue">已逾期</span>
          <span class="payment-rank__legend payment-rank__legend--open">未逾期</span>
        </div>
        <p v-if="receivablePendingCount" class="mt-1 text-xs text-[var(--color-muted)]">
          {{ receivablePendingCount }} 票未记应收或应收不大于 0，未计入排名
        </p>
        <p v-if="!visibleRanks.length" class="mt-2 text-sm text-[var(--color-muted)]">暂无可排名的应收</p>
        <ol v-else class="payment-rank__list mt-2 space-y-1">
          <li v-for="row in visibleRanks" :key="row.customer">
            <button
              type="button"
              class="payment-rank__row"
              :class="{ 'payment-rank__row--active': filterCustomer === row.customer }"
              @click="toggleRankCustomer(row.customer)"
            >
              <span class="payment-rank__name" :title="row.customer">{{ row.customer }}</span>
              <span class="payment-rank__bar">
                <span
                  class="payment-rank__overdue"
                  :style="{ width: rankWidth(row.overdue) }"
                />
                <span
                  class="payment-rank__open"
                  :style="{ width: rankWidth(row.open) }"
                />
              </span>
              <span class="payment-rank__money">{{ formatReceivable(row.total) }}</span>
            </button>
          </li>
        </ol>
      </div>
    </section>

    <div class="min-h-0 flex-1 overflow-hidden rounded-lg border border-[var(--color-border)]">
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :row-key="rowKey"
        :columns="columns"
        :data="items"
        :loading="loading"
        :bordered="false"
        flex-height
        class="payment-reminders-table h-full"
        size="small"
        :scroll-x="1900"
      />
    </div>

    <div
      v-if="selectedCount > 0"
      class="payment-reminders-selection-bar shrink-0 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="payment-reminders-selection-bar__label text-sm">
          已选
          <strong class="payment-reminders-selection-bar__count">{{ selectedCount }}</strong>
          条（本页）
          <template v-if="selectedWithReceivable">
            ，应收合计
            <strong class="payment-reminders-selection-bar__money">{{ formatReceivable(selectedReceivableTotal) }}</strong>
          </template>
          <template v-if="selectedMissingReceivable">
            ，{{ selectedMissingReceivable }} 票未记应收
          </template>
        </span>
        <NButton size="small" quaternary @click="clearSelection">取消选择</NButton>
      </div>
      <NSpace size="small">
        <NButton size="small" @click="openCollectionTermDialog">设置收款日</NButton>
        <NButton size="small" title="复制选中运单号（换行）" @click="copySelectedShipmentNos">
          复制运单号
        </NButton>
        <NButton
          size="small"
          :loading="syncingDps"
          title="从 DPS shipment_queryByOrder 拉取并更新选中运单"
          @click="handleSyncSelectedFromDps"
        >
          更新选中运单
        </NButton>
        <NButton
          size="small"
          type="warning"
          :loading="batchSubmitting"
          @click="handleBatchFollowup"
        >
          已跟进
        </NButton>
        <NButton size="small" type="primary" :loading="batchSubmitting" @click="handleBatchMarkPaid">
          标记已付款
        </NButton>
      </NSpace>
    </div>

    <ShipmentTrackingDrawer
      v-model:show="trackingDrawerShow"
      :shipment="trackingDrawerShipment"
      :initial-tab="trackingDrawerTab"
      @shipment-updated="handleTrackingDrawerShipmentUpdated"
    />

    <NDrawer v-model:show="followupDrawerShow" :width="420" placement="right">
      <NDrawerContent
        :title="followupShipment ? `跟进记录 · ${followupShipment.shipmentNo}` : '跟进记录'"
        closable
      >
        <div v-if="followupLoading" class="text-sm text-zinc-500">加载中…</div>
        <div v-else-if="!followupItems.length" class="text-sm text-zinc-500">暂无跟进记录</div>
        <ul v-else class="space-y-4">
          <li
            v-for="item in followupItems"
            :key="item.id"
            class="rounded-md border border-[var(--color-border)] p-3 text-sm"
          >
            <p class="text-xs text-zinc-500">
              {{ formatAbsoluteDateTime(item.followupTime) }}
              <span v-if="item.reminderType"> · {{ paymentReminderTypeLabel(item.reminderType) }}</span>
            </p>
            <p v-if="item.note" class="mt-2 whitespace-pre-wrap">{{ item.note }}</p>
            <p v-else class="mt-2 text-zinc-500">（无备注）</p>
          </li>
        </ul>
      </NDrawerContent>
    </NDrawer>

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
.payment-summary-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem 1.25rem;
  font-size: 0.8125rem;
  line-height: 1.25rem;
  color: var(--color-fg);
}

.payment-summary-bar__item {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.payment-summary-bar__dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 9999px;
  flex-shrink: 0;
}

.payment-summary-bar__dot--todo {
  background: #e02020;
}

.payment-summary-bar__dot--unpaid {
  background: #f7b500;
}

.payment-summary-bar__dot--overdue {
  background: #fa6400;
}

.payment-summary-bar__label {
  color: var(--color-fg-secondary, #52525b);
}

.payment-summary-bar__count {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis, #18181b);
}

.payment-summary-bar__divider {
  width: 1px;
  height: 0.875rem;
  background: var(--color-border, #e4e4e7);
  flex-shrink: 0;
}

.payment-summary-bar__total {
  color: #999999;
  font-variant-numeric: tabular-nums;
}

.payment-reminders-scope-tabs {
  flex-shrink: 0;
}

.payment-reminders-selection-bar {
  border: 1px solid color-mix(in srgb, var(--color-accent-text) 28%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent-text) 6%, transparent);
}

.payment-reminders-selection-bar__label {
  color: var(--color-muted);
}

.payment-reminders-selection-bar__count {
  color: var(--color-text);
}

.payment-reminders-selection-bar__money {
  color: rgb(180 83 9);
  font-variant-numeric: tabular-nums;
}

.payment-reminders-table :deep(.payment-receivable) {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.payment-reminders-table :deep(.payment-receivable--large) {
  color: rgb(180 83 9);
}

.payment-reminders-table :deep(.payment-receivable--empty) {
  font-weight: 400;
  color: var(--color-muted);
}

[data-theme='dark'] .payment-reminders-selection-bar__money,
[data-theme='dark'] .payment-reminders-table :deep(.payment-receivable--large) {
  color: rgb(253 230 138);
}

.payment-reminders-table :deep(.payment-reminders-customer-link) {
  max-width: 100%;
  overflow: hidden;
  border: none;
  background: transparent;
  padding: 0;
  color: var(--color-accent-text);
  font: inherit;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.payment-reminders-table :deep(.payment-reminders-customer-link:hover) {
  text-decoration: underline;
}

.payment-reminders-table :deep(.settlement-badge) {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 650;
  line-height: 20px;
  white-space: nowrap;
}

.payment-reminders-table :deep(.settlement-badge--before_shipment) {
  background: rgb(245 158 11 / 0.18);
  color: rgb(146 64 14);
}

.payment-reminders-table :deep(.settlement-badge--before_arrival) {
  background: rgb(14 165 233 / 0.16);
  color: rgb(3 105 161);
}

.payment-reminders-table :deep(.settlement-badge--after_arrival) {
  background: rgb(139 92 246 / 0.16);
  color: rgb(91 33 182);
}

.payment-reminders-table :deep(.settlement-badge--monthly) {
  background: rgb(113 113 122 / 0.16);
  color: rgb(63 63 70);
}

.payment-reminders-table :deep(.settlement-badge--after_delivery) {
  background: rgb(34 197 94 / 0.16);
  color: rgb(21 128 61);
}

.payment-reminders-table :deep(.settlement-badge--within_days) {
  background: rgb(244 63 94 / 0.16);
  color: rgb(190 18 60);
}

.payment-reminders-table :deep(.settlement-badge--unset) {
  background: transparent;
  color: var(--color-muted);
  box-shadow: inset 0 0 0 1px var(--color-border);
}

[data-theme='dark'] .payment-reminders-table :deep(.settlement-badge--before_shipment) {
  color: rgb(253 230 138);
}

[data-theme='dark'] .payment-reminders-table :deep(.settlement-badge--before_arrival) {
  color: rgb(125 211 252);
}

[data-theme='dark'] .payment-reminders-table :deep(.settlement-badge--after_arrival) {
  color: rgb(196 181 253);
}

[data-theme='dark'] .payment-reminders-table :deep(.settlement-badge--monthly) {
  color: rgb(212 212 216);
}

[data-theme='dark'] .payment-reminders-table :deep(.settlement-badge--within_days) {
  color: rgb(253 164 175);
}

[data-theme='dark'] .payment-reminders-table :deep(.settlement-badge--after_delivery) {
  color: rgb(134 239 172);
}

.payment-reminders-filters {
  min-width: 0;
}

.payment-rank__row {
  display: grid;
  width: 100%;
  grid-template-columns: 8rem minmax(0, 1fr) 6.5rem;
  align-items: center;
  gap: 0.5rem;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  padding: 0.15rem 0.25rem;
  text-align: left;
  cursor: pointer;
}

.payment-rank__row:hover,
.payment-rank__row--active {
  background: rgb(139 92 246 / 0.08);
}

.payment-rank__name {
  overflow: hidden;
  font-size: 0.75rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.payment-rank__list {
  max-height: 16rem;
  overflow: auto;
}

.payment-rank__bar {
  display: flex;
  height: 0.55rem;
  overflow: hidden;
  border-radius: 999px;
}

.payment-rank__overdue,
.payment-rank__open {
  height: 100%;
}

.payment-rank__overdue {
  background: rgb(244 63 94);
}

.payment-rank__open {
  background: rgb(14 165 233);
}

.payment-rank__money {
  font-size: 0.75rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.payment-rank__legend::before {
  content: '';
  display: inline-block;
  width: 0.55rem;
  height: 0.55rem;
  margin-right: 0.25rem;
  border-radius: 999px;
  vertical-align: -1px;
}

.payment-rank__legend--overdue::before {
  background: rgb(244 63 94);
}

.payment-rank__legend--open::before {
  background: rgb(14 165 233);
}

.payment-reminders-filters__row {
  display: flex;
  min-width: 0;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0.5rem;
  overflow-x: auto;
  overflow-y: hidden;
}

.payment-reminders-filters__row > * {
  flex: 0 0 auto;
}

.payment-reminders-filter-select {
  width: 7.25rem;
  min-width: 6.5rem;
}

.payment-reminders-filter-select--wide {
  width: 10.5rem;
  min-width: 9rem;
}

.payment-reminders-filter-search {
  width: 11rem;
  min-width: 9rem;
}

.payment-reminders-tracking-btn:hover {
  background: color-mix(in srgb, var(--color-accent-text) 8%, transparent);
}

.payment-reminders-tracking-time {
  color: var(--color-muted);
}

.payment-reminders-tracking-desc {
  color: var(--color-text);
}

.payment-reminders-table :deep(.shipment-status-badge) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.5rem;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 11px;
  font-weight: 500;
  line-height: 1.25;
  white-space: nowrap;
}

.payment-reminders-table :deep(.shipment-status-badge--default) {
  color: var(--tag-default-fg);
  background: var(--tag-default-bg);
}

.payment-reminders-table :deep(.shipment-status-badge--warning) {
  color: var(--tag-warning-fg);
  background: var(--tag-warning-bg);
}

.payment-reminders-table :deep(.shipment-status-badge--success) {
  color: var(--tag-success-fg);
  background: var(--tag-success-bg);
}

.payment-reminders-table :deep(.shipment-status-badge--indigo) {
  color: var(--tag-indigo-fg);
  background: var(--tag-indigo-bg);
}

.payment-reminders-table :deep(.payment-reminders-shipment-no-cell) {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
  flex-shrink: 0;
  white-space: nowrap;
}

.payment-reminders-table :deep(.payment-reminders-shipment-no-copy-btn) {
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

.payment-reminders-table :deep(.n-data-table-tr:hover .payment-reminders-shipment-no-copy-btn),
.payment-reminders-table :deep(.payment-reminders-shipment-no-copy-btn:focus-visible) {
  opacity: 1;
}

.payment-reminders-table :deep(.payment-reminders-shipment-no-copy-btn:hover) {
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg);
}
</style>
