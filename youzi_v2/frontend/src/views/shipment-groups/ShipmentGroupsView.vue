<script setup lang="ts">
import {
  NButton,
  NCheckbox,
  NDataTable,
  NDatePicker,
  NEmpty,
  NInput,
  NInputNumber,
  NPopconfirm,
  NSelect,
  NSpace,
  NTag,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { Package } from 'lucide-vue-next'
import { computed, h, onMounted, ref, watch } from 'vue'
import { formatGroupNoDisplay } from '@/utils/shipmentGroup'
import { useRoute, useRouter } from 'vue-router'
import { listShipments, updateShipment } from '@/api/shipments'
import {
  evaluateShipmentGroupAlerts,
  deleteShipmentGroup,
  getShipmentGroup,
  listShipmentGroupNotifications,
  listShipmentGroups,
  markAllShipmentGroupNotificationsRead,
  markShipmentGroupNotificationRead,
  replaceShipmentGroupRules,
  resolveShipmentGroupNotification,
  updateShipmentGroup,
} from '@/api/shipmentGroups'
import type { Shipment } from '@/types/shipment'
import type {
  ShipmentGroup,
  ShipmentGroupDetail,
  ShipmentGroupNotification,
  ShipmentGroupRuleInput,
} from '@/types/shipmentGroup'
import ShipmentGroupAlertCard from '@/components/shipments/ShipmentGroupAlertCard.vue'
import { ICON_STROKE } from '@/constants/icons'
import {
  SHIPMENT_GROUP_RULE_OPTIONS,
  defaultRuleDraft,
  shipmentGroupRuleHasDeadlineFields,
  shipmentGroupRuleHasEtaWarningFields,
  type ShipmentGroupRuleType,
} from '@/constants/shipmentGroupRules'
import {
  dateOnlyToTimestamp,
  formatDateOnlyForApi,
  formatTimestampForApi,
  parseDateTimeInput,
} from '@/utils/formatDateTime'

const message = useMessage()
const router = useRouter()
const route = useRoute()

const loadingList = ref(false)
const loadingDetail = ref(false)
const evaluating = ref(false)
const savingRules = ref(false)
const deletingGroup = ref(false)
const groups = ref<ShipmentGroup[]>([])
const total = ref(0)
const search = ref('')
type ListFilter = 'all' | 'hasRule' | 'pending'
const listFilter = ref<ListFilter>('all')
const selectedId = ref<string | null>(null)
const detail = ref<ShipmentGroupDetail | null>(null)
const notifications = ref<ShipmentGroupNotification[]>([])
const memberShipments = ref<Shipment[]>([])
const loadingMembers = ref(false)
const savingMemberField = ref<{ id: string; field: 'ata' | 'deliveredTime' } | null>(null)

const listFilterOptions: { value: ListFilter; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'hasRule', label: '启用规则' },
  { value: 'pending', label: '待处理' },
]

const enabledRuleTypes = ref<ShipmentGroupRuleType[]>([])
const ruleDrafts = ref<Record<string, ShipmentGroupRuleInput>>({})

const paymentOptions = [
  { label: '未付', value: 'UNPAID' },
  { label: '部分', value: 'PARTIAL' },
  { label: '已付', value: 'PAID' },
]

function deliveredTimeToTimestamp(value: string | null | undefined): number | null {
  const parsed = parseDateTimeInput(value)
  return parsed ? parsed.getTime() : null
}

function patchMemberStats() {
  if (!detail.value) return
  const items = memberShipments.value
  const delivered = items.filter(
    (s) => (s.deliveredTime ?? '').trim() || s.statusCode === 'DELIVERED',
  ).length
  detail.value.arrivedCount = items.filter((s) => (s.ata ?? '').trim()).length
  detail.value.deliveredCount = delivered
  detail.value.undeliveredCount = Math.max(0, items.length - delivered)
}

