<script setup lang="ts">
import { NButton, NCheckbox, NDrawer, NDrawerContent, NInput, NPopover, NSelect, NSwitch, NTag, useMessage } from 'naive-ui'
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  getOrderFlowLogs,
  getOrderFlowSummary,
  listOrderFlow,
  listOrderFlowCustomers,
  listOrderFlowStatuses,
  listOrderFlowChannels,
  listOrderFlowCountries,
  listOrderFlowWarehouses,
  markOrderFlowListSeen,
  refreshOrderFlow,
  type OrderFlowLog,
  updateOrderFlowSettings,
  type OrderFlowItem,
  type OrderFlowScope,
} from '@/api/orderFlow'
import { useOrderFlowTodoCount } from '@/composables/useOrderFlowTodoCount'
import { apiErrorMessage } from '@/utils/apiError'
import { formatRelativeTime } from '@/utils/formatDateTime'

const route = useRoute()
const message = useMessage()
const { refreshOrderFlowTodoCount } = useOrderFlowTodoCount()

const scope = ref<OrderFlowScope>('mine')
const search = ref('')
const items = ref<OrderFlowItem[]>([])
const loading = ref(false)
const refreshing = ref(false)
const pollEnabled = ref(false)
const mineCount = ref(0)
const activeCount = ref(0)
const endedCount = ref(0)
const changedCount = ref(0)

const selected = ref<string[]>([])
const statusFilter = ref<string | null>(null)
const customerFilter = ref<string | null>(null)
const warehouseFilter = ref<string | null>(null)
const countryFilter = ref<string | null>(null)
const channelFilter = ref<string[]>([])
const statuses = ref<string[]>([])
const customers = ref<string[]>([])
const warehouses = ref<string[]>([])
const countries = ref<string[]>([])
const channels = ref<string[]>([])
const logShow = ref(false)
const logWaybill = ref('')
const logs = ref<OrderFlowLog[]>([])
const logCache = ref<Record<string, OrderFlowLog[]>>({})
const logLoading = ref<Record<string, boolean>>({})
const listSeenAt = ref<string | null>(null)
let visitOpen = false

const scopes: { value: OrderFlowScope; label: string }[] = [
  { value: 'remind', label: '提醒' },
  { value: 'mine', label: '待处理' },
  { value: 'active', label: '流转中' },
  { value: 'ended', label: '已结束' },
  { value: 'all', label: '全部' },
]

const allChecked = computed(
  () => items.value.length > 0 && items.value.every((row) => selected.value.includes(row.waybillNo)),
)
const someChecked = computed(
  () => items.value.some((row) => selected.value.includes(row.waybillNo)) && !allChecked.value,
)

async function loadFilters() {
  try {
    const [statusRes, customerRes, warehouseRes, countryRes, channelRes] = await Promise.all([
      listOrderFlowStatuses(),
      listOrderFlowCustomers(),
      listOrderFlowWarehouses(),
      listOrderFlowCountries(),
      listOrderFlowChannels(),
    ])
    statuses.value = statusRes.items
    customers.value = customerRes.items
    warehouses.value = warehouseRes.items
    countries.value = countryRes.items
    channels.value = channelRes.items
  } catch {
    statuses.value = []
    customers.value = []
    warehouses.value = []
    countries.value = []
    channels.value = []
  }
}

function showNew(row: OrderFlowItem) {
  if (listSeenAt.value === null || !row.statusChanged) return false
  if (!listSeenAt.value) return true
  return (row.statusChangedAt || '') > listSeenAt.value
}

async function enterVisit() {
  if (visitOpen) return
  visitOpen = true
  try {
    const summary = await getOrderFlowSummary()
    listSeenAt.value = summary.listSeenAt || ''
  } catch {
    listSeenAt.value = listSeenAt.value ?? ''
  }
}

function leaveVisit() {
  if (!visitOpen) return
  visitOpen = false
  void markOrderFlowListSeen()
}

function operateLabel(value: string) {
  return formatRelativeTime(value)?.relative || showText(value)
}

