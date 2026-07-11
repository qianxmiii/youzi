<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDataTable,
  NDatePicker,
  NDropdown,
  NInput,
  NPagination,
  NPopconfirm,
  NSelect,
  NSpace,
  NTooltip,
  useDialog,
  useMessage,
  type DataTableColumns,
  type DataTableSortState,
  type DropdownOption,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { formatGroupNoDisplay } from '@/utils/shipmentGroup'
import { useRoute, useRouter } from 'vue-router'
import ShipmentGroupRuleIcon from '@/components/shipments/ShipmentGroupRuleIcon.vue'
import ShipmentGroupActionModal from '@/components/shipments/ShipmentGroupActionModal.vue'
import ShipmentGroupSuggestionsModal from '@/components/shipments/ShipmentGroupSuggestionsModal.vue'
import ShipmentExceptionCloseModal from '@/components/shipments/ShipmentExceptionCloseModal.vue'
import ShipmentExceptionOpenModal from '@/components/shipments/ShipmentExceptionOpenModal.vue'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import ShipmentTrackingFreshnessBar from '@/components/shipments/ShipmentTrackingFreshnessBar.vue'
import ShipmentFilterSummaryBar from '@/components/shipments/ShipmentFilterSummaryBar.vue'
import ShipmentAdvancedFilterDrawer from '@/components/shipments/ShipmentAdvancedFilterDrawer.vue'
import ShipmentColumnSettingsDrawer from '@/components/shipments/ShipmentColumnSettingsDrawer.vue'
import ShipmentBatchEditModal from '@/components/shipments/ShipmentBatchEditModal.vue'
import TableActionIcon from '@/components/common/TableActionIcon.vue'
import VipStarBadge from '@/components/common/VipStarBadge.vue'
import LastMileBadge from '@/components/common/LastMileBadge.vue'
import ExceptionStatusBadge from '@/components/common/ExceptionStatusBadge.vue'
import { usePendingTrackingTimeReviewCount } from '@/composables/usePendingTrackingTimeReviewCount'
import {
  batchDeleteShipments,
  batchUpdateShipments,
  closeShipmentExceptions,
  createShipment,
  deleteShipment,
  exportShipmentsExcel,
  getShipment,
  getShipmentFilterOptions,
  getTrackingFreshnessStats,
  getTrackingSyncDailyStats,
  importShipmentsExcel,
  listShipments,
  openShipmentExceptions,
  batchSubscribeShipments,
  batchUnsubscribeShipments,
  subscribeShipment,
  syncCarrierTracking,
  syncShipmentsFromDps,
  syncTracking,
  unsubscribeShipment,
  updateShipment,
  type ShipmentFilterOptions,
} from '@/api/shipments'
import type { TrackingSyncDailyStats } from '@/types/tracking'
import {
  addShipmentGroupMembers,
  createShipmentGroup,
  removeShipmentGroupMembers,
} from '@/api/shipmentGroups'
import ShipmentFormModal from '@/components/shipments/ShipmentFormModal.vue'
import type { Shipment, ShipmentBatchResult, ShipmentPayload } from '@/types/shipment'
import type { ShipmentGroupBatchMode, ShipmentGroupFilterOption, ShipmentGroupRuleInput } from '@/types/shipmentGroup'
import { Layers } from 'lucide-vue-next'
import { shipmentGroupRuleSelectOptions, sortShipmentGroupEnabledRules } from '@/constants/shipmentGroupRules'
import { ICON_STROKE } from '@/constants/icons'
import { CARRIER_FILTER_EMPTY } from '@/constants/shipmentFilters'
import {
  DEFAULT_SHIPMENT_VISIBLE_COLUMNS,
  SHIPMENT_COLUMN_STORAGE_KEY,
  SHIPMENT_SYSTEM_VIEWS,
  SHIPMENT_TIME_FIELD_OPTIONS,
  emptyAdvancedTimeRanges,
  systemViewFilters,
  type ShipmentSystemViewId,
  type ShipmentTimeField,
} from '@/constants/shipmentListFilterMeta'
import { buildCarrierSelectOptions } from '@/utils/carrierFilterOptions'
import { buildChannelSelectOptions, channelFilterLabel } from '@/utils/channelFilterOptions'
import {
  buildShipmentFilterQuery,
  buildShipmentFilterSummaryTags,
  type ShipmentFilterQueryInput,
} from '@/utils/shipmentListFilterQuery'
import { useDictLabels } from '@/composables/useDictLabels'
import { formatRelativeTime } from '@/utils/formatDateTime'
import { shipmentPaymentStatusLabel } from '@/utils/formatGroupAlertMessage'
import { parseBatchSearchTokens } from '@/utils/parseBatchSearch'
import { hasEffectiveInternalTracking } from '@/utils/internalTracking'
import { formatShipmentDetailSummaryCopyText, formatShipmentDetailSummaryWithCustomerNoCopyText } from '@/utils/shipmentCopyFormat'
import { formatLastMileTooltip, resolveLastMileTracking } from '@/utils/lastMileTracking'
import {
  daysSinceLocalCalendar,
  FRESHNESS_DOT_CLASS,
  FRESHNESS_LABEL,
  isCarrierTrackingNewerThanInternal,
  trackingFreshnessLevel,
  type TrackingFreshnessBucket,
  type TrackingFreshnessStats,
} from '@/utils/trackingFreshness'
import { notifyTrackingSyncResult } from '@/utils/trackingSyncNotify'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const { loadDictTypes, dictLabel } = useDictLabels()
const countryLabel = (raw: string | null | undefined) => dictLabel('country_code', raw)
const loading = ref(false)
const importing = ref(false)
const exporting = ref(false)
const syncingTracking = ref(false)
const syncingCarrier = ref(false)
const syncingDps = ref(false)
const carrierDaily = ref<TrackingSyncDailyStats | null>(null)
const freshnessStats = ref<TrackingFreshnessStats | null>(null)
const filterNoInternalTracking = ref(false)
const filterNoCarrierTracking = ref(false)
const filterCarrierAheadOfInternal = ref(false)
const filterPendingTrackingTimeReview = ref(false)
const { refreshPendingTrackingTimeReviewCount } = usePendingTrackingTimeReviewCount()
const items = ref<Shipment[]>([])
const total = ref(0)
const searchShipmentNo = ref('')
const searchKeyword = ref('')
const searchTrackingContent = ref('')
const advExactShipmentNo = ref('')
const advContainerNos = ref('')
const advBillNos = ref('')
const advCustomerShipmentIds = ref('')
const DEFAULT_STATUS_FILTER = 'IN_TRANSIT'
const filterStatus = ref<string | null>(DEFAULT_STATUS_FILTER)
const filterCustomer = ref<string | null>(null)
const filterChannelCode = ref<string | null>(null)
const timeField = ref<ShipmentTimeField | null>(null)
const timeRange = ref<[number, number] | null>(null)
const filterVipOnly = ref(false)
const filterFclOnly = ref(false)
const filterCarrier = ref<string | null>(null)
const filterCountry = ref<string | null>(null)
const filterChannelNameZh = ref<string | null>(null)
const filterChannelCategory = ref<string | null>(null)
const filterCustomerNo = ref('')
const filterDestinationPort = ref<string | null>(null)
const filterAddressKeyword = ref<string | null>(null)
const filterVesselVoyage = ref<string | null>(null)
const filterStaleDays = ref<number | null>(null)
const filterNoZipcode = ref(false)
const filterHasTrackingNumber = ref(false)
const filterException = ref<string | null>(null)
const filterPaymentStatus = ref<string | null>(null)
const filterHasException = ref<boolean | null>(null)
const filterGroupId = ref<string | null>(null)
const filterGroupNo = ref<string | null>(null)
const filterRuleType = ref<string | null>(null)
const filterHasGroup = ref<boolean | null>(null)
const missingEtd = ref(false)
const missingAtd = ref(false)
const missingEta = ref(false)
const missingAta = ref(false)
const missingExpectedDelivery = ref(false)
const missingDelivered = ref(false)
const notDelivered = ref(false)
const hasAta = ref(false)
const deliveryRisk = ref<string | null>(null)
const advancedTimes = ref(emptyAdvancedTimeRanges())
const advancedFilterShow = ref(false)
const columnSettingsShow = ref(false)
const selectedSystemView = ref<ShipmentSystemViewId | null>(null)

function loadVisibleColumnKeys(): string[] {
  try {
    const raw = localStorage.getItem(SHIPMENT_COLUMN_STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as unknown
      if (Array.isArray(parsed) && parsed.every((x) => typeof x === 'string')) {
        return parsed.filter((key) => key !== 'statusCode')
      }
    }
  } catch {
    /* ignore */
  }
  return [...DEFAULT_SHIPMENT_VISIBLE_COLUMNS]
}

const visibleColumnKeys = ref<string[]>(loadVisibleColumnKeys())
const filterOptions = ref<ShipmentFilterOptions>({
  customers: [],
  carrierCodes: [],
  carriers: [],
  countryCodes: [],
  channelCodes: [],
  channels: [],
  channelNameZhs: [],
  channelCategories: [],
  statusCodes: [],
  exceptionCodes: [],
  exceptionTypes: [],
  groups: [],
})
const exceptionOpenShow = ref(false)
const exceptionCloseShow = ref(false)
const exceptionSubmitting = ref(false)
const batchEditShow = ref(false)
const batchSubmitting = ref(false)
const groupActionShow = ref(false)
const groupSuggestionsShow = ref(false)
const groupActionMode = ref<ShipmentGroupBatchMode>('create')
const groupActionSubmitting = ref(false)
const subscriptionTogglingId = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(20)
const sortBy = ref<'shipmentNo' | null>(null)
const sortOrder = ref<'asc' | 'desc' | null>(null)
const trackingDrawerShow = ref(false)
const trackingDrawerShipment = ref<Shipment | null>(null)
const trackingDrawerTab = ref<'internal' | 'carrier'>('internal')

const modalShow = ref(false)
const modalMode = ref<'create' | 'edit'>('edit')
const editingRow = ref<Shipment | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const checkedRowKeys = ref<string[]>([])

const selectedCount = computed(() => selectedRows.value.length)

function syncSelectionWithItems() {
  const visible = new Set(items.value.map((row) => row.id))
  checkedRowKeys.value = checkedRowKeys.value.filter((id) => visible.has(id))
}

const shipmentNoTokens = computed(() => parseBatchSearchTokens(searchShipmentNo.value))
const batchShipmentSearchActive = computed(() => shipmentNoTokens.value.length > 1)

/** 按当前页最长运单号 + 侧栏标识（异常等）估算列宽 */
const shipmentNoColWidth = computed(() => {
  let maxLen = 10
  let maxBadges = 0
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.shipmentNo || '').length)
    let badges = 0
    if (hasActiveException(row)) badges++
    maxBadges = Math.max(maxBadges, badges)
  }
  const textW = Math.ceil(maxLen * 7.5) + 21
  const badgeW = maxBadges > 0 ? 8 + maxBadges * 22 : 0
  return Math.min(385, Math.max(193, textW + badgeW))
})

/** 按当前页最长客户名估算列宽 */
const customerColWidth = computed(() => {
  let maxLen = 4
  for (const row of items.value) {
    maxLen = Math.max(maxLen, (row.customer || '').length)
  }
  return Math.min(220, Math.max(120, Math.ceil(maxLen * 7) + 28))
})