async function saveMemberAta(row: Shipment, ts: number | null) {
  const next = ts != null ? formatTimestampForApi(ts) : null
  const prevTs = dateOnlyToTimestamp(row.ata) ?? deliveredTimeToTimestamp(row.ata)
  const prev = prevTs != null ? formatTimestampForApi(prevTs) : null
  if (next === prev) return

  savingMemberField.value = { id: row.id, field: 'ata' }
  try {
    const updated = await updateShipment(row.id, { ata: next })
    const idx = memberShipments.value.findIndex((s) => s.id === row.id)
    if (idx >= 0) memberShipments.value[idx] = updated
    patchMemberStats()
    message.success('到港时间已更新')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新到港时间失败')
  } finally {
    savingMemberField.value = null
  }
}

async function saveMemberDeliveredTime(row: Shipment, ts: number | null) {
  const next = ts != null ? formatTimestampForApi(ts) : null
  const prevTs = deliveredTimeToTimestamp(row.deliveredTime)
  const prev = prevTs != null ? formatTimestampForApi(prevTs) : null
  if (next === prev) return

  savingMemberField.value = { id: row.id, field: 'deliveredTime' }
  try {
    const updated = await updateShipment(row.id, { deliveredTime: next })
    const idx = memberShipments.value.findIndex((s) => s.id === row.id)
    if (idx >= 0) memberShipments.value[idx] = updated
    patchMemberStats()
    message.success('签收时间已更新')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新签收时间失败')
  } finally {
    savingMemberField.value = null
  }
}

function memberStatusBadgeClass(code: string | null | undefined): string {
  const c = (code || 'UNKNOWN').toUpperCase()
  if (c === 'DELIVERED') return 'shipment-status-badge--success'
  if (c === 'INSPECTION') return 'shipment-status-badge--warning'
  if (c === 'IN_TRANSIT') return 'shipment-status-badge--warning'
  return 'shipment-status-badge--default'
}

function memberStatusLabel(code: string | null | undefined): string {
  const c = (code || 'UNKNOWN').toUpperCase()
  if (c === 'IN_TRANSIT') return 'TRANSIT'
  if (c === 'UNKNOWN') return 'PENDING'
  return c
}

function goToShipment(row: Shipment) {
  router.push({ path: '/shipments', query: { shipmentNo: row.shipmentNo } })
}

const hasEnabledRules = computed(() => enabledRuleTypes.value.length > 0)

const pendingNotifications = computed(() =>
  notifications.value.filter((n) => !n.resolvedAt),
)

const hasUnreadPending = computed(() =>
  pendingNotifications.value.some((n) => !n.readAt),
)

const detailCustomer = computed(() => detail.value?.customer?.trim() || '')
const detailGroupName = computed(() => {
  if (!detail.value) return ''
  const name = detail.value.groupName?.trim() || ''
  if (!name || name === detailCustomer.value) return ''
  return name
})

const memberColumns = computed<DataTableColumns<Shipment>>(() => [
  {
    title: '运单号',
    key: 'shipmentNo',
    minWidth: 172,
    cellProps: () => ({ class: 'shipment-group-td-no' }),
    render: (row) =>
      h(
        'button',
        {
          type: 'button',
          class: 'shipment-group-shipment-no',
          onClick: () => goToShipment(row),
        },
        row.shipmentNo,
      ),
  },
  { title: '客户', key: 'customer', minWidth: 100, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'statusCode',
    width: 92,
    align: 'center',
    render: (row) =>
      h(
        'span',
        { class: ['shipment-status-badge', memberStatusBadgeClass(row.statusCode)] },
        memberStatusLabel(row.statusCode),
      ),
  },
  {
    title: '到港',
    key: 'ata',
    width: 148,
    render: (row) =>
      h(NDatePicker, {
        value: dateOnlyToTimestamp(row.ata) ?? deliveredTimeToTimestamp(row.ata),
        type: 'datetime',
        clearable: true,
        size: 'small',
        placeholder: '选择日期',
        class: 'w-full min-w-[8.5rem]',
        format: 'yyyy-MM-dd HH:mm',
        disabled:
          savingMemberField.value?.id === row.id &&
          savingMemberField.value.field === 'deliveredTime',
        onUpdateValue: (v: number | null) => {
          void saveMemberAta(row, v)
        },
      }),
  },
  {
    title: '签收',
    key: 'deliveredTime',
    width: 148,
    render: (row) =>
      h(NDatePicker, {
        value: deliveredTimeToTimestamp(row.deliveredTime),
        type: 'datetime',
        clearable: true,
        size: 'small',
        placeholder: '选择日期',
        class: 'w-full min-w-[8.5rem]',
        format: 'yyyy-MM-dd HH:mm',
        disabled:
          savingMemberField.value?.id === row.id && savingMemberField.value.field === 'ata',
        onUpdateValue: (v: number | null) => {
          void saveMemberDeliveredTime(row, v)
        },
      }),
  },
  {
    title: '操作',
    key: 'actions',
    width: 72,
    align: 'center',
    render: (row) =>
      h(
        'button',
        {
          type: 'button',
          class: 'shipment-group-member-action',
          onClick: () => goToShipment(row),
        },
        '详情',
      ),
  },
])

