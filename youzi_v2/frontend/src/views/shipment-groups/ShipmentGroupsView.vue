<script setup lang="ts">
import {
  NButton,
  NDataTable,
  NEmpty,
  NInput,
  NSelect,
  NSpace,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listShipments } from '@/api/shipments'
import {
  evaluateShipmentGroupAlerts,
  getShipmentGroup,
  listShipmentGroupNotifications,
  listShipmentGroups,
  markAllShipmentGroupNotificationsRead,
  markShipmentGroupNotificationRead,
  resolveShipmentGroupNotification,
  updateShipmentGroup,
} from '@/api/shipmentGroups'
import type { Shipment } from '@/types/shipment'
import type { ShipmentGroup, ShipmentGroupDetail, ShipmentGroupNotification } from '@/types/shipmentGroup'
import {
  groupPrimaryType,
  shipmentGroupTypeLabel,
  shipmentGroupTypeSelectOptions,
  type ShipmentGroupType,
} from '@/constants/shipmentGroupTypes'
import ShipmentGroupTypeIcon from '@/components/shipments/ShipmentGroupTypeIcon.vue'
import ShipmentGroupTypeTags from '@/components/shipments/ShipmentGroupTypeTags.vue'
import {
  renderShipmentGroupTypeSelectLabel,
} from '@/utils/shipmentGroupTypeSelectRender'
import { formatRelativeTime } from '@/utils/formatDateTime'

const message = useMessage()
const router = useRouter()
const route = useRoute()

const loadingList = ref(false)
const loadingDetail = ref(false)
const evaluating = ref(false)
const groups = ref<ShipmentGroup[]>([])
const total = ref(0)
const search = ref('')
const filterGroupType = ref<string | null>(null)
const selectedId = ref<string | null>(null)
const detail = ref<ShipmentGroupDetail | null>(null)
const notifications = ref<ShipmentGroupNotification[]>([])
const memberShipments = ref<Shipment[]>([])
const loadingMembers = ref(false)

const paymentOptions = [
  { label: '未付', value: 'UNPAID' },
  { label: '部分', value: 'PARTIAL' },
  { label: '已付', value: 'PAID' },
]

const groupTypeOptions = shipmentGroupTypeSelectOptions()

const severityTag: Record<string, 'default' | 'warning' | 'error'> = {
  info: 'default',
  warning: 'warning',
  urgent: 'error',
}

const memberColumns: DataTableColumns<Shipment> = [
  {
    title: '运单号',
    key: 'shipmentNo',
    minWidth: 140,
    render: (row) =>
      h(
        'button',
        {
          type: 'button',
          class: 'text-[var(--color-accent-text)] hover:underline',
          onClick: () =>
            router.push({ path: '/shipments', query: { shipmentNo: row.shipmentNo } }),
        },
        row.shipmentNo,
      ),
  },
  { title: '客户', key: 'customer', ellipsis: { tooltip: true } },
  { title: '状态', key: 'statusCode', width: 88 },
  { title: '到港', key: 'ata', width: 108, render: (row) => row.ata?.slice(0, 10) || '—' },
  {
    title: '签收',
    key: 'deliveredTime',
    width: 108,
    render: (row) => row.deliveredTime?.slice(0, 10) || '—',
  },
]