const selectedShipmentNos = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)).map((row) => row.shipmentNo),
)

const selectedRows = computed(() =>
  items.value.filter((row) => checkedRowKeys.value.includes(row.id)),
)

const selectedIds = computed(() => selectedRows.value.map((row) => row.id))

const selectedMemberGroupOptions = computed((): ShipmentGroupFilterOption[] => {
  const map = new Map<string, ShipmentGroupFilterOption>()
  for (const row of selectedRows.value) {
    for (const g of row.groups ?? []) {
      if (!map.has(g.groupId)) {
        map.set(g.groupId, {
          id: g.groupId,
          groupNo: g.groupNo,
          groupName: g.groupName,
        })
      }
    }
  }
  return [...map.values()].sort((a, b) => a.groupNo.localeCompare(b.groupNo))
})

const groupFilterOptions = computed(() =>
  filterOptions.value.groups.map((g) => {
    const no = formatGroupNoDisplay(g.groupNo)
    return {
      label: g.groupName?.trim() ? `${g.groupName}（${no}）` : no,
      value: g.id,
    }
  }),
)
const ruleTypeFilterOptions = shipmentGroupRuleSelectOptions()

const hasGroupFilterOptions = [
  { label: '有分组', value: 'yes' },
  { label: '无分组', value: 'no' },
]

function goShipmentGroup(groupId: string) {
  if (!groupId?.trim()) return
  void router.push({ path: '/shipment-groups', query: { groupId: groupId.trim() } })
}

function renderGroupIconButton(
  g: NonNullable<Shipment['groups']>[number],
  child: ReturnType<typeof h>,
) {
  const groupNo = formatGroupNoDisplay(g.groupNo)
  return h(
    NTooltip,
    { placement: 'top' },
    {
      trigger: () =>
        h(
          'button',
          {
            type: 'button',
            class: 'shipment-group-rule-icon-btn',
            onClick: (e: MouseEvent) => {
              e.stopPropagation()
              goShipmentGroup(g.groupId)
            },
          },
          [child],
        ),
      default: () => groupNo,
    },
  )
}

function renderGroupIconCluster(g: NonNullable<Shipment['groups']>[number]) {
  const rules = sortShipmentGroupEnabledRules(g.enabledRules ?? [])
  if (!rules.length) {
    return renderGroupIconButton(
      g,
      h(Layers, {
        class: 'shipment-group-rule-icon__svg shipment-group-rule-icon--placeholder',
        size: 14,
        strokeWidth: ICON_STROKE,
      }),
    )
  }
  return h(
    'span',
    { class: 'shipment-group-icon-cluster' },
    rules.map((ruleType) =>
      renderGroupIconButton(g, h(ShipmentGroupRuleIcon, { ruleType, size: 14 })),
    ),
  )
}

function renderShipmentGroups(row: Shipment) {
  const groups = row.groups ?? []
  if (!groups.length) return h('span', { class: 'tracking-empty' }, '—')
  const nodes = groups.flatMap((g, index) => {
    const parts: ReturnType<typeof h>[] = [renderGroupIconCluster(g)]
    if (index < groups.length - 1) {
      parts.push(h('span', { class: 'shipment-group-cell-sep', 'aria-hidden': 'true' }, '·'))
    }
    return parts
  })
  return h('span', { class: 'shipment-group-cell truncate block max-w-full' }, nodes)
}

const channelCodeOptions = computed(() =>
  buildChannelSelectOptions(filterOptions.value.channels, filterOptions.value.channelCodes),
)

const timeFieldOptions = [...SHIPMENT_TIME_FIELD_OPTIONS]

function rowKey(row: Shipment) {
  return row.id
}

async function loadCarrierDailyStats() {
  try {
    carrierDaily.value = await getTrackingSyncDailyStats('carrier')
  } catch {
    carrierDaily.value = null
  }
}

async function loadFreshnessStats() {
  try {
    freshnessStats.value = await getTrackingFreshnessStats()
    await refreshPendingTrackingTimeReviewCount()
  } catch {
    freshnessStats.value = null
  }
}

const carrierSyncHint = computed(() => {
  if (!carrierDaily.value) return null
  const d = carrierDaily.value
  let s = `今日同步任务已更新 ${d.updatedShipments} 单、新增 ${d.newLogCount} 条节点`
  if (d.lastFinished) s += ` · 上次 ${d.lastFinished}`
  return s
})

function toggleNoInternalTrackingFilter() {
  filterNoInternalTracking.value = !filterNoInternalTracking.value
  onFiltersChanged()
}

function toggleNoCarrierTrackingFilter() {
  filterNoCarrierTracking.value = !filterNoCarrierTracking.value
  onFiltersChanged()
}

function toggleCarrierAheadFilter() {
  filterCarrierAheadOfInternal.value = !filterCarrierAheadOfInternal.value
  onFiltersChanged()
}

function togglePendingReviewFilter() {
  filterPendingTrackingTimeReview.value = !filterPendingTrackingTimeReview.value
  onFiltersChanged()
}

function toggleStaleDaysFilter(days: 7 | 14) {
  if (filterStaleDays.value === days) {
    filterStaleDays.value = null
  } else {
    filterStaleDays.value = days
    filterNoInternalTracking.value = false
    filterStatus.value = DEFAULT_STATUS_FILTER
  }
  onFiltersChanged()
}

function toggleStale7Filter() {
  toggleStaleDaysFilter(7)
}

function toggleStale14Filter() {
  toggleStaleDaysFilter(14)
}

const statusLabel: Record<string, string> = {
  IN_TRANSIT: '转运中',
  DELIVERED: '已签收',
  INSPECTION: '查验',
  UNKNOWN: '未知',
}

const exceptionLabelByCode = computed(() => {
  const m: Record<string, string> = {}
  for (const t of filterOptions.value.exceptionTypes) {
    m[t.code] = t.nameZh
  }
  return m
})

function exceptionLabel(code: string | null | undefined) {
  if (!code) return '—'
  return exceptionLabelByCode.value[code] || code
}

function hasActiveException(row: Shipment) {
  return !!(row.exceptionCode && row.exceptionCode.trim())
}

async function openTrackingDrawer(row: Shipment, tab: 'internal' | 'carrier' = 'internal') {
  trackingDrawerTab.value = tab
  trackingDrawerShow.value = true
  trackingDrawerShipment.value = row
  try {
    trackingDrawerShipment.value = await getShipment(row.id)
  } catch {
    /* 列表行数据兜底 */
  }
}

function handleTrackingDrawerShipmentUpdated(row: Shipment) {
  trackingDrawerShipment.value = row
  const idx = items.value.findIndex((x) => x.id === row.id)
  if (idx >= 0) items.value[idx] = { ...items.value[idx], ...row }
  void loadFreshnessStats()
  void loadCarrierDailyStats()
}

function renderTrackingSummaryCell(
  row: Shipment,
  tab: 'internal' | 'carrier',
  time: string | null | undefined,
  desc: string | null | undefined,
) {
  const t = (time || '').trim()
  const d = (desc || '').trim()
  if (!t && !d) {
    return h('span', { class: 'tracking-empty' }, '—')
  }
  const carrierAhead = isCarrierTrackingNewerThanInternal(row)
  const effective =
    tab === 'internal' ? hasEffectiveInternalTracking(row) : Boolean(t)
  const level = trackingFreshnessLevel(time, effective)
  const dot = h('span', {
    class: `mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${FRESHNESS_DOT_CLASS[level]}`,
    'aria-hidden': 'true',
  })
  const timeRow =
    tab === 'carrier' && carrierAhead
      ? h('div', { class: 'flex min-w-0 items-center gap-1 leading-tight' }, [
          h('div', { class: 'tracking-ahead-time truncate text-xs tabular-nums' }, t),
          h('span', { class: 'tracking-ahead-badge shrink-0' }, '承新'),
        ])
      : t
        ? h(
            'div',
            {
              class: [
                'text-xs tabular-nums leading-tight',
                tab === 'internal' && carrierAhead ? 'tracking-time--faded' : 'tracking-time',
              ],
            },
            t,
          )
        : null
  const block = h('div', { class: 'tracking-summary-cell min-w-0 max-w-full flex gap-1.5' }, [
    dot,
    h('div', { class: 'min-w-0 flex-1' }, [
      timeRow,
      d
        ? h(
            'div',
            {
              class: [
                'text-xs leading-snug truncate',
                tab === 'carrier' && carrierAhead
                  ? 'tracking-ahead-desc'
                  : tab === 'internal' && carrierAhead
                    ? 'tracking-desc--faded'
                    : 'tracking-desc',
              ],
              title: d,
            },
            d,
          )
        : h('div', { class: 'tracking-empty text-xs' }, '—'),
    ]),
  ])
  const btnClass = [
    'tracking-summary-btn w-full min-w-0 cursor-pointer rounded px-1 py-0.5 text-left transition-colors',
    tab === 'carrier' && carrierAhead ? 'tracking-summary-btn--carrier-ahead' : '',
    tab === 'internal' && carrierAhead ? 'tracking-summary-btn--internal-behind' : '',
  ]
    .filter(Boolean)
    .join(' ')
  const clickable = h(
    'button',
    {
      type: 'button',
      class: btnClass,
      onClick: (e: MouseEvent) => {
        e.stopPropagation()
        openTrackingDrawer(row, tab)
      },
    },
    [block],
  )
  const tip = [t, d].filter(Boolean).join('\n')
  if (tip.length > 36) {
    return h(NTooltip, { trigger: 'hover' }, { trigger: () => clickable, default: () => tip })
  }
  return clickable
}

function openLastMileTrackUrl(row: Shipment) {
  const info = resolveLastMileTracking(row)
  if (!info?.url) {
    message.warning('暂未识别承运商官网，请手动查询')
    return
  }
  window.open(info.url, '_blank', 'noopener,noreferrer')
}

function renderLastMileBadge(row: Shipment) {
  const info = resolveLastMileTracking(row)
  if (!info) return null
  const badgeBtn = h(
    'button',
    {
      type: 'button',
      class: 'last-mile-badge-btn',
      onClick: (e: MouseEvent) => {
        e.stopPropagation()
        openLastMileTrackUrl(row)
      },
    },
    [h(LastMileBadge, { interactive: Boolean(info.url) })],
  )
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () => badgeBtn,
      default: () => formatLastMileTooltip(row) ?? info.number,
    },
  )
}

function renderRelativeTimeCell(iso: string | null | undefined) {
  const formatted = formatRelativeTime(iso)
  if (!formatted) return '—'
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () =>
        h('span', { class: 'cursor-default text-zinc-400 tabular-nums' }, formatted.relative),
      default: () => formatted.absolute,
    },
  )
}

function renderUpdatedTime(row: Shipment) {
  return renderRelativeTimeCell(row.updatedTime)
}

function renderExceptionBadge(row: Shipment) {
  if (!hasActiveException(row) || !row.exceptionCode) return null
  return h(ExceptionStatusBadge, {
    code: row.exceptionCode,
    label: exceptionLabel(row.exceptionCode),
    durationLabel: row.exceptionDurationLabel,
  })
}