function syncRuleDraftsFromDetail(d: ShipmentGroupDetail) {
  const drafts: Record<string, ShipmentGroupRuleInput> = {}
  const enabled: ShipmentGroupRuleType[] = []
  const normalizeRuleType = (rt: string) =>
    rt === 'LAST_BATCH_ARRIVED_PAYMENT' ? 'GROUP_ARRIVED_PAYMENT' : rt
  for (const opt of SHIPMENT_GROUP_RULE_OPTIONS) {
    const existing = d.rules?.find((r) => normalizeRuleType(r.ruleType) === opt.value)
    if (existing) {
      drafts[opt.value] = {
        ruleType: opt.value,
        enabled: existing.enabled,
        thresholdDays: existing.thresholdDays,
        warningDays: existing.warningDays,
        triggerStatus: existing.triggerStatus,
        configJson: existing.configJson,
      }
      if (existing.enabled) enabled.push(opt.value)
    } else {
      drafts[opt.value] = defaultRuleDraft(opt.value)
    }
  }
  ruleDrafts.value = drafts
  enabledRuleTypes.value = enabled
}

function toggleRule(ruleType: ShipmentGroupRuleType, checked: boolean) {
  if (checked) {
    if (!enabledRuleTypes.value.includes(ruleType)) {
      enabledRuleTypes.value.push(ruleType)
    }
    if (!ruleDrafts.value[ruleType]) {
      ruleDrafts.value[ruleType] = defaultRuleDraft(ruleType)
    }
    ruleDrafts.value[ruleType].enabled = true
  } else {
    enabledRuleTypes.value = enabledRuleTypes.value.filter((t) => t !== ruleType)
    if (ruleDrafts.value[ruleType]) {
      ruleDrafts.value[ruleType].enabled = false
    }
  }
}

function buildRulesPayload(): ShipmentGroupRuleInput[] {
  return SHIPMENT_GROUP_RULE_OPTIONS.map((opt) => {
    const draft = ruleDrafts.value[opt.value] ?? defaultRuleDraft(opt.value)
    const enabled = enabledRuleTypes.value.includes(opt.value)
    return {
      ...draft,
      ruleType: opt.value,
      enabled,
    }
  }).filter((r) => r.enabled)
}

async function loadGroups() {
  loadingList.value = true
  try {
    const res = await listShipmentGroups({
      search: search.value.trim() || undefined,
      hasRule: listFilter.value === 'hasRule' ? true : undefined,
      hasUnread: listFilter.value === 'pending' ? true : undefined,
      limit: 100,
      offset: 0,
    })
    groups.value = res.items
    total.value = res.total
    if (!selectedId.value && res.items.length) {
      selectedId.value = res.items[0].id
    } else if (selectedId.value && !res.items.some((g) => g.id === selectedId.value)) {
      selectedId.value = res.items[0]?.id ?? null
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载分组失败')
  } finally {
    loadingList.value = false
  }
}

async function loadDetail(id: string) {
  loadingDetail.value = true
  try {
    detail.value = await getShipmentGroup(id)
    syncRuleDraftsFromDetail(detail.value)
    const notifRes = await listShipmentGroupNotifications(id, { limit: 50 })
    notifications.value = notifRes.items
    await loadMemberShipments(id)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载详情失败')
    detail.value = null
    notifications.value = []
    memberShipments.value = []
  } finally {
    loadingDetail.value = false
  }
}

async function loadMemberShipments(groupId: string) {
  loadingMembers.value = true
  try {
    const res = await listShipments({ groupId, limit: 200, offset: 0 })
    memberShipments.value = res.items
  } catch {
    memberShipments.value = []
  } finally {
    loadingMembers.value = false
  }
}

async function handleEvaluate() {
  if (!selectedId.value) return
  evaluating.value = true
  try {
    const res = await evaluateShipmentGroupAlerts(selectedId.value)
    message.success(`已评估，新增 ${res.created} 条提醒`)
    await loadDetail(selectedId.value)
    await loadGroups()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '评估失败')
  } finally {
    evaluating.value = false
  }
}