function currentLogIndex(row: OrderFlowItem, items: OrderFlowLog[]) {
  const target = row.ended ? '已结束' : row.currentStatus
  for (let index = items.length - 1; index >= 0; index -= 1) {
    if (items[index]?.status === target) return index
  }
  return items.length - 1
}

function isCurrentLog(row: OrderFlowItem | undefined, items: OrderFlowLog[], index: number) {
  if (!items.length) return false
  if (!row) return index === items.length - 1
  return index === currentLogIndex(row, items)
}

async function ensureLogs(waybillNo: string) {
  if (logCache.value[waybillNo] || logLoading.value[waybillNo]) return
  logLoading.value = { ...logLoading.value, [waybillNo]: true }
  try {
    const res = await getOrderFlowLogs(waybillNo)
    logCache.value = { ...logCache.value, [waybillNo]: res.items }
  } catch (error) {
    message.error(apiErrorMessage(error, '加载轨迹失败'))
  } finally {
    logLoading.value = { ...logLoading.value, [waybillNo]: false }
  }
}

async function openLogs(waybillNo: string) {
  logWaybill.value = waybillNo
  logShow.value = true
  logs.value = logCache.value[waybillNo] || []
  try {
    const res = await getOrderFlowLogs(waybillNo)
    logs.value = res.items
    logCache.value = { ...logCache.value, [waybillNo]: res.items }
  } catch (error) {
    message.error(apiErrorMessage(error, '加载节点记录失败'))
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listOrderFlow({
      scope: scope.value,
      search: search.value.trim() || undefined,
      status: statusFilter.value || undefined,
      customer: customerFilter.value || undefined,
      warehouse: warehouseFilter.value || undefined,
      country: countryFilter.value || undefined,
      channel: channelFilter.value.length ? channelFilter.value : undefined,
    })
    items.value = res.items
    logCache.value = {}
    mineCount.value = res.mineCount
    activeCount.value = res.activeCount
    endedCount.value = res.endedCount
    changedCount.value = res.changedCount
    pollEnabled.value = res.orderFlowPollEnabled
    await refreshOrderFlowTodoCount()
  } catch (error) {
    message.error(apiErrorMessage(error, '加载失败'))
  } finally {
    loading.value = false
  }
}

async function onRefresh() {
  refreshing.value = true
  try {
    const res = await refreshOrderFlow()
    message.success(
      `已刷新：新增 ${res.created ?? 0}，状态变化 ${res.changed ?? 0}，结束 ${res.ended ?? 0}`,
    )
    await load()
    await loadFilters()
  } catch (error) {
    message.error(apiErrorMessage(error, '刷新失败'))
  } finally {
    refreshing.value = false
  }
}

async function onTogglePoll(enabled: boolean) {
  try {
    const res = await updateOrderFlowSettings(enabled)
    pollEnabled.value = res.orderFlowPollEnabled
    message.success(enabled ? '已开启，每 5 分钟刷新' : '已关闭定时刷新')
  } catch (error) {
    pollEnabled.value = !enabled
    message.error(apiErrorMessage(error, '保存失败'))
  }
}

function showText(value: string) {
  return value || '—'
}

function toggleRow(waybillNo: string, checked: boolean) {
  if (checked) {
    if (!selected.value.includes(waybillNo)) selected.value = [...selected.value, waybillNo]
    return
  }
  selected.value = selected.value.filter((item) => item !== waybillNo)
}

function toggleAll(checked: boolean) {
  const visible = items.value.map((row) => row.waybillNo)
  if (checked) {
    selected.value = [...new Set([...selected.value, ...visible])]
    return
  }
  selected.value = selected.value.filter((item) => !visible.includes(item))
}

async function copySelected() {
  if (!selected.value.length) return
  try {
    await navigator.clipboard.writeText(selected.value.join('\n'))
    message.success(`已复制 ${selected.value.length} 个单号`)
  } catch {
    message.error('复制失败')
  }
}

function applyScopeQuery() {
  const value = String(route.query.scope || '')
  if (value === 'mine' || value === 'active' || value === 'ended' || value === 'all' || value === 'remind') {
    scope.value = value
  }
  statusFilter.value = String(route.query.status || '') || null
}