function renderActionWithTooltip(
  kind: 'view' | 'edit' | 'delete' | 'subscribe',
  tooltip: string,
  options?: {
    onClick?: () => void
    active?: boolean
    emphasis?: boolean
    loading?: boolean
  },
) {
  return h(
    NTooltip,
    { trigger: 'hover', showArrow: false, disabled: options?.loading },
    {
      trigger: () =>
        h(TableActionIcon, {
          kind,
          title: tooltip,
          active: options?.active,
          emphasis: options?.emphasis,
          loading: options?.loading,
          onClick: options?.onClick,
        }),
      default: () => tooltip,
    },
  )
}

function renderSubscribeAction(row: Shipment) {
  const subscribed = Boolean(row.subscribed)
  const tooltip = subscribed ? '已订阅，点击取消' : '订阅轨迹更新'
  return renderActionWithTooltip('subscribe', tooltip, {
    active: subscribed,
    loading: subscriptionTogglingId.value === row.id,
    onClick: () => toggleShipmentSubscribe(row),
  })
}

function renderShipmentNo(row: Shipment) {
  const noCell = h(
    'span',
    { class: 'shipment-no-cell font-medium' },
    row.shipmentNo,
  )
  const inner = h('span', { class: 'shipment-no-cell-row' }, [
    noCell,
    renderLastMileBadge(row),
    renderExceptionBadge(row),
  ])
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () => inner,
      default: () => row.shipmentNo,
    },
  )
}

const exceptionColumns: DataTableColumns<Shipment> = [
  {
    title: '异常状态',
    key: 'exceptionCode',
    width: 88,
    align: 'center',
    render: (row) => {
      if (!row.exceptionCode) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return h(ExceptionStatusBadge, {
        code: row.exceptionCode,
        label: exceptionLabel(row.exceptionCode),
        durationLabel: row.exceptionDurationLabel,
        showLabel: true,
      })
    },
  },
  {
    title: '异常时长',
    key: 'exceptionDurationLabel',
    width: 88,
    align: 'center',
    render: (row) => {
      if (!row.exceptionDurationLabel) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return h('span', { class: 'text-xs tabular-nums text-zinc-400' }, row.exceptionDurationLabel)
    },
  },
]

const statusOptions = computed(() =>
  filterOptions.value.statusCodes.map((code) => ({
    label: statusLabel[code] || code,
    value: code,
  })),
)

const exceptionFilterOptions = computed(() =>
  filterOptions.value.exceptionTypes.map((t) => ({
    label: t.nameZh,
    value: t.code,
  })),
)

const hasExceptionFilterOptions = [
  { label: '有异常', value: 'yes' },
  { label: '无异常', value: 'no' },
]

const staleOptions = [
  { label: '≥7 天未更新', value: 7 },
  { label: '≥14 天未更新', value: 14 },
  { label: '≥30 天未更新', value: 30 },
]

const customerOptions = computed(() =>
  filterOptions.value.customers.map((v) => ({ label: v, value: v })),
)
const carrierOptions = computed(() =>
  buildCarrierSelectOptions(
    filterOptions.value.carriers,
    filterOptions.value.carrierCodes,
    { includeEmpty: true, emptyValue: CARRIER_FILTER_EMPTY },
  ),
)
const countryOptions = computed(() =>
  filterOptions.value.countryCodes.map((code) => ({
    label: countryLabel(code) === code ? code : `${countryLabel(code)} (${code})`,
    value: code,
  })),
)
const channelNameZhOptions = computed(() =>
  [...new Set(filterOptions.value.channelNameZhs.filter(Boolean))].map((v) => ({
    label: v,
    value: v,
  })),
)
const channelCategoryOptions = computed(() =>
  filterOptions.value.channelCategories.map((v) => ({ label: v, value: v })),
)

const systemViewOptions = computed(() =>
  SHIPMENT_SYSTEM_VIEWS.map((v) => ({ label: v.label, value: v.id })),
)

function carrierLabel(code: string | null | undefined): string {
  if (!code) return ''
  if (code === CARRIER_FILTER_EMPTY) return '（未填写）'
  const opt = carrierOptions.value.find((o) => o.value === code)
  return opt?.label || code
}

function groupLabel(id: string | null | undefined): string {
  if (!id) return ''
  const opt = groupFilterOptions.value.find((o) => o.value === id)
  return opt?.label || id
}

const filterQueryInput = computed((): ShipmentFilterQueryInput => ({
  searchKeyword: searchKeyword.value,
  searchShipmentNo: searchShipmentNo.value,
  searchTrackingContent: searchTrackingContent.value,
  advExactShipmentNo: advExactShipmentNo.value,
  advContainerNos: advContainerNos.value,
  advBillNos: advBillNos.value,
  advCustomerShipmentIds: advCustomerShipmentIds.value,
  filterStatus: filterStatus.value,
  filterCustomer: filterCustomer.value,
  filterChannelCode: filterChannelCode.value,
  timeField: timeField.value,
  timeRange: timeRange.value,
  filterCarrier: filterCarrier.value,
  filterCountry: filterCountry.value,
  filterChannelNameZh: filterChannelNameZh.value,
  filterChannelCategory: filterChannelCategory.value,
  filterCustomerNo: filterCustomerNo.value,
  filterDestinationPort: filterDestinationPort.value,
  filterAddressKeyword: filterAddressKeyword.value,
  filterVesselVoyage: filterVesselVoyage.value,
  filterVipOnly: filterVipOnly.value,
  filterFclOnly: filterFclOnly.value,
  filterNoInternalTracking: filterNoInternalTracking.value,
  filterNoCarrierTracking: filterNoCarrierTracking.value,
  filterCarrierAheadOfInternal: filterCarrierAheadOfInternal.value,
  filterPendingTrackingTimeReview: filterPendingTrackingTimeReview.value,
  filterStaleDays: filterStaleDays.value,
  filterNoTracking: filterNoInternalTracking.value,
  filterNoZipcode: filterNoZipcode.value,
  filterHasTrackingNumber: filterHasTrackingNumber.value,
  filterException: filterException.value,
  filterPaymentStatus: filterPaymentStatus.value,
  filterHasException: filterHasException.value,
  filterGroupId: filterGroupId.value,
  filterGroupNo: filterGroupNo.value,
  filterRuleType: filterRuleType.value,
  filterHasGroup: filterHasGroup.value,
  missingEtd: missingEtd.value,
  missingAtd: missingAtd.value,
  missingEta: missingEta.value,
  missingAta: missingAta.value,
  missingExpectedDelivery: missingExpectedDelivery.value,
  missingDelivered: missingDelivered.value,
  notDelivered: notDelivered.value,
  hasAta: hasAta.value,
  deliveryRisk: deliveryRisk.value,
  advancedTimes: advancedTimes.value,
  shipmentNoSearchActive: shipmentNoTokens.value.length > 0,
}))

const filterSummaryTags = computed(() =>
  buildShipmentFilterSummaryTags(filterQueryInput.value, {
    statusLabel,
    countryLabel,
    carrierLabel,
    channelLabel: (code) => channelFilterLabel(filterOptions.value.channels, code),
    groupLabel,
    exceptionLabel,
    freshnessLabel: FRESHNESS_LABEL,
  }),
)

const advancedOnlyActiveCount = computed(() => {
  let n = 0
  if (searchKeyword.value.trim()) n++
  if (advExactShipmentNo.value.trim()) n++
  if (advContainerNos.value.trim()) n++
  if (advBillNos.value.trim()) n++
  if (advCustomerShipmentIds.value.trim()) n++
  if (filterCarrier.value) n++
  if (filterCountry.value) n++
  if (filterChannelNameZh.value) n++
  if (filterChannelCategory.value) n++
  if (filterCustomerNo.value) n++
  if (filterDestinationPort.value) n++
  if (filterAddressKeyword.value) n++
  if (filterVesselVoyage.value) n++
  if (filterVipOnly.value) n++
  if (!filterFclOnly.value) n++
  if (filterHasException.value != null) n++
  if (filterException.value) n++
  if (filterPaymentStatus.value) n++
  if (filterNoInternalTracking.value) n++
  if (filterNoCarrierTracking.value) n++
  if (filterNoZipcode.value) n++
  if (filterHasTrackingNumber.value) n++
  if (filterStaleDays.value) n++
  if (filterGroupId.value) n++
  if (filterGroupNo.value) n++
  if (filterRuleType.value) n++
  if (filterHasGroup.value != null) n++
  if (missingEtd.value) n++
  if (missingAtd.value) n++
  if (missingEta.value) n++
  if (missingAta.value) n++
  if (missingExpectedDelivery.value) n++
  if (missingDelivered.value) n++
  if (notDelivered.value) n++
  if (hasAta.value) n++
  if (deliveryRisk.value) n++
  const adv = advancedTimes.value
  for (const key of Object.keys(adv) as (keyof typeof adv)[]) {
    if (adv[key]) n++
  }
  return n
})

function channelDisplayLabel(row: Shipment): string {
  const zh = row.channelNameZh?.trim()
  if (zh) return zh
  return row.channelCode?.trim() || '—'
}

function carrierDisplayLabel(row: Shipment): string {
  const zh = row.carrierNameZh?.trim()
  if (zh) return zh
  return row.carrierCode?.trim() || '—'
}

/** 横向滚动宽度 = 各列 width 之和 + 余量（避免滑条到不了最右侧） */
function sumTableColumnWidths(cols: DataTableColumns<Shipment>): number {
  let total = 0
  for (const col of cols) {
    if (col.type === 'selection') {
      total += typeof col.width === 'number' ? col.width : 40
      continue
    }
    const w = 'width' in col ? col.width : undefined
    if (typeof w === 'number') total += w
  }
  return total
}

/** 运单表滚动条：悬停显示、细轨道，避免常显抢眼 */
const tableScrollbarProps = {
  trigger: 'hover' as const,
  size: 6,
  themeOverrides: {
    railColor: 'transparent',
    color: 'rgba(113, 113, 122, 0.35)',
    colorHover: 'rgba(161, 161, 170, 0.55)',
  },
}

function clearSelection() {
  checkedRowKeys.value = []
}

function buildListParams(): Parameters<typeof listShipments>[0] {
  const tokens = shipmentNoTokens.value
  const multiShipment = batchShipmentSearchActive.value
  const limit = multiShipment
    ? Math.min(500, Math.max(pageSize.value, tokens.length))
    : pageSize.value
  const offset = multiShipment ? 0 : (page.value - 1) * pageSize.value

  return {
    ...buildShipmentFilterQuery(filterQueryInput.value),
    limit,
    offset,
    ...(sortBy.value && sortOrder.value
      ? { sortBy: sortBy.value, sortOrder: sortOrder.value }
      : {}),
  }
}

function handleSorterChange(sorter: DataTableSortState | null) {
  if (!sorter || sorter.columnKey !== 'shipmentNo' || !sorter.order) {
    sortBy.value = null
    sortOrder.value = null
  } else {
    sortBy.value = 'shipmentNo'
    sortOrder.value = sorter.order === 'ascend' ? 'asc' : 'desc'
  }
  page.value = 1
  void loadList()
}

let listRequestSeq = 0

async function loadList() {
  const seq = ++listRequestSeq
  loading.value = true
  try {
    const res = await listShipments(buildListParams())
    if (seq !== listRequestSeq) return
    items.value = res.items
    total.value = res.total
    syncSelectionWithItems()
  } catch (e) {
    if (seq !== listRequestSeq) return
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    if (seq === listRequestSeq) loading.value = false
  }
}