async function handlePaymentChange(val: string) {
  if (!selectedId.value || !detail.value) return
  try {
    await updateShipmentGroup(selectedId.value, { paymentStatus: val })
    message.success('收款状态已更新')
    await loadDetail(selectedId.value)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新失败')
  }
}

async function handleRulesSave() {
  if (!selectedId.value) return
  savingRules.value = true
  try {
    await replaceShipmentGroupRules(selectedId.value, buildRulesPayload())
    message.success('组规则已保存')
    await loadDetail(selectedId.value)
    await loadGroups()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存规则失败')
  } finally {
    savingRules.value = false
  }
}

const rulesDirty = computed(() => {
  if (!detail.value) return false
  const current = buildRulesPayload()
  const existing = (detail.value.rules ?? []).filter((r) => r.enabled)
  if (current.length !== existing.length) return true
  for (const rule of current) {
    const prev = existing.find(
      (r) =>
        (r.ruleType === 'LAST_BATCH_ARRIVED_PAYMENT'
          ? 'GROUP_ARRIVED_PAYMENT'
          : r.ruleType) === rule.ruleType,
    )
    if (!prev) return true
    if (prev.thresholdDays !== rule.thresholdDays) return true
    if (prev.warningDays !== rule.warningDays) return true
  }
  return false
})

async function handleMarkRead(n: ShipmentGroupNotification) {
  if (n.readAt) return
  try {
    await markShipmentGroupNotificationRead(n.id)
    await loadDetail(selectedId.value!)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '标记已读失败')
  }
}

async function handleResolve(n: ShipmentGroupNotification) {
  if (n.resolvedAt) return
  try {
    await resolveShipmentGroupNotification(n.id)
    await loadDetail(selectedId.value!)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '标记处理失败')
  }
}

async function handleMarkAllRead() {
  if (!selectedId.value) return
  try {
    const count = await markAllShipmentGroupNotificationsRead(selectedId.value)
    message.success(count ? `已标记 ${count} 条已读` : '暂无未读提醒')
    await loadDetail(selectedId.value)
    await loadGroups()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '操作失败')
  }
}

function selectGroup(id: string) {
  selectedId.value = id
}

async function handleDeleteGroup() {
  if (!selectedId.value || !detail.value) return
  deletingGroup.value = true
  const deletedId = selectedId.value
  const label = formatGroupNoDisplay(detail.value.groupNo)
  try {
    await deleteShipmentGroup(deletedId)
    message.success(`已删除分组 ${label}`)
    selectedId.value = null
    detail.value = null
    notifications.value = []
    memberShipments.value = []
    void router.replace({ path: '/shipment-groups' })
    await loadGroups()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '删除分组失败')
  } finally {
    deletingGroup.value = false
  }
}

function groupCardTitle(g: ShipmentGroup): string {
  return g.groupName?.trim() || g.customer?.trim() || formatGroupNoDisplay(g.groupNo)
}

function groupStatusDotClass(g: ShipmentGroup): string {
  if ((g.unreadNotificationCount ?? 0) > 0) return 'shipment-group-card__dot--alert'
  if ((g.enabledRules?.length ?? 0) > 0) return 'shipment-group-card__dot--active'
  return ''
}

function formatGroupMemberCount(count: number): string {
  return String(count).padStart(2, '0')
}

function setListFilter(next: ListFilter) {
  if (listFilter.value === next) return
  listFilter.value = next
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadGroups, 300)
})

watch(listFilter, () => {
  void loadGroups()
})