async function loadGroups() {
  loadingList.value = true
  try {
    const res = await listShipmentGroups({
      search: search.value.trim() || undefined,
      groupType: filterGroupType.value || undefined,
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

async function handleTypesSave() {
  if (!selectedId.value || !detail.value) return
  if (!editGroupTypes.value.length) {
    message.warning('请至少选择一项业务类型')
    return
  }
  if (!editGroupTypes.value.includes(editPrimaryType.value)) {
    message.warning('主类型须包含在业务类型中')
    return
  }
  try {
    await updateShipmentGroup(selectedId.value, {
      primaryType: editPrimaryType.value,
      groupTypes: [...editGroupTypes.value],
    })
    message.success('分组类型已更新')
    await loadDetail(selectedId.value)
    await loadGroups()
  } catch (e) {
    message.error(e instanceof Error ? e.message : '更新失败')
  }
}

const editGroupTypes = ref<ShipmentGroupType[]>(['MANUAL'])
const editPrimaryType = ref<ShipmentGroupType>('MANUAL')

const primaryTypeOptions = computed(() =>
  groupTypeOptions.filter((o) => editGroupTypes.value.includes(o.value as ShipmentGroupType)),
)

watch(
  () => detail.value,
  (d) => {
    if (!d) return
    editGroupTypes.value = [...(d.groupTypes?.length ? d.groupTypes : [d.primaryType || d.groupType || 'MANUAL'])] as ShipmentGroupType[]
    editPrimaryType.value = groupPrimaryType(d)
  },
  { immediate: true },
)

watch(editGroupTypes, (types) => {
  if (!types.length) return
  if (!types.includes(editPrimaryType.value)) {
    editPrimaryType.value = types[0]
  }
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

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(loadGroups, 300)
})

watch(filterGroupType, () => {
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
      <aside class="flex w-72 shrink-0 flex-col border-r border-[var(--color-border)]">
        <div class="shrink-0 space-y-2 border-b border-[var(--color-border)] p-3">
          <NInput v-model:value="search" placeholder="搜索组号/名称/客户" clearable size="small" />
          <NSelect
            v-model:value="filterGroupType"
            :options="groupTypeOptions"
            :render-label="renderShipmentGroupTypeSelectLabel"
            consistent-menu-width
            placeholder="分组类型"
            clearable
            size="small"
            class="w-full"
          />
        </div>
        <div v-if="loadingList" class="p-4 text-sm text-[var(--color-muted)]">加载中…</div>
        <div v-else-if="!groups.length" class="p-4">
          <NEmpty description="暂无分组" size="small" />
        </div>
        <ul v-else class="min-h-0 flex-1 overflow-y-auto p-2">
          <li v-for="g in groups" :key="g.id">
            <button
              type="button"
              class="shipment-group-list-item"
              :class="{ 'shipment-group-list-item--active': selectedId === g.id }"
              @click="selectGroup(g.id)"
            >
              <div class="flex min-w-0 items-center gap-1.5">
                <ShipmentGroupTypeIcon
                  :type="groupPrimaryType(g)"
                  :size="14"
                  :title="shipmentGroupTypeLabel(groupPrimaryType(g))"
                />
                <span class="shipment-group-list-item__no">{{ g.groupNo }}</span>
                <span
                  v-if="g.groupName?.trim()"
                  class="shipment-group-list-item__name"
                  :title="g.groupName"
                >
                  {{ g.groupName }}
                </span>
              </div>
              <div class="shipment-group-list-item__meta">{{ g.memberCount ?? 0 }} 票</div>
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
            <div class="shrink-0 border-b border-[var(--color-border)] p-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-lg font-semibold text-[var(--color-fg-emphasis)]">
                    <ShipmentGroupTypeIcon :type="groupPrimaryType(detail)" :size="20" />
                    <span class="shrink-0 font-mono text-sm font-semibold tabular-nums text-[var(--color-accent-text)]">
                      {{ detail.groupNo }}
                    </span>
                    <span
                      v-if="detail.groupName?.trim()"
                      class="min-w-0 truncate"
                      :title="detail.groupName"
                    >
                      {{ detail.groupName }}
                    </span>
                  </h3>
                  <p class="mt-1 text-sm text-[var(--color-muted)]">
                    <span v-if="detail.customer">{{ detail.customer }}</span>
                    <span v-if="detail.customer && detail.vesselVoyage"> · </span>
                    <span v-if="detail.vesselVoyage">{{ detail.vesselVoyage }}</span>
                  </p>
                </div>
                <NSpace>
                  <NButton size="small" :loading="evaluating" @click="handleEvaluate">
                    重新计算提醒
                  </NButton>
                </NSpace>
              </div>

              <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
                <div class="shipment-group-stat-card">
                  <div class="text-xs text-[var(--color-muted)]">运单数</div>
                  <div class="text-lg font-semibold tabular-nums text-[var(--color-fg-emphasis)]">{{ detail.memberCount ?? 0 }}</div>
                </div>
                <div class="shipment-group-stat-card">
                  <div class="text-xs text-[var(--color-muted)]">已到港</div>
                  <div class="text-lg font-semibold tabular-nums text-[var(--color-fg-emphasis)]">{{ detail.arrivedCount ?? 0 }}</div>
                </div>
                <div class="shipment-group-stat-card">
                  <div class="text-xs text-[var(--color-muted)]">已签收</div>
                  <div class="text-lg font-semibold tabular-nums text-[var(--color-fg-emphasis)]">{{ detail.deliveredCount ?? 0 }}</div>
                </div>
                <div class="shipment-group-stat-card">
                  <div class="text-xs text-[var(--color-muted)]">未签收</div>
                  <div class="text-lg font-semibold tabular-nums text-[var(--color-fg-emphasis)]">
                    {{ detail.undeliveredCount ?? 0 }}
                  </div>
                </div>
                <div class="shipment-group-stat-card">
                  <div class="text-xs text-[var(--color-muted)]">未读提醒</div>
                  <div class="text-lg font-semibold tabular-nums text-[var(--tag-warning-fg)]">
                    {{ detail.unreadNotificationCount ?? 0 }}
                  </div>
                </div>
                <div class="shipment-group-stat-card sm:col-span-2">
                  <div class="mb-1 text-xs text-[var(--color-muted)]">业务类型</div>
                  <NSelect
                    v-model:value="editGroupTypes"
                    :options="groupTypeOptions"
                    :render-label="renderShipmentGroupTypeSelectLabel"
                    consistent-menu-width
                    size="small"
                    class="w-full min-w-0"
                    multiple
                    @update:value="handleTypesSave"
                  />
                </div>
                <div class="shipment-group-stat-card sm:col-span-2">
                  <div class="mb-1 text-xs text-[var(--color-muted)]">主类型</div>
                  <NSelect
                    v-model:value="editPrimaryType"
                    :options="primaryTypeOptions"
                    :render-label="renderShipmentGroupTypeSelectLabel"
                    consistent-menu-width
                    size="small"
                    class="w-full min-w-0"
                    @update:value="handleTypesSave"
                  />
                </div>
                <div class="shipment-group-stat-card sm:col-span-2 lg:col-span-6">
                  <div class="mb-1 text-xs text-[var(--color-muted)]">全部类型</div>
                  <ShipmentGroupTypeTags
                    :types="detail.groupTypes"
                    :primary-type="detail.primaryType || detail.groupType"
                  />
                </div>
                <div class="shipment-group-stat-card">
                  <div class="mb-1 text-xs text-[var(--color-muted)]">收款状态</div>
                  <NSelect
                    :value="detail.paymentStatus"
                    :options="paymentOptions"
                    size="small"
                    @update:value="handlePaymentChange"
                  />
                </div>
              </div>
            </div>

            <div class="grid min-h-0 flex-1 grid-rows-[auto_1fr] gap-0 overflow-hidden lg:grid-cols-2 lg:grid-rows-1">
              <div class="flex min-h-0 flex-col border-b border-[var(--color-border)] lg:border-b-0 lg:border-r">
                <div class="flex shrink-0 items-center justify-between border-b border-[var(--color-border)] px-4 py-2">
                  <span class="text-sm font-medium">组内提醒</span>
                  <NButton
                    v-if="(detail.unreadNotificationCount ?? 0) > 0"
                    size="tiny"
                    quaternary
                    @click="handleMarkAllRead"
                  >
                    全部已读
                  </NButton>
                </div>
                <div class="min-h-0 flex-1 overflow-y-auto p-3">
                  <NEmpty v-if="!notifications.length" description="暂无提醒" size="small" />
                  <ul v-else class="space-y-2">
                    <li
                      v-for="n in notifications"
                      :key="n.id"
                      class="rounded-lg border px-3 py-2 text-sm transition-colors"
                      :class="
                        n.resolvedAt
                          ? 'border-transparent bg-[var(--color-btn-ghost-bg)] opacity-60'
                          : n.readAt
                            ? 'border-transparent bg-[var(--color-btn-ghost-bg)] opacity-70'
                            : 'border-amber-500/30 bg-[var(--tag-warning-bg)]'
                      "
                    >
                      <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0 flex-1">
                          <div class="flex items-center gap-2">
                            <NTag :type="severityTag[n.severity] ?? 'warning'" size="small" :bordered="false">
                              {{ n.title }}
                            </NTag>
                            <span class="text-xs text-[var(--color-muted)]">{{
                              formatRelativeTime(n.triggeredAt)
                            }}</span>
                            <NTag v-if="n.resolvedAt" size="tiny" :bordered="false">已处理</NTag>
                          </div>
                          <p class="mt-1 text-[var(--color-fg-secondary)]">{{ n.message }}</p>
                        </div>
                        <NSpace v-if="!n.resolvedAt" size="small">
                          <NButton v-if="!n.readAt" size="tiny" quaternary @click="handleMarkRead(n)">
                            知道了
                          </NButton>
                          <NButton size="tiny" quaternary @click="handleResolve(n)">已处理</NButton>
                        </NSpace>
                      </div>
                    </li>
                  </ul>
                </div>
              </div>

              <div class="flex min-h-0 flex-col">
                <div class="shrink-0 border-b border-[var(--color-border)] px-4 py-2 text-sm font-medium">
                  组内运单
                </div>
                <div class="min-h-0 flex-1 overflow-hidden p-2">
                  <NDataTable
                    :columns="memberColumns"
                    :data="memberShipments"
                    :loading="loadingMembers"
                    size="small"
                    flex-height
                    class="h-full"
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