/** 下拉/勾选筛选变更：回到第 1 页并立即刷新 */
function onFiltersChanged() {
  page.value = 1
  checkedRowKeys.value = []
  void loadList()
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch([searchShipmentNo, searchKeyword, searchTrackingContent], () => {
  if (shipmentNoTokens.value.length > 0) {
    filterStatus.value = null
  }
  page.value = 1
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    checkedRowKeys.value = []
    void loadList()
  }, 300)
})

watch([page, pageSize], () => {
  checkedRowKeys.value = []
  void loadList()
})

watch(filterNoInternalTracking, (checked) => {
  if (checked) filterStaleDays.value = null
})

async function loadFilterOptions() {
  try {
    filterOptions.value = await getShipmentFilterOptions()
  } catch {
    /* 筛选项加载失败不阻塞列表 */
  }
}

/** 订阅消息等带 ?shipmentNo= 跳入时同步运单号搜索框 */
function readRouteShipmentNo(): string {
  const q = route.query.shipmentNo
  if (typeof q === 'string') return q.trim()
  if (Array.isArray(q)) {
    const first = q[0]
    return typeof first === 'string' ? first.trim() : ''
  }
  return ''
}

function isRouteFromNotify(): boolean {
  const f = route.query.fromNotify
  if (f === '1' || f === 'true') return true
  if (Array.isArray(f)) return f[0] === '1' || f[0] === 'true'
  return false
}

function isRouteFromGroup(): boolean {
  const f = route.query.fromGroup
  if (f === '1' || f === 'true') return true
  if (Array.isArray(f)) return f[0] === '1' || f[0] === 'true'
  return false
}

function showNotifyJumpHint(sn: string) {
  message.success(`已定位运单 ${sn}`)
}

function showGroupJumpHint(count: number, firstNo: string) {
  if (count > 1) {
    message.success(`已筛选组内 ${count} 个运单`)
    return
  }
  message.success(`已定位运单 ${firstNo}`)
}

function applyRouteShipmentNoToSearch() {
  const sn = readRouteShipmentNo()
  if (!sn) return
  const fromNotify = isRouteFromNotify()
  const fromGroup = isRouteFromGroup()
  const tokens = parseBatchSearchTokens(sn)
  if (searchShipmentNo.value !== sn) {
    searchShipmentNo.value = sn
  }
  filterStatus.value = null
  if (fromGroup && tokens.length > 0) {
    showGroupJumpHint(tokens.length, tokens[0] || sn)
    void router.replace({ path: '/shipments', query: { shipmentNo: sn } })
  } else if (fromNotify) {
    showNotifyJumpHint(tokens[0] || sn)
    void router.replace({ path: '/shipments', query: { shipmentNo: sn } })
  }
}

watch(
  () => [readRouteShipmentNo(), route.query.fromNotify, route.query.fromGroup] as const,
  () => {
    applyRouteShipmentNoToSearch()
  },
)

onMounted(async () => {
  applyRouteShipmentNoToSearch()
  await Promise.all([
    loadDictTypes('country_code'),
    loadFilterOptions(),
    loadCarrierDailyStats(),
    loadFreshnessStats(),
  ])
  await loadList()
})

function openCreate() {
  modalMode.value = 'create'
  editingRow.value = null
  modalShow.value = true
}

function openEdit(row: Shipment) {
  modalMode.value = 'edit'
  editingRow.value = row
  modalShow.value = true
}

async function handleFormSubmit(payload: ShipmentPayload) {
  try {
    if (modalMode.value === 'create') {
      await createShipment(payload)
      message.success('运单已创建')
      modalShow.value = false
      searchShipmentNo.value = payload.shipmentNo
      page.value = 1
      await loadList()
      return
    }
    if (!editingRow.value) return
    const editId = editingRow.value.id
    await updateShipment(editId, payload)
    message.success('运单已更新')
    modalShow.value = false
    await loadList()
    if (trackingDrawerShipment.value?.id === editId) {
      try {
        trackingDrawerShipment.value = await getShipment(editId)
      } catch {
        trackingDrawerShipment.value =
          items.value.find((r) => r.id === editId) ?? trackingDrawerShipment.value
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  }
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
    const params = buildListParams()
    const blob = await exportShipmentsExcel({
      ...params,
      limit: Math.min(total.value || 10_000, 10_000),
      offset: 0,
    })
    const ts = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '').slice(0, 14)
    downloadBlob(blob, `运单导出_${ts}.xlsx`)
    message.success(`已导出 ${total.value} 条运单（当前筛选）`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleBatchSubscribe() {
  const ids = selectedIds.value
  if (!ids.length) {
    message.warning('请先勾选运单')
    return
  }
  batchSubmitting.value = true
  try {
    const res = await batchSubscribeShipments(ids)
    let text = `已订阅 ${res.subscribed} / ${res.total} 条轨迹更新`
    if (res.failed) text += `，失败 ${res.failed} 条`
    if (res.failed && res.errors.length) {
      message.warning(text, { duration: 6000 })
    } else {
      message.success(text)
    }
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量订阅失败')
  } finally {
    batchSubmitting.value = false
  }
}

async function handleBatchUnsubscribe() {
  const ids = selectedIds.value
  if (!ids.length) {
    message.warning('请先勾选运单')
    return
  }
  batchSubmitting.value = true
  try {
    const res = await batchUnsubscribeShipments(ids)
    message.success(`已取消 ${res.unsubscribed} 条订阅`)
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量取消订阅失败')
  } finally {
    batchSubmitting.value = false
  }
}

async function toggleShipmentSubscribe(row: Shipment) {
  subscriptionTogglingId.value = row.id
  try {
    if (row.subscribed) {
      await unsubscribeShipment(row.id)
      message.success('已取消轨迹订阅')
    } else {
      await subscribeShipment(row.id)
      message.success('已订阅轨迹更新')
    }
    const idx = items.value.findIndex((x) => x.id === row.id)
    if (idx >= 0) {
      items.value[idx] = { ...items.value[idx], subscribed: !row.subscribed }
    }
    if (trackingDrawerShipment.value?.id === row.id) {
      trackingDrawerShipment.value = {
        ...trackingDrawerShipment.value,
        subscribed: !row.subscribed,
      }
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    subscriptionTogglingId.value = null
  }
}

async function handleDelete(row: Shipment) {
  try {
    await deleteShipment(row.id)
    message.success('已删除')
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除失败')
  }
}

function notifyBatchResult(res: ShipmentBatchResult, verb: '删除' | '更新') {
  const ok = verb === '删除' ? (res.deleted ?? 0) : (res.updated ?? 0)
  let text = `${verb}完成：成功 ${ok} / ${res.total} 条`
  if (res.skipped.length) text += `，跳过 ${res.skipped.length} 条`
  if (res.errors.length) text += `，失败 ${res.errors.length} 条`
  if (res.errors.length && ok === 0) {
    message.error(text, { duration: 8000 })
  } else if (res.skipped.length || res.errors.length) {
    message.warning(text, { duration: 6000 })
  } else {
    message.success(text)
  }
}

async function handleBatchDelete() {
  const ids = selectedIds.value
  if (!ids.length) {
    message.warning('请先勾选运单')
    return
  }
  batchSubmitting.value = true
  try {
    const res = await batchDeleteShipments(ids)
    notifyBatchResult(res, '删除')
    clearSelection()
    if (items.value.length <= ids.length && page.value > 1) page.value -= 1
    await loadList()
    await loadFreshnessStats()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量删除失败')
  } finally {
    batchSubmitting.value = false
  }
}

async function handleBatchEditSubmit(updates: Partial<ShipmentPayload>) {
  const ids = selectedIds.value
  if (!ids.length) return
  batchSubmitting.value = true
  try {
    const res = await batchUpdateShipments(ids, updates)
    notifyBatchResult(res, '更新')
    batchEditShow.value = false
    clearSelection()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '批量修改失败')
  } finally {
    batchSubmitting.value = false
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function handleSyncTracking(shipmentNos?: string[]) {
  syncingTracking.value = true
  try {
    const res = await syncTracking(shipmentNos)
    notifyTrackingSyncResult(message, res, '内部轨迹')
    await loadFreshnessStats()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新内部轨迹失败')
  } finally {
    syncingTracking.value = false
  }
}

async function handleSyncCarrierTracking(shipmentNos?: string[]) {
  syncingCarrier.value = true
  try {
    const res = await syncCarrierTracking(shipmentNos)
    notifyTrackingSyncResult(message, res, '承运商轨迹')
    await loadCarrierDailyStats()
    await loadFreshnessStats()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新承运商轨迹失败')
  } finally {
    syncingCarrier.value = false
  }
}

function resetFilterValues() {
  selectedSystemView.value = null
  filterStatus.value = DEFAULT_STATUS_FILTER
  filterException.value = null
  filterPaymentStatus.value = null
  filterHasException.value = null
  filterCustomer.value = null
  filterChannelCode.value = null
  timeField.value = null
  timeRange.value = null
  filterVipOnly.value = false
  filterFclOnly.value = false
  filterCarrier.value = null
  filterCountry.value = null
  filterChannelNameZh.value = null
  filterChannelCategory.value = null
  filterCustomerNo.value = ''
  filterDestinationPort.value = null
  filterAddressKeyword.value = null
  filterVesselVoyage.value = null
  filterNoInternalTracking.value = false
  filterNoCarrierTracking.value = false
  filterCarrierAheadOfInternal.value = false
  filterPendingTrackingTimeReview.value = false
  filterStaleDays.value = null
  filterNoZipcode.value = false
  filterHasTrackingNumber.value = false
  filterGroupId.value = null
  filterGroupNo.value = null
  filterRuleType.value = null
  filterHasGroup.value = null
  missingEtd.value = false
  missingAtd.value = false
  missingEta.value = false
  missingAta.value = false
  missingExpectedDelivery.value = false
  missingDelivered.value = false
  notDelivered.value = false
  hasAta.value = false
  deliveryRisk.value = null
  advancedTimes.value = emptyAdvancedTimeRanges()
  searchShipmentNo.value = ''
  searchKeyword.value = ''
  searchTrackingContent.value = ''
  advExactShipmentNo.value = ''
  advContainerNos.value = ''
  advBillNos.value = ''
  advCustomerShipmentIds.value = ''
}

function resetFilters() {
  resetFilterValues()
  page.value = 1
  loadList()
}

function removeFilterTag(key: string) {
  switch (key) {
    case 'searchKeyword':
      searchKeyword.value = ''
      break
    case 'searchShipmentNo':
      searchShipmentNo.value = ''
      break
    case 'advExactShipmentNo':
      advExactShipmentNo.value = ''
      break
    case 'advContainerNos':
      advContainerNos.value = ''
      break
    case 'advBillNos':
      advBillNos.value = ''
      break
    case 'advCustomerShipmentIds':
      advCustomerShipmentIds.value = ''
      break
    case 'searchTrackingContent':
      searchTrackingContent.value = ''
      break
    case 'filterStatus':
      filterStatus.value = DEFAULT_STATUS_FILTER
      break
    case 'filterCustomer':
      filterCustomer.value = null
      break
    case 'filterChannelCode':
      filterChannelCode.value = null
      break
    case 'timeRange':
      timeField.value = null
      timeRange.value = null
      break
    case 'filterCarrier':
      filterCarrier.value = null
      break
    case 'filterCountry':
      filterCountry.value = null
      break
    case 'filterChannelNameZh':
      filterChannelNameZh.value = null
      break
    case 'filterChannelCategory':
      filterChannelCategory.value = null
      break
    case 'filterCustomerNo':
      filterCustomerNo.value = ''
      break
    case 'filterDestinationPort':
      filterDestinationPort.value = null
      break
    case 'filterAddressKeyword':
      filterAddressKeyword.value = null
      break
    case 'filterVesselVoyage':
      filterVesselVoyage.value = null
      break
    case 'filterVipOnly':
      filterVipOnly.value = false
      break
    case 'filterFclOnly':
      filterFclOnly.value = false
      break
    case 'filterHasException':
      filterHasException.value = null
      break
    case 'filterException':
      filterException.value = null
      break
    case 'filterPaymentStatus':
      filterPaymentStatus.value = null
      break
    case 'filterNoInternalTracking':
      filterNoInternalTracking.value = false
      break
    case 'filterNoCarrierTracking':
      filterNoCarrierTracking.value = false
      break
    case 'filterNoZipcode':
      filterNoZipcode.value = false
      break
    case 'filterHasTrackingNumber':
      filterHasTrackingNumber.value = false
      break
    case 'filterStaleDays':
      filterStaleDays.value = null
      break
    case 'filterCarrierAheadOfInternal':
      filterCarrierAheadOfInternal.value = false
      break
    case 'filterPendingTrackingTimeReview':
      filterPendingTrackingTimeReview.value = false
      break
    case 'filterGroupId':
      filterGroupId.value = null
      break
    case 'filterGroupNo':
      filterGroupNo.value = null
      break
    case 'filterRuleType':
      filterRuleType.value = null
      break
    case 'filterHasGroup':
      filterHasGroup.value = null
      break
    case 'missingEtd':
      missingEtd.value = false
      break
    case 'missingAtd':
      missingAtd.value = false
      break
    case 'missingEta':
      missingEta.value = false
      break
    case 'missingAta':
      missingAta.value = false
      break
    case 'missingExpectedDelivery':
      missingExpectedDelivery.value = false
      break
    case 'missingDelivered':
      missingDelivered.value = false
      break
    case 'notDelivered':
      notDelivered.value = false
      break
    case 'hasAta':
      hasAta.value = false
      break
    case 'deliveryRisk':
      deliveryRisk.value = null
      break
  }
  selectedSystemView.value = null
  onFiltersChanged()
}

function applySystemView(viewId: ShipmentSystemViewId | null) {
  if (!viewId) {
    selectedSystemView.value = null
    return
  }
  resetFilterValues()
  const overrides = systemViewFilters(viewId)
  if (overrides.deliveryRisk) deliveryRisk.value = overrides.deliveryRisk
  if (overrides.notDelivered) notDelivered.value = true
  if (overrides.hasAta) hasAta.value = true
  if (overrides.pendingTrackingTimeReview) filterPendingTrackingTimeReview.value = true
  filterStatus.value = null
  selectedSystemView.value = viewId
  onFiltersChanged()
}

function openGroupAction(mode: ShipmentGroupBatchMode) {
  if (!selectedCount.value) {
    message.warning('请先勾选运单')
    return
  }
  if (mode === 'remove' && !selectedMemberGroupOptions.value.length) {
    message.warning('所选运单未加入任何分组')
    return
  }
  if (mode === 'suggest') {
    if (selectedCount.value < 2) {
      message.warning('推荐分组至少需勾选 2 条运单')
      return
    }
    groupSuggestionsShow.value = true
    return
  }
  groupActionMode.value = mode
  groupActionShow.value = true
}

async function handleGroupCreate(
  groupName: string,
  customer?: string,
  rules?: ShipmentGroupRuleInput[],
) {
  const ids = selectedIds.value
  if (!ids.length) return
  groupActionSubmitting.value = true
  try {
    const group = await createShipmentGroup({
      groupName,
      rules: rules ?? [],
      customer: customer ?? null,
    })
    const res = await addShipmentGroupMembers(group.id, ids)
    let text = `已新建分组 ${formatGroupNoDisplay(group.groupNo)}，加入 ${res.added} / ${res.total} 条`
    if (res.skipped) text += `，跳过 ${res.skipped} 条`
    if (res.failed) text += `，失败 ${res.failed} 条`
    message.success(text)
    groupActionShow.value = false
    await loadFilterOptions()
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '新建分组失败')
  } finally {
    groupActionSubmitting.value = false
  }
}

async function handleGroupAdd(groupId: string) {
  const ids = selectedIds.value
  if (!ids.length) return
  groupActionSubmitting.value = true
  try {
    const res = await addShipmentGroupMembers(groupId, ids)
    let text = `已加入 ${res.added} / ${res.total} 条`
    if (res.skipped) text += `，跳过 ${res.skipped} 条`
    if (res.failed) text += `，失败 ${res.failed} 条`
    message.success(text)
    groupActionShow.value = false
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加入分组失败')
  } finally {
    groupActionSubmitting.value = false
  }
}

async function handleGroupRemove(groupId: string) {
  const ids = selectedIds.value
  if (!ids.length) return
  groupActionSubmitting.value = true
  try {
    const res = await removeShipmentGroupMembers(groupId, ids)
    let text = `已移出 ${res.removed} / ${res.total} 条`
    if (res.notFound) text += `，未在组内 ${res.notFound} 条`
    message.success(text)
    groupActionShow.value = false
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '移出分组失败')
  } finally {
    groupActionSubmitting.value = false
  }
}

function onGroupActionConfirmCreate(
  groupName: string,
  customer?: string,
  rules?: ShipmentGroupRuleInput[],
) {
  void handleGroupCreate(groupName, customer, rules)
}

function onGroupActionConfirmGroupId(groupId: string) {
  if (groupActionMode.value === 'add') void handleGroupAdd(groupId)
  else if (groupActionMode.value === 'remove') void handleGroupRemove(groupId)
}

async function handleOpenException(
  exceptionCode: string,
  openedTime?: string,
  note?: string,
) {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  exceptionSubmitting.value = true
  try {
    const res = await openShipmentExceptions(nos, exceptionCode, { openedTime, note })
    exceptionOpenShow.value = false
    let text = `已标记异常 ${res.opened ?? 0} 条`
    if (res.skipped.length) text += `，跳过 ${res.skipped.length} 条`
    if (res.errors.length) text += `，失败 ${res.errors.length} 条`
    message.success(text)
    clearSelection()
    await loadList()
    await loadFilterOptions()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '标记异常失败')
  } finally {
    exceptionSubmitting.value = false
  }
}

async function handleCloseException(closedTime?: string, note?: string) {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  exceptionSubmitting.value = true
  try {
    const res = await closeShipmentExceptions(nos, { closedTime, note })
    exceptionCloseShow.value = false
    let text = `已解除异常 ${res.closed ?? 0} 条`
    if (res.skipped.length) text += `，跳过 ${res.skipped.length} 条`
    if (res.errors.length) text += `，失败 ${res.errors.length} 条`
    message.success(text)
    clearSelection()
    await loadList()
    await loadFilterOptions()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '解除异常失败')
  } finally {
    exceptionSubmitting.value = false
  }
}

async function handleSyncSelectedInternal() {
  if (!selectedRows.value.length) {
    message.warning('请先勾选运单')
    return
  }
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('所选运单无有效运单号')
    return
  }
  await handleSyncTracking(nos)
}