watch(selectedId, (id) => {
  if (id) void loadDetail(id)
  else {
    detail.value = null
    notifications.value = []
    memberShipments.value = []
  }
})

function applyRouteGroupId() {
  const q = route.query.groupId
  if (typeof q === 'string' && q.trim()) {
    selectedId.value = q.trim()
  }
}

watch(
  () => route.query.groupId,
  () => applyRouteGroupId(),
)


onMounted(async () => {
  await loadGroups()
  applyRouteGroupId()
  if (selectedId.value) await loadDetail(selectedId.value)
})
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <div class="shrink-0 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="page-h2">运单分组</h2>
        <p class="page-subtitle">共 {{ total }} 个分组 · 签收期限与到港催款提醒</p>
      </div>
    </div>

    <div class="panel flex min-h-0 flex-1 overflow-hidden p-0">
      <aside class="shipment-group-sidebar flex shrink-0 flex-col border-r border-[var(--color-border)]">
        <div class="shrink-0 space-y-3 border-b border-[var(--color-border)] p-3">
          <NInput v-model:value="search" placeholder="搜索分组ID…" clearable size="small" />
          <div class="shipment-group-filter-chips">
            <button
              v-for="opt in listFilterOptions"
              :key="opt.value"
              type="button"
              class="shipment-group-filter-chip"
              :class="{ 'shipment-group-filter-chip--active': listFilter === opt.value }"
              @click="setListFilter(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
        </div>
        <div v-if="loadingList" class="p-4 text-sm text-[var(--color-muted)]">加载中…</div>
        <div v-else-if="!groups.length" class="p-4">
          <NEmpty description="暂无分组" size="small" />
        </div>
        <ul v-else class="min-h-0 flex-1 overflow-y-auto scrollbar-subtle shipment-group-card-list">
          <li v-for="g in groups" :key="g.id">
            <button
              type="button"
              class="shipment-group-card"
              :class="{ 'shipment-group-card--active': selectedId === g.id }"
              @click="selectGroup(g.id)"
            >
              <div class="shipment-group-card__head">
                <span class="shipment-group-card__no">{{ formatGroupNoDisplay(g.groupNo) }}</span>
                <span
                  class="shipment-group-card__dot"
                  :class="groupStatusDotClass(g)"
                  :title="
                    (g.unreadNotificationCount ?? 0) > 0
                      ? `${g.unreadNotificationCount} 条未读提醒`
                      : (g.enabledRules?.length ?? 0) > 0
                        ? '已启用规则'
                        : undefined
                  "
                />
              </div>
              <h4 class="shipment-group-card__title">{{ groupCardTitle(g) }}</h4>
              <div class="shipment-group-card__foot">
                <span class="shipment-group-card__count">
                  <Package class="shipment-group-card__count-icon" :stroke-width="ICON_STROKE" />
                  {{ formatGroupMemberCount(g.memberCount ?? 0) }} 运单
                </span>
              </div>
            </button>
          </li>
        </ul>
      </aside>

      <section class="flex min-w-0 flex-1 flex-col overflow-hidden">
        <div v-if="!selectedId" class="flex flex-1 items-center justify-center">
          <NEmpty description="请选择左侧分组" />
        </div>
        <template v-else>
          <div
            v-if="loadingDetail && !detail"
            class="flex flex-1 items-center justify-center text-sm text-[var(--color-muted)]"
          >
            加载详情…
          </div>
          <template v-else-if="detail">
            <div class="shipment-group-detail shrink-0 border-b border-[var(--color-border)] p-4">
              <div class="shipment-group-detail__head">
                <div class="min-w-0 flex-1">
                  <div class="shipment-group-detail__title-row">
                    <span class="shipment-group-detail__no">{{ formatGroupNoDisplay(detail.groupNo) }}</span>
                    <NTag
                      v-if="detailCustomer"
                      size="small"
                      :bordered="false"
                      class="shipment-group-detail__customer-tag"
                    >
                      {{ detailCustomer }}
                    </NTag>
                    <NTag
                      v-if="hasEnabledRules"
                      size="small"
                      :bordered="false"
                      type="info"
                      class="shipment-group-detail__rule-tag"
                    >
                      启用规则
                    </NTag>
                  </div>
                  <p v-if="detailGroupName" class="shipment-group-detail__group-name">
                    {{ detailGroupName }}
                  </p>
                </div>
                <NPopconfirm
                  @positive-click="handleDeleteGroup"
                >
                  <template #trigger>
                    <NButton size="small" type="error" quaternary :loading="deletingGroup">
                      删除分组
                    </NButton>
                  </template>
                  确定删除分组「{{ formatGroupNoDisplay(detail.groupNo) }}」？组内运单不会被删除，仅解除分组关系。
                </NPopconfirm>
              </div>

              <div class="shipment-group-detail__stats">
                <div class="shipment-group-detail__stat">
                  <span class="shipment-group-detail__stat-label">运单数</span>
                  <span class="shipment-group-detail__stat-value">{{ detail.memberCount ?? 0 }}</span>
                </div>
                <div class="shipment-group-detail__stat">
                  <span class="shipment-group-detail__stat-label">已到港</span>
                  <span class="shipment-group-detail__stat-value">{{ detail.arrivedCount ?? 0 }}</span>
                </div>
                <div class="shipment-group-detail__stat">
                  <span class="shipment-group-detail__stat-label">已签收</span>
                  <span class="shipment-group-detail__stat-value">{{ detail.deliveredCount ?? 0 }}</span>
                </div>
                <div class="shipment-group-detail__stat">
                  <span class="shipment-group-detail__stat-label">未签收</span>
                  <span class="shipment-group-detail__stat-value">{{ detail.undeliveredCount ?? 0 }}</span>
                </div>
                <div class="shipment-group-detail__stat">
                  <span class="shipment-group-detail__stat-label">未读提醒</span>
                  <span
                    class="shipment-group-detail__stat-value shipment-group-detail__stat-value--alert"
                  >
                    {{ detail.unreadNotificationCount ?? 0 }}
                  </span>
                </div>
                <div class="shipment-group-detail__stat shipment-group-detail__stat--payment">
                  <span class="shipment-group-detail__stat-label">收款状态</span>
                  <NSelect
                    :value="detail.paymentStatus"
                    :options="paymentOptions"
                    size="small"
                    class="shipment-group-detail__payment-select"
                    @update:value="handlePaymentChange"
                  />
                </div>
              </div>

              <div class="shipment-group-rules-panel">
                <div class="shipment-group-rules-panel__head">
                  <span class="shipment-group-rules-panel__title">组规则</span>
                  <NButton
                    size="tiny"
                    type="primary"
                    :loading="savingRules"
                    :disabled="!rulesDirty"
                    @click="handleRulesSave"
                  >
                    保存规则
                  </NButton>
                </div>
                <div class="shipment-group-rules-panel__body">
                  <div
                    v-for="opt in SHIPMENT_GROUP_RULE_OPTIONS"
                    :key="opt.value"
                    class="shipment-group-rule-row"
                  >
                    <NCheckbox
                      :checked="enabledRuleTypes.includes(opt.value)"
                      @update:checked="(v: boolean) => toggleRule(opt.value, v)"
                    >
                      {{ opt.label }}
                    </NCheckbox>
                    <div
                      v-if="
                        enabledRuleTypes.includes(opt.value) &&
                        shipmentGroupRuleHasDeadlineFields(opt.value)
                      "
                      class="shipment-group-rule-row__fields"
                    >
                      <label class="shipment-group-rule-field">
                        <span class="shipment-group-rule-field__label">期限 (天)</span>
                        <NInputNumber
                          v-model:value="ruleDrafts[opt.value].thresholdDays"
                          :min="1"
                          :show-button="false"
                          size="small"
                          class="shipment-group-rule-field__input"
                        />
                      </label>
                      <label class="shipment-group-rule-field">
                        <span class="shipment-group-rule-field__label">提前提醒 (天)</span>
                        <NInputNumber
                          v-model:value="ruleDrafts[opt.value].warningDays"
                          :min="0"
                          :show-button="false"
                          size="small"
                          class="shipment-group-rule-field__input"
                        />
                      </label>
                    </div>
                    <div
                      v-else-if="
                        enabledRuleTypes.includes(opt.value) &&
                        shipmentGroupRuleHasEtaWarningFields(opt.value)
                      "
                      class="shipment-group-rule-row__fields"
                    >
                      <label class="shipment-group-rule-field">
                        <span class="shipment-group-rule-field__label">到港前提醒 (天)</span>
                        <NInputNumber
                          v-model:value="ruleDrafts[opt.value].warningDays"
                          :min="1"
                          :show-button="false"
                          size="small"
                          class="shipment-group-rule-field__input"
                        />
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="shipment-group-detail-split grid min-h-0 flex-1 gap-0 overflow-hidden">
              <div
                class="flex min-h-0 flex-col border-b border-[var(--color-border)] lg:border-b-0 lg:border-r"
              >
                <div class="shipment-group-panel-head">
                  <span class="shipment-group-panel-head__title">提醒与待处理</span>
                  <NSpace size="small">
                    <NButton size="tiny" quaternary :loading="evaluating" @click="handleEvaluate">
                      重新计算
                    </NButton>
                    <NButton
                      v-if="(detail.unreadNotificationCount ?? 0) > 0"
                      size="tiny"
                      quaternary
                      @click="handleMarkAllRead"
                    >
                      全部已读
                    </NButton>
                  </NSpace>
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto p-2.5 scrollbar-subtle">
                  <ul v-if="pendingNotifications.length" class="space-y-2.5">
                    <li v-for="n in pendingNotifications" :key="n.id">
                      <ShipmentGroupAlertCard
                        compact
                        :title="n.title"
                        :message="n.message"
                        :customer-name="n.customer || detailCustomer"
                        :rule-type="n.ruleType"
                        :triggered-at="n.triggeredAt"
                        :severity="n.severity"
                        :read="Boolean(n.readAt)"
                        :resolved="Boolean(n.resolvedAt)"
                      >
                        <template #aside>
                          <template v-if="!n.resolvedAt">
                            <button
                              v-if="!n.readAt"
                              type="button"
                              class="group-alert-card__btn"
                              @click="handleMarkRead(n)"
                            >
                              知道了
                            </button>
                            <button
                              type="button"
                              class="group-alert-card__btn group-alert-card__btn--ghost"
                              @click="handleResolve(n)"
                            >
                              已处理
                            </button>
                          </template>
                          <span v-else class="group-alert-card__status">已处理</span>
                        </template>
                      </ShipmentGroupAlertCard>
                    </li>
                  </ul>
                  <div v-if="!hasUnreadPending" class="shipment-group-alerts-empty">
                    暂无新的提醒
                  </div>
                </div>
              </div>

              <div class="flex min-h-0 flex-col">
                <div class="shipment-group-panel-head">
                  <span class="shipment-group-panel-head__title">组内运单</span>
                </div>
                <div class="min-h-0 flex-1 overflow-hidden p-3">
                  <NDataTable
                    :columns="memberColumns"
                    :data="memberShipments"
                    :loading="loadingMembers"
                    size="small"
                    flex-height
                    :scroll-x="820"
                    class="h-full shipment-group-members-table"
                    :bordered="false"
                  />
                </div>
              </div>
            </div>
          </template>
        </template>
      </section>
    </div>
  </div>
</template>

<style scoped>
.shipment-group-members-table :deep(.shipment-group-td-no) {
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
}

.shipment-group-shipment-no {
  display: inline-block;
  max-width: none;
  border: none;
  background: transparent;
  padding: 0;
  font-family: inherit;
  font-size: inherit;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.35;
  white-space: nowrap;
  word-break: keep-all;
  color: var(--color-accent-text);
  cursor: pointer;
  text-align: left;
}

.shipment-group-shipment-no:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.shipment-group-members-table :deep(.shipment-status-badge) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 4.25rem;
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 10px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.shipment-group-members-table :deep(.shipment-status-badge--default) {
  color: var(--tag-default-fg);
  background: var(--tag-default-bg);
}

.shipment-group-members-table :deep(.shipment-status-badge--warning) {
  color: var(--tag-warning-fg);
  background: var(--tag-warning-bg);
}

.shipment-group-members-table :deep(.shipment-status-badge--success) {
  color: var(--tag-success-fg);
  background: var(--tag-success-bg);
}
</style>