function selectScope(value: OrderFlowScope) {
  statusFilter.value = null
  scope.value = value
}

watch(scope, () => void load())
watch([statusFilter, customerFilter, warehouseFilter, countryFilter, channelFilter], () => void load())
watch(() => [route.query.scope, route.query.status], applyScopeQuery)

onMounted(() => {
  applyScopeQuery()
  void loadFilters()
  void load()
  void enterVisit()
})
onActivated(() => {
  void enterVisit()
})
onDeactivated(leaveVisit)
onUnmounted(leaveVisit)
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3 p-4">
    <div class="flex shrink-0 flex-wrap items-end justify-between gap-3">
      <h1 class="page-h2">订单流转</h1>
      <div class="flex flex-wrap items-center gap-3">
        <label class="flex items-center gap-2 text-sm">
          <NSwitch :value="pollEnabled" @update:value="onTogglePoll" />
          每 5 分钟
        </label>
        <NButton size="small" :disabled="!selected.length" @click="copySelected">复制单号</NButton>
        <NButton type="primary" size="small" :loading="refreshing" @click="onRefresh">手动刷新</NButton>
      </div>
    </div>

    <div class="panel shrink-0 space-y-2 px-3 py-2">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="item in scopes"
          :key="item.value"
          type="button"
          class="rounded-md px-2.5 py-1 text-sm"
          :class="scope === item.value ? 'bg-[var(--color-accent)] text-white' : 'text-[var(--color-fg-secondary)]'"
          @click="selectScope(item.value)"
        >
          {{ item.label }}
          <span v-if="item.value === 'remind'"> {{ changedCount }}</span>
          <span v-else-if="item.value === 'mine'"> {{ mineCount }}</span>
          <span v-else-if="item.value === 'active'"> {{ activeCount }}</span>
          <span v-else-if="item.value === 'ended'"> {{ endedCount }}</span>
        </button>
      </div>
      <div class="grid grid-cols-2 gap-2 lg:grid-cols-12">
        <div class="col-span-2 flex gap-2 lg:col-span-4">
          <NInput
            v-model:value="search"
            size="small"
            clearable
            placeholder="搜索运单号"
            class="min-w-0 flex-1"
            @keyup.enter="load()"
          />
          <NButton size="small" @click="load">查询</NButton>
        </div>
        <NSelect
          v-model:value="statusFilter"
          :options="[{ label: '已结束', value: '已结束' }, ...statuses.map((item) => ({ label: item, value: item }))]"
          clearable
          filterable
          placeholder="状态"
          size="small"
          class="w-full lg:col-span-2"
        />
        <NSelect
          v-model:value="customerFilter"
          :options="customers.map((item) => ({ label: item, value: item }))"
          clearable
          filterable
          placeholder="客户"
          size="small"
          class="w-full lg:col-span-2"
        />
        <NSelect
          v-model:value="channelFilter"
          :options="channels.map((item) => ({ label: item, value: item }))"
          multiple
          clearable
          filterable
          :max-tag-count="1"
          placeholder="渠道"
          size="small"
          class="w-full lg:col-span-2"
        />
        <NSelect
          v-model:value="warehouseFilter"
          :options="warehouses.map((item) => ({ label: item, value: item }))"
          clearable
          filterable
          placeholder="仓库"
          size="small"
          class="w-full lg:col-span-1"
        />
        <NSelect
          v-model:value="countryFilter"
          :options="countries.map((item) => ({ label: item, value: item }))"
          clearable
          filterable
          placeholder="国家"
          size="small"
          class="w-full lg:col-span-1"
        />
      </div>
    </div>

    <div class="panel min-h-0 flex-1 overflow-hidden p-0">
      <div class="scrollbar-visible h-full overflow-auto">
        <table class="order-flow-table w-full min-w-[1280px] text-left text-sm">
          <thead class="text-xs text-[var(--color-muted)]">
            <tr>
              <th class="order-flow-check px-3 py-2 font-medium">
                <NCheckbox :checked="allChecked" :indeterminate="someChecked" @update:checked="toggleAll" />
              </th>
              <th class="px-3 py-2 font-medium">运单号</th>
              <th class="px-3 py-2 font-medium">客户</th>
              <th class="px-3 py-2 font-medium">当前状态</th>
              <th class="px-3 py-2 font-medium">渠道</th>
              <th class="px-3 py-2 font-medium">操作时间</th>
              <th class="px-3 py-2 font-medium">件数</th>
              <th class="px-3 py-2 font-medium">实重</th>
              <th class="px-3 py-2 font-medium">计费重</th>
              <th class="px-3 py-2 font-medium">体积</th>
              <th class="px-3 py-2 font-medium">国家</th>
              <th class="px-3 py-2 font-medium">仓库</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && !items.length">
              <td colspan="12" class="px-3 py-8 text-center text-[var(--color-muted)]">
                暂无订单。待处理为空时可以看「流转中」，或先手动刷新。
              </td>
            </tr>
            <tr
              v-for="row in items"
              :key="row.waybillNo"
              :class="row.mine && !row.ended ? 'is-mine' : ''"
            >
              <td class="order-flow-check px-3 py-2">
                <NCheckbox
                  :checked="selected.includes(row.waybillNo)"
                  @update:checked="(checked) => toggleRow(row.waybillNo, checked)"
                />
              </td>
              <td class="px-3 py-2 font-medium">
                <button type="button" class="text-left text-[var(--color-accent-text)] hover:underline" @click="openLogs(row.waybillNo)">
                  {{ row.waybillNo }}
                </button>
              </td>
              <td class="px-3 py-2">{{ showText(row.customerName) }}</td>
              <td class="px-3 py-2">
                <div class="status-name">
                  <span>{{ showText(row.currentStatus) }}</span>
                  <span v-if="showNew(row)" class="status-new">NEW</span>
                </div>
                <div v-if="row.ended" class="mt-1">
                  <NTag size="tiny" :bordered="false">已结束</NTag>
                </div>
              </td>
              <td class="px-3 py-2">{{ showText(row.channelName) }}</td>
              <td class="whitespace-nowrap px-3 py-2">
                <NPopover
                  trigger="hover"
                  placement="left-start"
                  :show-arrow="false"
                  @update:show="(show) => show && ensureLogs(row.waybillNo)"
                >
                  <template #trigger>
                    <span class="cursor-default border-b border-dashed border-[var(--color-border)]">
                      {{ operateLabel(row.lastOperateTime) }}
                    </span>
                  </template>
                  <div class="max-h-80 w-80 overflow-auto pr-1">
                    <p class="mb-3 text-xs text-[var(--color-muted)]">全部轨迹</p>
                    <p v-if="logLoading[row.waybillNo]" class="text-xs text-[var(--color-muted)]">加载中</p>
                    <p v-else-if="!(logCache[row.waybillNo] || []).length" class="text-xs text-[var(--color-muted)]">还没有轨迹</p>
                    <ol v-else class="flow-timeline">
                      <li
                        v-for="(item, index) in logCache[row.waybillNo]"
                        :key="`${item.status}-${index}`"
                        :class="{ 'is-current': isCurrentLog(row, logCache[row.waybillNo] || [], index) }"
                      >
                        <span class="flow-timeline__dot" />
                        <div class="flex items-center justify-between gap-2">
                          <span class="font-medium leading-5">{{ item.status }}</span>
                          <span v-if="isCurrentLog(row, logCache[row.waybillNo] || [], index)" class="flow-timeline__badge">当前</span>
                        </div>
                        <div class="mt-0.5 text-xs text-[var(--color-muted)]">{{ item.operateTime || item.recordedTime || '—' }}</div>
                      </li>
                    </ol>
                  </div>
                </NPopover>
              </td>
              <td class="px-3 py-2 tabular-nums">{{ showText(row.pieces) }}</td>
              <td class="px-3 py-2 tabular-nums">{{ showText(row.weightKg) }}</td>
              <td class="px-3 py-2 tabular-nums">{{ showText(row.chargeWeightKg) }}</td>
              <td class="px-3 py-2 tabular-nums">{{ showText(row.volumeCbm) }}</td>
              <td class="px-3 py-2">{{ showText(row.countryName) }}</td>
              <td class="px-3 py-2">{{ showText(row.warehouseName) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <NDrawer v-model:show="logShow" :width="420" placement="right">
      <NDrawerContent :title="logWaybill ? `${logWaybill} 的节点` : '节点记录'" closable>
        <p v-if="!logs.length" class="text-sm text-[var(--color-muted)]">还没有节点记录。之后每次状态变化都会记在这里。</p>
        <ol v-else class="flow-timeline">
          <li
            v-for="(item, index) in logs"
            :key="`${item.status}-${index}`"
            :class="{ 'is-current': isCurrentLog(items.find((row) => row.waybillNo === logWaybill), logs, index) }"
          >
            <span class="flow-timeline__dot" />
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium leading-5">{{ item.status }}</span>
              <span v-if="isCurrentLog(items.find((row) => row.waybillNo === logWaybill), logs, index)" class="flow-timeline__badge">当前</span>
            </div>
            <div class="mt-0.5 text-xs text-[var(--color-muted)]">{{ item.operateTime || item.recordedTime || '—' }}</div>
          </li>
        </ol>
      </NDrawerContent>
    </NDrawer>
    <p class="shrink-0 text-xs text-[var(--color-muted)]">
      已选 {{ selected.length }}。悬停操作时间可看全部轨迹。铃铛按节点汇总，数字是没看过的新节点。
    </p>
  </div>
</template>

<style scoped>
.order-flow-table {
  border-collapse: separate;
  border-spacing: 0;
}

.order-flow-check {
  width: 40px;
  text-align: center;
  vertical-align: middle;
}

.status-name {
  position: relative;
  display: inline-block;
  max-width: 100%;
  padding-top: 0.35rem;
  padding-right: 1.7rem;
}

.status-new {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.04em;
  color: #fff;
  background: var(--color-accent);
  border-radius: 3px;
  padding: 1px 3px;
}

.order-flow-table th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--color-panel);
  box-shadow: inset 0 -1px 0 var(--color-border);
  white-space: nowrap;
}

