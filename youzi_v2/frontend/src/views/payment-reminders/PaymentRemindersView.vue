<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
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
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import {
  batchCreatePaymentReminderFollowups,
  createPaymentReminderFollowup,
  exportPaymentRemindersExcel,
  getPaymentReminderSummary,
  listPaymentReminderFollowups,
  listPaymentReminders,
  type PaymentReminderFollowup,
  type PaymentReminderItem,
  type PaymentReminderScope,
} from '@/api/paymentReminders'
import { batchUpdateShipments, getShipment, getShipmentFilterOptions } from '@/api/shipments'
import {
  PAYMENT_FOLLOWUP_STATUS_OPTIONS,
  PAYMENT_REMINDER_TYPE_OPTIONS,
  SETTLEMENT_METHOD_FILTER_OPTIONS,
  paymentReminderDueHint,
  paymentReminderTypeLabel,
  settlementMethodLabel,
} from '@/constants/paymentReminders'
import { ICON_STROKE } from '@/constants/icons'
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
const items = ref<PaymentReminderItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const checkedRowKeys = ref<string[]>([])
const todoCount = ref(0)
const allUnpaidCount = ref(0)
const overdueCount = ref(0)

const scope = ref<PaymentReminderScope>('todo')
const filterCustomer = ref<string | null>(null)
const filterSettlementMethod = ref<string | null>(null)
const filterReminderType = ref<string | null>(null)
const filterFollowupStatus = ref<'unfollowed' | 'followed' | null>(null)
const search = ref('')

const customerOptions = ref<{ label: string; value: string }[]>([])

const followupDrawerShow = ref(false)
const followupLoading = ref(false)
const followupShipment = ref<PaymentReminderItem | null>(null)
const followupItems = ref<PaymentReminderFollowup[]>([])

const trackingDrawerShow = ref(false)
const trackingDrawerShipment = ref<Shipment | null>(null)
const trackingDrawerTab = ref<'internal' | 'carrier'>('internal')

const SHIPMENT_STATUS_LABEL: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

const selectedRows = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.shipmentId)),
)
const selectedCount = computed(() => selectedRows.value.length)
const selectedShipmentNos = computed(() =>
  selectedRows.value.map((r) => displayShipmentNo(r)).filter(Boolean),
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

async function load() {
  loading.value = true
  try {
    const res = await listPaymentReminders({
      scope: scope.value,
      customer: filterCustomer.value || undefined,
      settlementMethod: filterSettlementMethod.value || undefined,
      reminderType: filterReminderType.value || undefined,
      followupStatus: filterFollowupStatus.value || undefined,
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

async function loadSummary() {
  try {
    const summary = await getPaymentReminderSummary()
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
    const blob = await exportPaymentRemindersExcel({
      scope: scope.value,
      customer: filterCustomer.value || undefined,
      settlementMethod: filterSettlementMethod.value || undefined,
      reminderType: filterReminderType.value || undefined,
      followupStatus: filterFollowupStatus.value || undefined,
      search: search.value.trim() || undefined,
      limit: Math.min(total.value || 10_000, 10_000),
      offset: 0,
    })
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

function goShipmentList(shipmentNo: string) {
  void router.push({ path: '/shipments', query: { shipmentNo } })
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
  const code = (row.statusCode || 'UNKNOWN').trim().toUpperCase()
  const label = SHIPMENT_STATUS_LABEL[code] || code
  const tone =
    code === 'DELIVERED'
      ? 'shipment-status-badge--success'
      : code === 'INSPECTION' || code === 'IN_TRANSIT'
        ? 'shipment-status-badge--warning'
        : 'shipment-status-badge--default'
  return h('span', { class: ['shipment-status-badge', tone] }, label)
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
        onClick: () => goShipmentList(row.shipmentNo),
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
  { title: '客户', key: 'customer', width: 132, ellipsis: { tooltip: true } },
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
    title: '结算方式',
    key: 'settlementMethod',
    width: 108,
    render: (row) => settlementMethodLabel(row.settlementMethod),
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

watch([scope, filterCustomer, filterSettlementMethod, filterReminderType, filterFollowupStatus], () => {
  page.value = 1
  clearSelection()
  void load()
})

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
})
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-4">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="page-h2">催款管理</h1>
        <p class="page-subtitle mt-1">
          待催 {{ todoCount }} 条 · 全部未付款 {{ allUnpaidCount }} 条
          <span v-if="overdueCount > 0"> · 逾期 {{ overdueCount }} 条</span>
          · 当前列表 {{ total }} 条
        </p>
      </div>
      <NButton size="small" :loading="exporting" :disabled="total <= 0" @click="handleExport">
        导出
      </NButton>
    </div>

    <div class="payment-reminders-filters panel shrink-0 px-3 py-2">
      <div class="payment-reminders-filters__row scrollbar-subtle">
        <NRadioGroup
          :value="scope"
          size="small"
          class="payment-reminders-scope-tabs shrink-0"
          @update:value="onScopeTabChange"
        >
          <NRadioButton value="todo">待催</NRadioButton>
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
          placeholder="运单号 / 客户单号 / 货件号"
          class="payment-reminders-filter-search"
          size="small"
        />
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
        class="payment-reminders-table h-full"
        size="small"
        :scroll-x="1648"
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

.payment-reminders-filters {
  min-width: 0;
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