async function handleSyncSelectedCarrier() {
  if (!selectedRows.value.length) {
    message.warning('请先勾选运单')
    return
  }
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('所选运单无有效运单号')
    return
  }
  await handleSyncCarrierTracking(nos)
}

async function handleSyncSelectedFromDps() {
  if (!selectedRows.value.length) {
    message.warning('请先勾选运单')
    return
  }
  const nos = selectedShipmentNos.value
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
    await loadList()
    await loadFilterOptions()
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'DPS 更新失败')
  } finally {
    syncingDps.value = false
  }
}

async function copySelectedShipmentNos() {
  const nos = selectedShipmentNos.value
  if (!nos.length) {
    message.warning('请先勾选运单')
    return
  }
  const text = nos.join('\n')
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制 ${nos.length} 个运单号`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

function displayField(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

function formatDateCell(value: string | null | undefined): string {
  const v = displayField(value)
  if (!v) return '—'
  return v.length > 10 ? v.slice(0, 10) : v
}

function formatCtnsField(ctns: number | null | undefined): string {
  if (ctns === null || ctns === undefined) return ''
  return `${ctns}ctns`
}

/** 复制格式：运单号 = 客户订单号 [= 货件号] = 地址代码 = 件数ctns → 物流时间 → 物流轨迹 */
function formatTrackingCopyBlock(
  row: Shipment,
  tracking: { desc: string; time: string },
): string {
  const headParts = [
    displayField(row.shipmentNo),
    displayField(row.customerNo),
  ]
  const shipmentId = displayField(row.customerShipmentId)
  if (shipmentId) headParts.push(shipmentId)
  headParts.push(displayField(row.addressCode), formatCtnsField(row.ctns))
  const head = headParts.join(' = ')
  return `${head}\n${tracking.time}\n${tracking.desc}`
}

/** 列表已有字段：优先内部最新轨迹，否则承运商摘要 */
function latestTrackingForCopy(row: Shipment): { desc: string; time: string } {
  if (hasEffectiveInternalTracking(row)) {
    return {
      desc: row.latestTrackingDesc?.trim() || '—',
      time: row.latestTrackingTime?.trim() || '—',
    }
  }
  const carrierDesc = row.latestCarrierDesc?.trim()
  const carrierTime = row.latestCarrierTime?.trim()
  if (carrierDesc || carrierTime) {
    return {
      desc: carrierDesc || '—',
      time: carrierTime || '—',
    }
  }
  return { desc: '—', time: '—' }
}

/** 复制格式：运单号 = FedEx 871877368540 */
function formatTrackingNumberCopyLine(row: Shipment): string | null {
  const info = resolveLastMileTracking(row)
  if (!info) return null
  const no = displayField(row.shipmentNo)
  if (!no) return null
  return `${no} = ${info.carrierLabel} ${info.number}`
}

async function copySelectedTrackingNumbers() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  const lines = rows
    .map((row) => formatTrackingNumberCopyLine(row))
    .filter((line): line is string => Boolean(line))
  if (!lines.length) {
    message.warning('所选运单无转单号')
    return
  }
  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    const skipped = rows.length - lines.length
    message.success(
      skipped > 0
        ? `已复制 ${lines.length} 条转单号（${skipped} 条无转单号已跳过）`
        : `已复制 ${lines.length} 条转单号`,
    )
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

async function copySelectedLatestTracking() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  try {
    const blocks = rows.map((row) =>
      formatTrackingCopyBlock(row, latestTrackingForCopy(row)),
    )
    await navigator.clipboard.writeText(blocks.join('\n\n'))
    message.success(`已复制 ${rows.length} 条最新轨迹`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '复制失败')
  }
}

async function copySelectedShipmentDetailSummary() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  const text = formatShipmentDetailSummaryCopyText(rows)
  if (!text) {
    message.warning('无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制 ${rows.length} 条运单明细`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

async function copySelectedShipmentDetailSummaryWithCustomerNo() {
  const rows = selectedRows.value
  if (!rows.length) {
    message.warning('请先勾选运单')
    return
  }
  const text = formatShipmentDetailSummaryWithCustomerNoCopyText(rows)
  if (!text) {
    message.warning('无可复制内容')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    message.success(`已复制 ${rows.length} 条运单明细（客户编号）`)
  } catch {
    message.error('复制失败，请检查浏览器权限')
  }
}

const copyDropdownOptions: DropdownOption[] = [
  { label: '运单明细', key: 'detailSummary' },
  { label: '运单明细（客户编号）', key: 'detailSummaryCustomerNo' },
  { label: '最新轨迹', key: 'latestTracking' },
  { label: '转单号', key: 'trackingNumbers' },
]

function handleCopyMenuSelect(key: string | number) {
  if (key === 'detailSummary') void copySelectedShipmentDetailSummary()
  else if (key === 'detailSummaryCustomerNo') void copySelectedShipmentDetailSummaryWithCustomerNo()
  else if (key === 'latestTracking') void copySelectedLatestTracking()
  else if (key === 'trackingNumbers') void copySelectedTrackingNumbers()
}

const subscribeDropdownOptions: DropdownOption[] = [
  { label: '批量取消订阅', key: 'unsubscribe' },
]

function handleSubscribeMenuSelect(key: string | number) {
  if (key === 'unsubscribe') void handleBatchUnsubscribe()
}

const batchEditDropdownOptions: DropdownOption[] = [
  { label: '批量删除', key: 'delete' },
]

function handleBatchEditMenuSelect(key: string | number) {
  if (key === 'delete') promptBatchDelete()
}

function promptBatchDelete() {
  const n = selectedCount.value
  if (!n) {
    message.warning('请先勾选运单')
    return
  }
  dialog.warning({
    title: '批量删除',
    content: `确定删除所选 ${n} 条运单？关联轨迹将一并删除且不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: () => {
      void handleBatchDelete()
    },
  })
}

const groupDropdownOptions: DropdownOption[] = [
  { label: '推荐分组', key: 'suggest' },
  { label: '新建分组', key: 'create' },
  { label: '加入已有分组', key: 'add' },
  { label: '移出分组', key: 'remove' },
]

function handleGroupMenuSelect(key: string | number) {
  if (key === 'suggest') openGroupAction('suggest')
  else if (key === 'create') openGroupAction('create')
  else if (key === 'add') openGroupAction('add')
  else if (key === 'remove') openGroupAction('remove')
}

const exceptionDropdownOptions: DropdownOption[] = [
  { label: '标记异常', key: 'open' },
  { label: '解除异常', key: 'close' },
]

function handleExceptionMenuSelect(key: string | number) {
  if (key === 'open') exceptionOpenShow.value = true
  else if (key === 'close') exceptionCloseShow.value = true
}

async function onFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  importing.value = true
  try {
    const res = await importShipmentsExcel(file)
    let text =
      `导入完成：新增 ${res.created} 条，更新 ${res.updated} 条（按运单号匹配）` +
      (res.failed ? `，跳过/失败 ${res.failed} 行` : '')
    if (res.skippedColumns?.length) {
      const preview = res.skippedColumns.slice(0, 5).join('、')
      const more =
        res.skippedColumns.length > 5 ? ` 等 ${res.skippedColumns.length} 列` : ''
      text += `；未映射列已忽略：${preview}${more}`
    }
    if (res.membersAdded) {
      text += `；分组关联 ${res.membersAdded} 条`
      if (res.groupsCreated) text += `（新建 ${res.groupsCreated} 组）`
    }
    message.success(text, { duration: 8000 })
    if (res.failed > 0 && res.errors.length) {
      console.warn('import errors', res.errors)
    }
    page.value = 1
    await loadList()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '导入失败')
  } finally {
    importing.value = false
  }
}

const optionalColumnDefs = computed((): Record<string, DataTableColumns<Shipment>[number]> => ({
  statusCode: {
    title: '状态',
    key: 'statusCode',
    width: 88,
    align: 'center',
    render: (row) => {
      const code = row.statusCode || 'UNKNOWN'
      const label = statusLabel[code] || code
      const tone =
        code === 'DELIVERED'
          ? 'shipment-status-badge--success'
          : code === 'INSPECTION'
            ? 'shipment-status-badge--warning'
            : 'shipment-status-badge--default'
      return h('span', { class: ['shipment-status-badge', tone] }, label)
    },
  },
  customer: {
    title: '客户',
    key: 'customer',
    width: customerColWidth.value,
    minWidth: 120,
    ellipsis: { tooltip: true },
    render: (row) => {
      const name = displayField(row.customer) || '—'
      if (!row.isVip) return name
      return h('span', { class: 'inline-flex max-w-full items-center gap-1' }, [
        h('span', { class: 'min-w-0 truncate' }, name),
        h(VipStarBadge),
      ])
    },
  },
  ctns: { title: '件数', key: 'ctns', width: 64, align: 'center' },
  paymentStatus: {
    title: '付款状态',
    key: 'paymentStatus',
    width: 88,
    align: 'center',
    render: (row) => {
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
    },
  },
  groups: {
    title: '分组',
    key: 'groups',
    width: 104,
    align: 'center',
    ellipsis: { tooltip: false },
    render: (row) => renderShipmentGroups(row),
  },
  channelCode: {
    title: '渠道',
    key: 'channelCode',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => {
      const label = channelDisplayLabel(row)
      const code = row.channelCode?.trim()
      if (!code || label === code) {
        return h('span', label)
      }
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
  carrierCode: {
    title: '承运商',
    key: 'carrierCode',
    width: 90,
    ellipsis: { tooltip: true },
    render: (row) => {
      const label = carrierDisplayLabel(row)
      const code = row.carrierCode?.trim()
      if (!code || label === code) {
        return h('span', label)
      }
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
  addressCode: {
    title: '派送仓库',
    key: 'addressCode',
    width: 100,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.addressCode) || '—',
  },
  zipcode: {
    title: '邮编',
    key: 'zipcode',
    width: 96,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.zipcode) || '—',
  },
  supplierName: {
    title: '供应商',
    key: 'supplierName',
    width: 100,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.supplierName) || '—',
  },
  customerShipmentId: {
    title: '货件号',
    key: 'customerShipmentId',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.customerShipmentId) || '—',
  },
  amazonRefId: {
    title: '亚马逊预约号',
    key: 'amazonRefId',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.amazonRefId) || '—',
  },
  customerNo: {
    title: '客户编号',
    key: 'customerNo',
    width: 108,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.customerNo) || '—',
  },
  countryCode: {
    title: '国家',
    key: 'countryCode',
    width: 80,
    ellipsis: { tooltip: true },
    render: (row) => countryLabel(row.countryCode) || '—',
  },
  deliveryAddress: {
    title: '派送地址',
    key: 'deliveryAddress',
    width: 160,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.deliveryAddress) || '—',
  },
  productName: {
    title: '品名',
    key: 'productName',
    width: 120,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.productName) || '—',
  },
  originWarehouseCode: {
    title: '起运仓',
    key: 'originWarehouseCode',
    width: 96,
    ellipsis: { tooltip: true },
    render: (row) => displayField(row.originWarehouseCode) || '—',
  },
  etd: {
    title: 'ETD',
    key: 'etd',
    width: 100,
    render: (row) => formatDateCell(row.etd),
  },
  warehouseEntryTime: {
    title: '入仓时间',
    key: 'warehouseEntryTime',
    width: 108,
    render: (row) => formatDateCell(row.warehouseEntryTime),
  },
  atd: {
    title: 'ATD',
    key: 'atd',
    width: 100,
    render: (row) => formatDateCell(row.atd),
  },
  eta: {
    title: 'ETA',
    key: 'eta',
    width: 100,
    render: (row) => formatDateCell(row.eta),
  },
  ata: {
    title: 'ATA',
    key: 'ata',
    width: 100,
    render: (row) => formatDateCell(row.ata),
  },
  expectedDeliveryTime: {
    title: '预计送仓',
    key: 'expectedDeliveryTime',
    width: 108,
    render: (row) => formatDateCell(row.expectedDeliveryTime),
  },
  deliveredTime: {
    title: '签收时间',
    key: 'deliveredTime',
    width: 108,
    render: (row) => formatDateCell(row.deliveredTime),
  },
  createdTime: {
    title: '创建时间',
    key: 'createdTime',
    width: 108,
    render: (row) => renderRelativeTimeCell(row.createdTime),
  },
  latestTracking: {
    title: '内部轨迹',
    key: 'latestTracking',
    width: 220,
    ellipsis: { tooltip: true },
    render: (row) => {
      if (!hasEffectiveInternalTracking(row)) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      return renderTrackingSummaryCell(
        row,
        'internal',
        row.latestTrackingTime,
        row.latestTrackingDesc,
      )
    },
  },
  latestCarrier: {
    key: 'latestCarrier',
    width: 220,
    ellipsis: { tooltip: true },
    title: () =>
      h('span', { class: 'inline-flex items-center gap-1' }, [
        '承运商轨迹',
        h(
          NTooltip,
          { trigger: 'hover' },
          {
            trigger: () => h('span', { class: 'tracking-ahead-badge cursor-help' }, '承新'),
            default: () => '该运单承运最新节点时间晚于内部时，单元格琥珀色高亮（非按节点条数统计）',
          },
        ),
      ]),
    render: (row) =>
      renderTrackingSummaryCell(row, 'carrier', row.latestCarrierTime, row.latestCarrierDesc),
  },
  staleDays: {
    title: '未更新',
    key: 'staleDays',
    width: 72,
    align: 'center',
    render: (row) => {
      const d = hasEffectiveInternalTracking(row)
        ? daysSinceLocalCalendar(row.latestTrackingTime)
        : null
      if (d === null) {
        return h('span', { class: 'tracking-empty' }, '—')
      }
      const tone =
        d >= 14
          ? 'shipment-status-badge--error'
          : d >= 7
            ? 'shipment-status-badge--warning'
            : 'shipment-status-badge--default'
      return h('span', { class: ['shipment-status-badge', tone] }, `${d}天`)
    },
  },
  updatedTime: {
    title: '更新时间',
    key: 'updatedTime',
    width: 108,
    render: (row) => renderUpdatedTime(row),
  },
  exceptionCode: exceptionColumns[0],
  exceptionDurationLabel: exceptionColumns[1],
}))

const columns = computed<DataTableColumns<Shipment>>(() => {
  const defs = optionalColumnDefs.value
  const statusCol = defs.statusCode
  const dynamicCols = visibleColumnKeys.value
    .filter((key) => key !== 'statusCode')
    .map((key) => defs[key])
    .filter((col): col is DataTableColumns<Shipment>[number] => Boolean(col))

  return [
    { type: 'selection', fixed: 'left', width: 40 },
    {
      title: '运单号',
      key: 'shipmentNo',
      width: shipmentNoColWidth.value,
      minWidth: 193,
      fixed: 'left',
      sorter: {
        compare: () => 0,
      },
      sortOrder:
        sortBy.value === 'shipmentNo'
          ? sortOrder.value === 'asc'
            ? 'ascend'
            : sortOrder.value === 'desc'
              ? 'descend'
              : false
          : false,
      cellProps: () => ({ class: 'shipment-td-no' }),
      render: (row) => renderShipmentNo(row),
    },
    ...(statusCol ? [{ ...statusCol, fixed: 'left' as const }] : []),
    ...dynamicCols,
    {
      title: '操作',
      key: 'actions',
      width: 132,
      align: 'center',
      fixed: 'right',
      render: (row) =>
        h(
          NSpace,
          { size: 6, justify: 'center', wrap: false, itemStyle: 'display:flex' },
          () => [
            renderSubscribeAction(row),
            renderActionWithTooltip(
              'view',
              row.hasPendingSignedTimeReview ? '签收时间待确认' : '轨迹',
              {
                emphasis: Boolean(row.hasPendingSignedTimeReview),
                onClick: () => openTrackingDrawer(row, 'internal'),
              },
            ),
            renderActionWithTooltip('edit', '编辑', { onClick: () => openEdit(row) }),
            h(
              NPopconfirm,
              { onPositiveClick: () => handleDelete(row) },
              {
                trigger: () => renderActionWithTooltip('delete', '删除'),
                default: () => '确定删除该运单？',
              },
            ),
          ],
        ),
    },
  ] as DataTableColumns<Shipment>
})

const tableScrollX = computed(() => sumTableColumnWidths(columns.value) + 96)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="shrink-0 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="page-h2">运单管理</h2>
        <p class="page-subtitle">
          共 {{ total }} 条
          <span v-if="batchShipmentSearchActive" class="text-violet-400">
            · 批量运单号 {{ shipmentNoTokens.length }} 个
          </span>
        </p>
      </div>
      <NSpace align="center">
        <NButton
          size="small"
          :loading="syncingTracking"
          title="同步转运中、未知、查验；已签收不查"
          @click="handleSyncTracking()"
        >
          更新全部内部轨迹
        </NButton>
        <NButton
          size="small"
          :loading="syncingCarrier"
          title="仅同步转运中运单，已签收不查"
          @click="handleSyncCarrierTracking()"
        >
          更新全部承运商轨迹
        </NButton>
        <NButton type="primary" size="small" @click="openCreate">新增运单</NButton>
        <NButton size="small" :loading="importing" @click="triggerImport">导入运单</NButton>
        <NButton size="small" :loading="exporting" @click="handleExport">导出运单</NButton>
      </NSpace>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls"
      class="hidden"
      @change="onFileSelected"
    />

    <ShipmentTrackingFreshnessBar
      :stats="freshnessStats"
      :no-internal-active="filterNoInternalTracking"
      :no-carrier-active="filterNoCarrierTracking"
      :carrier-ahead-active="filterCarrierAheadOfInternal"
      :pending-review-active="filterPendingTrackingTimeReview"
      :stale7-active="filterStaleDays === 7"
      :stale14-active="filterStaleDays === 14"
      :filtered-no-internal-count="filterNoInternalTracking && !loading ? total : null"
      :filtered-no-carrier-count="filterNoCarrierTracking && !loading ? total : null"
      :filtered-pending-review-count="filterPendingTrackingTimeReview && !loading ? total : null"
      :filtered-carrier-ahead-count="filterCarrierAheadOfInternal && !loading ? total : null"
      :filtered-stale7-count="filterStaleDays === 7 && !loading ? total : null"
      :filtered-stale14-count="filterStaleDays === 14 && !loading ? total : null"
      :carrier-sync-hint="carrierSyncHint"
      @toggle-no-internal="toggleNoInternalTrackingFilter"
      @toggle-no-carrier="toggleNoCarrierTrackingFilter"
      @toggle-carrier-ahead="toggleCarrierAheadFilter"
      @toggle-pending-review="togglePendingReviewFilter"
      @toggle-stale7="toggleStale7Filter"
      @toggle-stale14="toggleStale14Filter"
    />

    <div class="panel shipments-filters-bar shrink-0 px-3 py-2">
      <div class="flex min-w-0 flex-col gap-2">
        <div class="shipments-filter-search-row">
          <div class="shipments-filter-search-half">
            <NInput
              v-model:value="searchShipmentNo"
              type="textarea"
              placeholder="多号精确搜索：运单号、柜号、提单号、货件号、客户编号（逗号/空格/换行分隔，最多 200 个）"
              :autosize="{ minRows: 1, maxRows: 4 }"
              clearable
              size="small"
              class="shipments-filter-shipment-no"
            />
            <span
              v-if="shipmentNoTokens.length > 0"
              class="mt-1 shrink-0 rounded bg-violet-500/20 px-2 py-0.5 text-[10px] text-violet-200"
            >
              {{ shipmentNoTokens.length }} 个单号
            </span>
          </div>
          <NInput
            v-model:value="searchTrackingContent"
            placeholder="轨迹搜索"
            clearable
            size="small"
            class="shipments-filter-tracking"
            @keyup.enter="onFiltersChanged"
          />
        </div>
        <div class="shipments-filter-row flex min-w-0 flex-wrap items-center gap-2">
          <NSelect
            v-model:value="filterStatus"
            :options="statusOptions"
            placeholder="状态"
            clearable
            size="small"
            class="shipments-filter-select"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterChannelCode"
            :options="channelCodeOptions"
            placeholder="渠道"
            clearable
            filterable
            size="small"
            class="shipments-filter-select shipments-filter-select--wide"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="filterCustomer"
            :options="customerOptions"
            placeholder="客户"
            clearable
            filterable
            size="small"
            class="shipments-filter-select shipments-filter-select--customer"
            @update:value="onFiltersChanged"
          />
          <NSelect
            v-model:value="timeField"
            :options="timeFieldOptions"
            placeholder="时间口径"
            clearable
            size="small"
            class="shipments-filter-select shipments-filter-select--wide"
            @update:value="onFiltersChanged"
          />
          <NDatePicker
            v-model:value="timeRange"
            type="daterange"
            clearable
            size="small"
            class="shipments-filter-daterange"
            @update:value="onFiltersChanged"
          />
          <NCheckbox
            v-model:checked="filterFclOnly"
            size="small"
            class="shrink-0"
            @update:checked="onFiltersChanged"
          >
            整柜
          </NCheckbox>
          <NButton size="small" quaternary class="shrink-0" @click="advancedFilterShow = true">
            高级筛选
            <span
              v-if="advancedOnlyActiveCount > 0"
              class="ml-1 rounded bg-violet-500/25 px-1.5 text-[10px] text-violet-200"
            >
              {{ advancedOnlyActiveCount }}
            </span>
          </NButton>
          <NSelect
            :value="selectedSystemView"
            :options="systemViewOptions"
            placeholder="系统视图"
            clearable
            size="small"
            class="shipments-filter-select shipments-filter-select--wide"
            @update:value="(v) => (v ? applySystemView(v) : resetFilters())"
          />
          <NButton size="small" quaternary class="shrink-0" @click="columnSettingsShow = true">
            列设置
          </NButton>
          <NButton size="small" quaternary class="shrink-0" @click="resetFilters">重置</NButton>
          <NButton size="small" quaternary class="shrink-0" :loading="exporting" @click="handleExport">
            导出
          </NButton>
        </div>
      </div>
    </div>

    <ShipmentFilterSummaryBar
      :tags="filterSummaryTags"
      @remove="removeFilterTag"
      @clear="resetFilters"
    />

    <div class="panel shipments-table-panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable
        v-model:checked-row-keys="checkedRowKeys"
        :row-key="rowKey"
        :columns="columns"
        :data="items"
        :loading="loading"
        :scroll-x="tableScrollX"
        :scrollbar-props="tableScrollbarProps"
        size="small"
        flex-height
        class="shipments-data-table h-full"
        :bordered="false"
        @update:sorter="handleSorterChange"
      />
    </div>

    <div
      v-if="selectedCount > 0"
      class="shipments-selection-bar shrink-0 flex flex-wrap items-center justify-between gap-2 rounded-lg px-3 py-2"
    >
      <div class="flex flex-wrap items-center gap-2">
        <span class="shipments-selection-bar__label text-sm">
          已选
          <strong class="shipments-selection-bar__count">{{ selectedCount }}</strong>
          条（本页）
        </span>
        <NButton size="small" quaternary @click="clearSelection">取消选择</NButton>
      </div>
      <NSpace size="small">
        <NDropdown trigger="hover" :options="copyDropdownOptions" @select="handleCopyMenuSelect">
          <NButton size="small" title="复制选中运单号（换行）" @click="copySelectedShipmentNos">
            复制
          </NButton>
        </NDropdown>
        <NDropdown
          trigger="hover"
          :options="subscribeDropdownOptions"
          @select="handleSubscribeMenuSelect"
        >
          <NButton
            size="small"
            type="primary"
            :loading="batchSubmitting"
            title="批量订阅轨迹更新"
            @click="handleBatchSubscribe"
          >
            订阅
          </NButton>
        </NDropdown>
        <NDropdown
          trigger="hover"
          :options="batchEditDropdownOptions"
          @select="handleBatchEditMenuSelect"
        >
          <NButton
            size="small"
            :loading="batchSubmitting"
            @click="batchEditShow = true"
          >
            批量修改
          </NButton>
        </NDropdown>
        <NButton
          size="small"
          :loading="syncingTracking"
          title="含已签收；以 DPS 接口全量覆盖本地轨迹（删除源端已删节点）"
          @click="handleSyncSelectedInternal"
        >
          更新选中内部轨迹
        </NButton>
        <NButton
          size="small"
          type="primary"
          :loading="syncingCarrier"
          title="含已签收；按勾选运单号同步"
          @click="handleSyncSelectedCarrier"
        >
          更新选中承运商轨迹
        </NButton>
        <NButton
          size="small"
          :loading="syncingDps"
          title="从 DPS shipment_queryByOrder 拉取并更新选中运单"
          @click="handleSyncSelectedFromDps"
        >
          更新选中运单
        </NButton>
        <NDropdown trigger="hover" :options="groupDropdownOptions" @select="handleGroupMenuSelect">
          <NButton size="small" :loading="groupActionSubmitting" @click="openGroupAction('create')">
            分组
          </NButton>
        </NDropdown>
        <NDropdown
          trigger="hover"
          :options="exceptionDropdownOptions"
          @select="handleExceptionMenuSelect"
        >
          <NButton size="small" :loading="exceptionSubmitting">异常处理</NButton>
        </NDropdown>
      </NSpace>
    </div>

    <ShipmentBatchEditModal
      :show="batchEditShow"
      :count="selectedCount"
      :status-options="statusOptions"
      :channel-options="channelCodeOptions"
      :carrier-options="carrierOptions"
      :country-options="countryOptions"
      @close="batchEditShow = false"
      @submit="handleBatchEditSubmit"
    />

    <ShipmentGroupActionModal
      :show="groupActionShow"
      :mode="groupActionMode"
      :count="selectedCount"
      :member-group-options="selectedMemberGroupOptions"
      :default-customer="selectedRows[0]?.customer ?? null"
      @close="groupActionShow = false"
      @confirm-create="onGroupActionConfirmCreate"
      @confirm-group-id="onGroupActionConfirmGroupId"
    />

    <ShipmentGroupSuggestionsModal
      :show="groupSuggestionsShow"
      :shipment-ids="selectedIds"
      @close="groupSuggestionsShow = false"
      @applied="
        async () => {
          await loadFilterOptions()
          await loadList()
        }
      "
    />

    <ShipmentExceptionOpenModal
      :show="exceptionOpenShow"
      :count="selectedCount"
      :exception-types="filterOptions.exceptionTypes"
      @close="exceptionOpenShow = false"
      @confirm="handleOpenException"
    />
    <ShipmentExceptionCloseModal
      :show="exceptionCloseShow"
      :count="selectedCount"
      @close="exceptionCloseShow = false"
      @confirm="handleCloseException"
    />

    <div class="shrink-0 flex justify-end border-t border-[var(--color-border)] pt-3">
      <NPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :item-count="total"
        :page-sizes="[10, 20, 50, 100]"
        show-size-picker
        size="small"
      />
    </div>

    <ShipmentFormModal
      :show="modalShow"
      :mode="modalMode"
      :initial="editingRow"
      @close="modalShow = false"
      @submit="handleFormSubmit"
    />

    <ShipmentTrackingDrawer
      v-model:show="trackingDrawerShow"
      :shipment="trackingDrawerShipment"
      :initial-tab="trackingDrawerTab"
      :exception-label-by-code="exceptionLabelByCode"
      @shipment-updated="handleTrackingDrawerShipmentUpdated"
    />

    <ShipmentAdvancedFilterDrawer
      v-model:show="advancedFilterShow"
      v-model:filter-carrier="filterCarrier"
      v-model:filter-country="filterCountry"
      v-model:filter-channel-name-zh="filterChannelNameZh"
      v-model:filter-channel-category="filterChannelCategory"
      v-model:filter-customer-no="filterCustomerNo"
      v-model:adv-exact-shipment-no="advExactShipmentNo"
      v-model:adv-container-nos="advContainerNos"
      v-model:adv-bill-nos="advBillNos"
      v-model:adv-customer-shipment-ids="advCustomerShipmentIds"
      v-model:search-keyword="searchKeyword"
      v-model:filter-destination-port="filterDestinationPort"
      v-model:filter-address-keyword="filterAddressKeyword"
      v-model:filter-vessel-voyage="filterVesselVoyage"
      v-model:filter-vip-only="filterVipOnly"
      v-model:has-ata="hasAta"
      v-model:filter-exception="filterException"
      v-model:filter-payment-status="filterPaymentStatus"
      v-model:filter-has-exception="filterHasException"
      v-model:filter-stale-days="filterStaleDays"
      v-model:filter-no-internal-tracking="filterNoInternalTracking"
      v-model:filter-no-carrier-tracking="filterNoCarrierTracking"
      v-model:filter-no-zipcode="filterNoZipcode"
      v-model:filter-has-tracking-number="filterHasTrackingNumber"
      v-model:filter-group-id="filterGroupId"
      v-model:filter-group-no="filterGroupNo"
      v-model:filter-rule-type="filterRuleType"
      v-model:filter-has-group="filterHasGroup"
      v-model:filter-pending-tracking-time-review="filterPendingTrackingTimeReview"
      v-model:missing-etd="missingEtd"
      v-model:missing-atd="missingAtd"
      v-model:missing-eta="missingEta"
      v-model:missing-ata="missingAta"
      v-model:missing-expected-delivery="missingExpectedDelivery"
      v-model:missing-delivered="missingDelivered"
      v-model:not-delivered="notDelivered"
      v-model:delivery-risk="deliveryRisk"
      v-model:advanced-times="advancedTimes"
      :filter-options="filterOptions"
      :carrier-options="carrierOptions"
      :country-options="countryOptions"
      :channel-name-zh-options="channelNameZhOptions"
      :channel-category-options="channelCategoryOptions"
      :exception-filter-options="exceptionFilterOptions"
      :has-exception-filter-options="hasExceptionFilterOptions"
      :stale-options="staleOptions"
      :has-group-filter-options="hasGroupFilterOptions"
      :group-filter-options="groupFilterOptions"
      :rule-type-filter-options="ruleTypeFilterOptions"
      @apply="onFiltersChanged"
    />

    <ShipmentColumnSettingsDrawer
      v-model:show="columnSettingsShow"
      v-model:visible-keys="visibleColumnKeys"
    />
  </div>
</template>

<style scoped>
.shipments-filters-bar {
  border-radius: 0.5rem;
}

.shipments-filter-row > * {
  flex: 0 0 auto;
}

.shipments-filter-search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.5rem;
  align-items: start;
  min-width: 0;
}

.shipments-filter-search-half {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  gap: 0.5rem;
}

.shipments-filters-bar .shipments-filter-shipment-no {
  flex: 1 1 auto;
  min-width: 0;
  width: 100%;
}

.shipments-filters-bar .shipments-filter-tracking {
  min-width: 0;
  width: 100%;
}

.shipments-filters-bar .shipments-filter-keyword {
  width: 180px;
  min-width: 140px;
}

.shipments-filters-bar .shipments-filter-daterange {
  width: 240px;
  min-width: 200px;
}

.shipments-filters-bar .shipments-filter-select {
  width: 7.25rem;
  min-width: 6.5rem;
}

.shipments-filters-bar .shipments-filter-select--customer {
  width: 12rem;
  min-width: 10.5rem;
}

.shipments-filters-bar .shipments-filter-select--wide {
  width: 11rem;
  min-width: 9rem;
}

/* 左侧固定列：不透明 + 轻阴影，横滚时不与右侧双行轨迹叠字 */
.shipments-data-table :deep(.n-data-table-tbody .n-data-table-td--fixed-left) {
  background-color: var(--n-td-color) !important;
  z-index: 3;
  box-shadow: 6px 0 10px -6px rgb(0 0 0 / 0.45);
}

.shipments-data-table :deep(
    .n-data-table-tbody .n-data-table-tr:not(.n-data-table-tr--summary):hover > .n-data-table-td
  ) {
  background-color: var(--n-td-color-hover) !important;
}

.shipments-data-table :deep(
    .n-data-table-tbody
      .n-data-table-tr:not(.n-data-table-tr--summary):hover
      > .n-data-table-td--fixed-left
  ) {
  background-color: var(--n-td-color-hover) !important;
}

.shipments-data-table :deep(.shipment-td-no) {
  padding-right: 10px !important;
  overflow: hidden;
}

.shipments-data-table :deep(.shipment-no-cell-row) {
  display: inline-flex;
  max-width: 100%;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.shipments-data-table :deep(th.n-data-table-th--fixed-left) {
  background-color: var(--n-th-color) !important;
  z-index: 4;
}

.shipments-data-table :deep(.tracking-summary-cell) {
  line-height: 1.35;
}

.shipments-data-table :deep(.tracking-summary-btn) {
  border: none;
  background: transparent;
  font: inherit;
}

.shipments-data-table :deep(.tracking-summary-btn:hover) {
  background: var(--color-nav-hover);
}

.shipments-data-table :deep(.tracking-empty) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.tracking-time) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.tracking-time--faded) {
  color: var(--color-muted);
  opacity: 0.72;
}

.shipments-data-table :deep(.tracking-desc) {
  color: var(--color-fg);
}

.shipments-data-table :deep(.tracking-desc--faded) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.tracking-ahead-time) {
  color: var(--tracking-ahead-fg);
}

.shipments-data-table :deep(.tracking-ahead-desc) {
  color: var(--tracking-ahead-desc);
}

.shipments-data-table :deep(.tracking-ahead-badge) {
  border-radius: 4px;
  border: 1px solid var(--tracking-ahead-badge-border);
  background: var(--tracking-ahead-badge-bg);
  padding: 0 4px;
  font-size: 9px;
  font-weight: 500;
  color: var(--tracking-ahead-badge-fg);
}

.shipments-data-table :deep(.tracking-summary-btn--carrier-ahead) {
  border-left: 2px solid rgb(251 191 36 / 0.75);
  background: rgb(245 158 11 / 0.08);
  box-shadow: inset 0 0 0 1px rgb(245 158 11 / 0.12);
}

.shipments-data-table :deep(.tracking-summary-btn--carrier-ahead:hover) {
  background: rgb(245 158 11 / 0.14);
}

/* 内部相对滞后：略淡化，与承运高亮成对比 */
.shipments-data-table :deep(.tracking-summary-btn--internal-behind) {
  opacity: 0.82;
}

.shipments-data-table :deep(.shipment-no-cell) {
  display: inline-block;
  white-space: nowrap;
  word-break: keep-all;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.shipments-data-table :deep(.shipment-group-cell) {
  display: inline-flex;
  max-width: 100%;
  align-items: center;
  justify-content: center;
  flex-wrap: nowrap;
  white-space: nowrap;
  gap: 0.125rem;
}

.shipments-data-table :deep(.shipment-group-icon-cluster) {
  display: inline-flex;
  align-items: center;
  gap: 0.125rem;
}

.shipments-data-table :deep(.shipment-group-rule-icon-btn) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.125rem;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  cursor: pointer;
  line-height: 0;
  transition: background-color 0.15s ease;
}

.shipments-data-table :deep(.shipment-group-rule-icon-btn:hover) {
  background: var(--color-btn-ghost-bg);
}

.shipments-data-table :deep(.shipment-group-rule-icon) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.shipments-data-table :deep(.shipment-group-rule-icon__svg) {
  display: block;
}

.shipments-data-table :deep(.shipment-group-rule-icon--delivery) {
  color: var(--tag-warning-fg, #d97706);
}

.shipments-data-table :deep(.shipment-group-rule-icon--payment) {
  color: var(--color-accent-text, #6366f1);
}

.shipments-data-table :deep(.shipment-group-rule-icon--arrival) {
  color: #0ea5e9;
}

.shipments-data-table :deep(.shipment-group-rule-icon--default),
.shipments-data-table :deep(.shipment-group-rule-icon--placeholder) {
  color: var(--color-muted);
}

.shipments-data-table :deep(.shipment-group-cell-sep) {
  flex-shrink: 0;
  margin: 0 0.0625rem;
  color: var(--color-muted);
  user-select: none;
}

.shipments-data-table :deep(.last-mile-badge-btn) {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  padding: 0;
  border: none;
  background: transparent;
  font: inherit;
  line-height: 0;
}

.shipments-data-table :deep(.shipment-status-badge) {
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

.shipments-data-table :deep(.shipment-status-badge--default) {
  color: var(--tag-default-fg);
  background: var(--tag-default-bg);
}

.shipments-data-table :deep(.shipment-status-badge--warning) {
  color: var(--tag-warning-fg);
  background: var(--tag-warning-bg);
}

.shipments-data-table :deep(.shipment-status-badge--success) {
  color: var(--tag-success-fg);
  background: var(--tag-success-bg);
}

.shipments-data-table :deep(.shipment-status-badge--error) {
  color: var(--tag-error-fg);
  background: var(--tag-error-bg);
}

.shipments-selection-bar {
  border: 1px solid color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 14%, var(--color-elevated));
  color: var(--color-fg);
  box-shadow: var(--panel-inset-shadow);
}

.shipments-selection-bar__label {
  color: var(--color-fg);
  font-weight: 500;
}

.shipments-selection-bar__count {
  margin: 0 0.15em;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--color-fg-emphasis);
}

.shipments-table-panel {
  display: flex;
  flex-direction: column;
}

.shipments-table-panel :deep(.n-data-table) {
  flex: 1;
  min-height: 0;
}

/* Naive 滚动条圆角、弱化轨道占位 */
.shipments-table-panel :deep(.n-scrollbar-rail__scrollbar) {
  border-radius: 9999px !important;
}
</style>