.order-flow-table td {
  background: var(--color-panel);
  border-bottom: 1px solid var(--color-border);
  vertical-align: top;
  transition: background-color 0.15s ease;
}

.order-flow-table tbody tr:hover td {
  background: color-mix(in srgb, var(--color-fg) 6%, var(--color-panel));
}

.order-flow-table tr.is-mine td {
  background: color-mix(in srgb, #f59e0b 12%, var(--color-panel));
}

.order-flow-table tbody tr.is-mine:hover td {
  background: color-mix(in srgb, #f59e0b 22%, var(--color-panel));
}

.flow-timeline {
  margin: 0;
  padding: 2px 0 0;
  list-style: none;
}

.flow-timeline li {
  position: relative;
  padding: 0 0 16px 18px;
}

.flow-timeline li:last-child {
  padding-bottom: 0;
}

.flow-timeline li::before {
  content: '';
  position: absolute;
  left: 4px;
  top: 12px;
  bottom: -4px;
  width: 1px;
  background: var(--color-border);
}

.flow-timeline li:last-child::before {
  display: none;
}

.flow-timeline__dot {
  position: absolute;
  left: 0;
  top: 5px;
  width: 9px;
  height: 9px;
  border: 2px solid var(--color-muted);
  border-radius: 999px;
  background: var(--color-elevated);
}

.flow-timeline li.is-current .flow-timeline__dot {
  border-color: var(--color-accent);
  background: var(--color-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent) 28%, transparent);
}

.flow-timeline li.is-current {
  color: var(--color-accent-hover);
}

.flow-timeline__badge {
  flex-shrink: 0;
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-accent) 22%, transparent);
  padding: 0 6px;
  font-size: 10px;
  line-height: 16px;
  color: var(--color-accent-hover);
}
</style>
