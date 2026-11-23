<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { NButton, NDatePicker, NDropdown, NInput, NModal, NSelect, useMessage, type InputInst } from 'naive-ui'
import { Check, ChevronDown, Copy } from 'lucide-vue-next'
import { api } from '@/api/client'
import type { Shipment } from '@/types/shipment'
import { syncShipmentsRouteStatusFromDps, syncTrackingAfterRouteAdd } from '@/api/shipments'
import { ICON_STROKE } from '@/constants/icons'
import { normalizeRouteStatusLocalCode, ROUTE_STATUS_BADGE_TONE } from '@/constants/shipmentRouteStatus'

const props = defineProps<{
  show: boolean
  shipments: Shipment[]
  carrierSource?: { trackingTime: string; trackingDesc: string } | null
}>()
const emit = defineEmits<{ close: []; updated: [] }>()
const message = useMessage()
const busy = ref(false)
const optionsLoading = ref(false)
const attempted = ref(false)
const nodeTime = ref<number | null>(Date.now())
const deliveryTime = ref<number | null>(Date.now())
const timeSettingsOpen = ref(true)
const description = ref('')
const appointmentDate = ref<string | null>(null)
const deliveredDate = ref<string | null>(null)
const appointmentDatePlaceholder = '{预计交仓日期}'
const deliveredDatePlaceholder = '{完成派送日期}'
const warehousePlaceholder = '{派送仓库}'
const descriptionFieldOptions = [appointmentDatePlaceholder, deliveredDatePlaceholder, warehousePlaceholder]
  .map(key => ({ label: key.slice(1, -1), key }))
const appointmentDatePattern = /\{预计交仓日期\}|\bN\/N\b/g
const needsAppointmentDate = computed(() => description.value.search(appointmentDatePattern) !== -1)
const needsDeliveredDate = computed(() => description.value.includes(deliveredDatePlaceholder))
const needsWarehouse = computed(() => description.value.includes(warehousePlaceholder))
const missingWarehouseShipments = computed(() => props.shipments.filter(shipment => !shipment.addressCode?.trim()))
const missingDescriptionDate = computed(() => (needsAppointmentDate.value && !appointmentDate.value)
  || (needsDeliveredDate.value && !deliveredDate.value))

function monthDay(date: string) {
  return date.slice(5).replace('-', '/')
}

const resolvedDescription = computed(() => {
  let text = description.value.trim()
  if (appointmentDate.value) text = text.replace(appointmentDatePattern, monthDay(appointmentDate.value))
  if (deliveredDate.value) text = text.split(deliveredDatePlaceholder).join(monthDay(deliveredDate.value))
  return text
})
const warehousePreviews = computed(() => {
  if (!needsWarehouse.value) return []
  const counts = new Map<string, number>()
  for (const shipment of props.shipments) {
    const code = shipment.addressCode?.trim()
    if (code) counts.set(code, (counts.get(code) ?? 0) + 1)
  }
  return Array.from(counts, ([code, count]) => ({
    code,
    count,
    description: resolvedDescription.value.split(warehousePlaceholder).join(code),
  }))
})
const status = ref<string | null>(null)
const statuses = ref<{ label: string; value: string }[]>([])
const selectedStatusLabel = computed(() => statuses.value.find(option => option.value === status.value)?.label)
interface Result { id: string; shipmentNo: string; status: 'success' | 'failed' | 'unknown'; message: string }
const results = ref<Result[] | null>(null)
const error = ref('')
const defaultPresets = [
  { label: '已送达，等待 POD', status: '601', text: 'Delivered, waiting for POD' },
  { label: '已完成派送（仓库和日期）', status: '601', text: 'Delivered to {派送仓库} on {完成派送日期} local time.（{派送仓库}当地时间{完成派送日期}-已完成派送）' },
  { label: '到达目的港', status: '306', text: 'Arrived at destination port' },
  { label: '到达中转仓', status: '502', text: 'Arrived at destination transit warehouse' },
  { label: '已约仓，等待派送', status: '509', text: 'Delivery appointment confirmed, awaiting delivery' },
  { label: '已交尾程承运商', status: '510', text: 'Handed over to last-mile carrier' },
  { label: '已离开起运港', status: '301', text: 'Departed from port of loading' },
]
type RoutePreset = (typeof defaultPresets)[number]
const presets = ref<RoutePreset[]>([])
const statusOrder = computed(() => new Map(
  statuses.value.map((option, index) => [option.value, option.value === '100' ? statuses.value.length + 1 : index]),
))
const orderedPresets = computed(() => [...presets.value].sort(comparePresetStatus))
const availablePresets = computed(() => orderedPresets.value.filter(preset => statusOrder.value.has(preset.status)))
const descriptionInput = ref<InputInst | null>(null)
const suggestDescription = ref(false)
const descriptionSuggestions = computed(() => {
  const keyword = description.value.trim().toLowerCase()
  if (!suggestDescription.value || !keyword || attempted.value) return []
  return availablePresets.value.filter(preset =>
    preset.text.toLowerCase().includes(keyword) || preset.label.toLowerCase().includes(keyword),
  )
})
const configOpen = ref(false)
const configSaving = ref(false)
const configError = ref('')
const optionsReady = ref(false)
const draftPresets = ref<(Omit<RoutePreset, 'status'> & { status: string | null; key: number })[]>([])
let draftKey = 0

function comparePresetStatus(a: { status: string | null }, b: { status: string | null }) {
  const fallback = statusOrder.value.size
  return (statusOrder.value.get(a.status ?? '') ?? fallback) - (statusOrder.value.get(b.status ?? '') ?? fallback)
}

function openPresetConfig() {
  draftPresets.value = orderedPresets.value.map(preset => ({ ...preset, key: ++draftKey }))
  configError.value = ''
  configOpen.value = true
}

function presetStatusOptions(value: string | null) {
  if (value && !statusOrder.value.has(value)) {
    return [...statuses.value, { label: `${value}（未启用）`, value, disabled: true }]
  }
  return statuses.value
}

function presetColors(code: string) {
  const tone = ROUTE_STATUS_BADGE_TONE[normalizeRouteStatusLocalCode(code)] || 'default'
  return { '--preset-fg': `var(--tag-${tone}-fg)`, '--preset-bg': `var(--tag-${tone}-bg)` }
}

function isPresetSelected(preset: RoutePreset) {
  return status.value === preset.status && description.value === preset.text
}

function applyPreset(preset: RoutePreset) {
  suggestDescription.value = false
  appointmentDate.value = null
  deliveredDate.value = null
  description.value = preset.text
  status.value = preset.status
}

function updateDescription(value: string) {
  description.value = value
  suggestDescription.value = true
}

async function selectDescriptionSuggestion(preset: RoutePreset) {
  applyPreset(preset)
  await nextTick()
  descriptionInput.value?.focus()
}

async function savePresetConfig() {
  if (configSaving.value) return
  configError.value = ''
  const payload = draftPresets.value
    .map(({ label, status, text }) => ({ label: label.trim(), status, text: text.trim() }))
    .sort(comparePresetStatus)
  if (payload.some(preset => !preset.label || !preset.status || !preset.text)) {
    configError.value = '请填写每项的按钮名称、明细状态和节点描述。'
    return
  }
  configSaving.value = true
  try {
    const result = await api<{ presets: RoutePreset[] }>('/api/v1/shipment-routes/presets', {
      method: 'PUT', retry: 0, body: { presets: payload },
    })
    presets.value = result.presets
    configOpen.value = false
    message.success('路由配置已保存')
  } catch (e) {
    const detail = (e as { data?: { detail?: unknown } })?.data?.detail
    configError.value = typeof detail === 'string' ? detail : '路由配置保存失败，请重试。'
  } finally { configSaving.value = false }
}
const invalid = computed(() => !props.shipments.length || props.shipments.length > 50
  || props.shipments.some(s => !s.waybillId) || !nodeTime.value || !deliveryTime.value
  || !resolvedDescription.value || missingDescriptionDate.value
  || (needsWarehouse.value && missingWarehouseShipments.value.length > 0)
  || !selectedStatusLabel.value)
function formatTime(value: number | null) {
  if (value === null) return ''
  const d = new Date(value), pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const carrierSourceTime = computed(() => {
  const raw = props.carrierSource?.trackingTime?.trim().replace('T', ' ') || ''
  if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?$/.test(raw)) return null
  const time = raw.length === 16 ? `${raw}:00` : raw
  const timestamp = new Date(time.replace(' ', 'T')).getTime()
  return Number.isFinite(timestamp) && formatTime(timestamp) === time ? timestamp : null
})

async function copyCarrierSource(value: string, label: string) {
  try {
    await navigator.clipboard.writeText(value)
    message.success(`已复制${label}`)
  } catch {
    message.error(`${label}复制失败`)
  }
}

let revision = 0
watch(() => props.show, async show => {
  const current = ++revision
  if (!show) return
  const now = new Date(), delivery = new Date(now)
  delivery.setDate(delivery.getDate() + 15)
  nodeTime.value = props.carrierSource ? carrierSourceTime.value : now.getTime()
  deliveryTime.value = delivery.getTime()
  timeSettingsOpen.value = true
  appointmentDate.value = null
  deliveredDate.value = null
  suggestDescription.value = false
  description.value = ''; status.value = null; attempted.value = false; results.value = null; error.value = ''; statuses.value = []
  optionsLoading.value = true
  optionsReady.value = false
  configOpen.value = false
  presets.value = []
  try {
    const data = await api<{ statuses: typeof statuses.value; presets?: typeof defaultPresets | null }>('/api/v1/shipment-routes/options')
    if (current === revision) {
      statuses.value = data.statuses.map(s => ({ ...s, label: `${s.label} (${s.value})` }))
      presets.value = data.presets ?? defaultPresets.filter(preset => statusOrder.value.has(preset.status))
      optionsReady.value = true
    }
  } catch { if (current === revision) error.value = '明细状态加载失败，请关闭后重试' }
  finally { if (current === revision) optionsLoading.value = false }
})
const successfulShipmentNos = computed(() => [...new Set((results.value ?? [])
  .filter(row => row.status === 'success').map(row => row.shipmentNo.trim()).filter(Boolean))])

async function refreshAddedRoutes() {
  const shipmentNos = successfulShipmentNos.value
  if (!shipmentNos.length) return
  const warnings: string[] = []
  try {
    const sync = await syncShipmentsRouteStatusFromDps(shipmentNos)
    if (sync.failed || sync.missingWaybillId || sync.empty) warnings.push('部分明细状态未能回读')
  } catch { warnings.push('明细状态回读失败') }
  try {
    const sync = await syncTrackingAfterRouteAdd(shipmentNos)
    if (sync.errors.length || sync.notFound || sync.empty || sync.excludedNotInTransit || sync.total < shipmentNos.length) {
      warnings.push('部分内部轨迹暂未同步')
    }
  } catch { warnings.push('内部轨迹同步失败') }
  error.value = warnings.length ? `节点已新增。${warnings.join('。')}。可稍后重新回读。` : ''
}

async function refreshAgain() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await refreshAddedRoutes()
    emit('updated')
  } finally { busy.value = false }
}

async function submit() {
  if (busy.value || attempted.value || optionsLoading.value || invalid.value) return
  attempted.value = true; busy.value = true; error.value = ''
  try {
    const result = await api<{ items: Result[] }>('/api/v1/shipment-routes', {
      method: 'POST', retry: 0, timeout: 900_000,
      body: { ids: props.shipments.map(s => s.id), nodeTime: formatTime(nodeTime.value), estimatedDeliveryDate: formatTime(deliveryTime.value), nodeDesc: resolvedDescription.value, status: status.value },
    })
    results.value = result.items
    if (result.items.every(r => r.status === 'success')) message.success('路由新增成功')
    else message.warning('部分运单需要核对，请查看逐票结果')
    await refreshAddedRoutes()
    emit('updated')
  } catch (e) {
    error.value = (e as { data?: { detail?: string } })?.data?.detail || '请求未能确认完成，请先核对 DPS 路由，勿重复提交'
  } finally { busy.value = false }
}
</script>

<template>
  <NModal :show="show" preset="card" title="新增路由" :style="{ width: 'min(720px, calc(100vw - 2rem))' }" :mask-closable="!busy && !configOpen" :close-on-esc="!busy && !configOpen" :closable="!busy && !configOpen" @update:show="value => { if (!value && !busy && !configOpen) emit('close') }">
    <template #header-extra>
      <NButton v-if="!configOpen" size="small" :disabled="busy || !optionsReady" @click="openPresetConfig">路由配置</NButton>
    </template>
    <section v-if="configOpen" aria-label="路由配置">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-sm font-semibold">常用节点配置</h3>
        <NButton size="small" :disabled="configSaving || draftPresets.length >= 100" @click="draftPresets.push({ key: ++draftKey, label: '', status: null, text: '' })">添加节点</NButton>
      </div>
      <div class="max-h-[55vh] space-y-3 overflow-y-auto p-1">
        <p v-if="!draftPresets.length" class="text-sm text-[var(--color-muted)]">暂无常用节点。</p>
        <div v-for="(preset, index) in draftPresets" :key="preset.key" class="rounded border border-[var(--color-border)] p-3">
          <div class="mb-2 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <NInput v-model:value="preset.label" :disabled="configSaving" :maxlength="100" placeholder="按钮名称" :input-props="{ 'aria-label': '按钮名称' }" />
            <NSelect v-model:value="preset.status" :disabled="configSaving" :options="presetStatusOptions(preset.status)" filterable placeholder="明细状态" aria-label="明细状态" />
            <NButton size="small" :disabled="configSaving" @click="draftPresets.splice(index, 1)">移除</NButton>
          </div>
          <NInput v-model:value="preset.text" :disabled="configSaving" type="textarea" :maxlength="2000" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="节点描述" :input-props="{ 'aria-label': '节点描述' }" />
          <NDropdown
            trigger="click"
            :options="descriptionFieldOptions.map(option => ({ ...option, disabled: preset.text.length + option.key.length > 2000 }))"
            @select="key => preset.text += String(key)"
          >
            <NButton size="tiny" quaternary class="mt-1.5" :disabled="configSaving">插入字段</NButton>
          </NDropdown>
        </div>
      </div>
      <p v-if="configError" role="alert" class="mt-3 text-sm text-red-600">{{ configError }}</p>
      <div class="mt-4 flex justify-end gap-2">
        <NButton :disabled="configSaving" @click="configOpen = false">取消</NButton>
        <NButton type="primary" :loading="configSaving" @click="savePresetConfig">保存配置</NButton>
      </div>
    </section>
    <template v-else>
    <div class="mb-3 flex items-start gap-2 text-sm">
      <span v-if="shipments.length > 1" class="shrink-0 rounded bg-[var(--color-border-subtle)] px-2">{{ shipments.length }} 票</span>
      <span class="max-h-20 min-w-0 overflow-auto break-words font-medium">{{ shipments.map(s => s.shipmentNo).join('、') }}</span>
    </div>
    <p v-if="shipments.length > 50" role="alert" class="mb-3 text-sm text-red-600">单次最多 50 票。</p>
    <p v-if="shipments.some(s => !s.waybillId)" class="mb-3 text-sm text-red-600">部分运单缺少 DPS ID，请先更新运单。</p>
    <section v-if="carrierSource" aria-label="承运商轨迹原文" class="mb-3 space-y-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-border-subtle)] px-3 py-2 text-sm">
      <div class="flex flex-wrap items-center justify-between gap-x-2">
        <h3 class="font-medium">承运商轨迹</h3>
        <div v-if="carrierSource.trackingTime" class="flex items-center gap-1 text-xs tabular-nums text-[var(--color-muted)]">
          <span>{{ carrierSource.trackingTime }}</span>
          <NButton size="tiny" quaternary circle title="复制时间" aria-label="复制时间" @click="copyCarrierSource(carrierSource.trackingTime, '时间')">
            <template #icon><Copy :size="14" :stroke-width="ICON_STROKE" aria-hidden="true" /></template>
          </NButton>
        </div>
      </div>
      <div v-if="carrierSource.trackingDesc" class="flex items-start gap-1">
        <p class="max-h-24 min-w-0 flex-1 overflow-auto whitespace-pre-wrap break-words">{{ carrierSource.trackingDesc }}</p>
        <NButton size="tiny" quaternary circle title="复制原文" aria-label="复制原文" @click="copyCarrierSource(carrierSource.trackingDesc, '原文')">
          <template #icon><Copy :size="14" :stroke-width="ICON_STROKE" aria-hidden="true" /></template>
        </NButton>
      </div>
    </section>
    <fieldset :disabled="busy || attempted" class="space-y-3">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="preset in availablePresets"
          :key="`${preset.status}:${preset.text}`"
          type="button"
          class="route-preset"
          :style="presetColors(preset.status)"
          :aria-pressed="isPresetSelected(preset)"
          :disabled="busy || attempted"
          @click="applyPreset(preset)"
        >
          <Check v-if="isPresetSelected(preset)" class="size-3.5 shrink-0" :stroke-width="ICON_STROKE" aria-hidden="true" />
          {{ preset.label }}
        </button>
      </div>
      <div><label class="mb-1 block text-sm">明细状态</label><NSelect v-model:value="status" :options="statuses" :loading="optionsLoading" :disabled="busy || attempted" filterable placeholder="请选择对应的节点状态" /></div>
      <div>
        <label class="mb-1 block text-sm">节点描述</label>
        <NInput ref="descriptionInput" :value="description" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" :maxlength="2000" :disabled="busy || attempted" placeholder="输入描述或关键词" :input-props="{ 'aria-label': '节点描述' }" @update:value="updateDescription" />
        <section v-if="descriptionSuggestions.length" aria-label="匹配的常用描述" class="mt-1.5 rounded-lg border border-[var(--color-border)]">
          <ul class="max-h-36 overflow-auto p-1">
            <li v-for="preset in descriptionSuggestions" :key="`${preset.status}:${preset.text}`">
              <button type="button" class="block w-full rounded px-2 py-1.5 text-left text-sm hover:bg-[var(--color-border-subtle)] focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]" @click="selectDescriptionSuggestion(preset)">
                <span class="block font-medium">{{ preset.label }} <span class="route-preset-code" :style="presetColors(preset.status)">{{ preset.status }}</span></span>
                <span class="block break-words text-xs text-[var(--color-muted)]">{{ preset.text }}</span>
              </button>
            </li>
          </ul>
        </section>
      </div>
      <div v-if="needsAppointmentDate || needsDeliveredDate" class="grid gap-2 sm:grid-cols-2">
        <div v-if="needsAppointmentDate">
          <label class="mb-1 block text-sm">预计交仓日期</label>
          <NDatePicker v-model:formatted-value="appointmentDate" type="date" format="yyyy-MM-dd" value-format="yyyy-MM-dd" clearable :disabled="busy || attempted" placeholder="选择约好的交仓日期" aria-label="预计交仓日期" class="w-full" />
        </div>
        <div v-if="needsDeliveredDate">
          <label class="mb-1 block text-sm">完成派送日期（目的地当地）</label>
          <NDatePicker v-model:formatted-value="deliveredDate" type="date" format="yyyy-MM-dd" value-format="yyyy-MM-dd" clearable :disabled="busy || attempted" placeholder="选择当地完成派送的日期" aria-label="完成派送日期（目的地当地）" class="w-full" />
        </div>
      </div>
      <div class="rounded-lg border border-[var(--color-border)]">
        <button type="button" class="flex w-full flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-3 py-2 text-left text-sm focus-visible:outline-2 focus-visible:outline-[var(--color-accent-text)]" :aria-expanded="timeSettingsOpen" @click="timeSettingsOpen = !timeSettingsOpen">
          <span class="inline-flex items-center gap-1.5 font-medium">
            <ChevronDown class="size-4" :class="{ 'rotate-180': timeSettingsOpen }" :stroke-width="ICON_STROKE" aria-hidden="true" />
            时间设置
          </span>
          <span v-if="!timeSettingsOpen" class="flex flex-wrap gap-x-3 text-xs text-[var(--color-muted)]">
            <span>节点 {{ formatTime(nodeTime) || '未选择' }}</span>
            <span>预计派送 {{ formatTime(deliveryTime) || '未选择' }}</span>
          </span>
        </button>
        <div v-if="timeSettingsOpen" class="grid gap-3 px-3 pb-3 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-sm">节点时间</label>
            <NDatePicker v-model:value="nodeTime" type="datetime" :status="carrierSource && nodeTime === null ? 'error' : undefined" :disabled="busy || attempted" aria-label="节点时间" class="w-full" />
            <p v-if="carrierSource && nodeTime === null" role="alert" class="mt-1 text-xs text-red-600">请选择节点时间。</p>
          </div>
          <div><label class="mb-1 block text-sm">预计派送时间</label><NDatePicker v-model:value="deliveryTime" type="datetime" :disabled="busy || attempted" aria-label="预计派送时间" class="w-full" /></div>
        </div>
      </div>
    </fieldset>
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <div v-if="results" class="mt-4 max-h-52 overflow-auto text-sm" role="status">
      <p v-for="row in results" :key="row.id" class="mb-1">
        {{ row.shipmentNo }} · {{ row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : '待核对' }}<template v-if="row.status !== 'success' && row.message"> · {{ row.message }}</template>
      </p>
      <p v-if="busy && successfulShipmentNos.length" class="mt-2 text-[var(--color-muted)]">正在回读轨迹…</p>
    </div>
    <div v-if="!attempted && needsWarehouse && missingWarehouseShipments.length" role="alert" class="mt-3 text-xs text-red-600">
      <p>缺少派送仓库</p>
      <p class="mt-1 max-h-20 overflow-auto break-words">{{ missingWarehouseShipments.map(shipment => shipment.shipmentNo).join('、') }}</p>
    </div>
    <section v-if="!attempted && resolvedDescription && !missingDescriptionDate && (!needsWarehouse || warehousePreviews.length)" aria-label="提交预览" class="mt-3 space-y-2 rounded-lg border border-[var(--color-border)] px-3 py-2.5 text-sm">
      <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 class="text-sm font-semibold">提交预览</h3>
        <span v-if="selectedStatusLabel" class="text-xs text-[var(--color-muted)]">{{ selectedStatusLabel }}</span>
      </div>
      <template v-if="needsWarehouse && shipments.length > 1">
        <div class="max-h-40 space-y-1 overflow-y-auto">
          <div v-for="group in warehousePreviews" :key="group.code" class="rounded border border-[var(--color-border)] px-2.5 py-1.5">
            <h4 class="font-medium">{{ group.code }} · {{ group.count }} 票</h4>
            <p class="mt-1.5 whitespace-pre-wrap break-words">{{ group.description }}</p>
          </div>
        </div>
      </template>
      <p v-else class="whitespace-pre-wrap break-words">{{ needsWarehouse ? warehousePreviews[0]?.description : resolvedDescription }}</p>
    </section>
    <div class="mt-4 flex justify-end gap-2">
      <NButton :disabled="busy" @click="emit('close')">{{ attempted ? '关闭' : '取消' }}</NButton>
      <NButton v-if="successfulShipmentNos.length" :loading="busy" @click="refreshAgain">重新回读</NButton>
      <NButton v-else type="primary" :loading="busy" :disabled="invalid || optionsLoading || attempted" @click="submit">新增路由</NButton>
    </div>
    </template>
  </NModal>
</template>

<style scoped>
.route-preset,
.route-preset-code {
  color: var(--preset-fg);
  background: var(--preset-bg);
}

.route-preset {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 1px solid color-mix(in srgb, var(--preset-fg) 28%, var(--color-border));
  border-radius: 0.375rem;
  padding: 0.25rem 0.625rem;
  font-size: 0.8125rem;
  line-height: 1.25rem;
  cursor: pointer;
}

.route-preset:hover:not(:disabled),
.route-preset[aria-pressed='true'] {
  border-color: var(--preset-fg);
}

.route-preset:focus-visible {
  outline: 2px solid var(--preset-fg);
  outline-offset: 2px;
}

.route-preset:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.route-preset-code {
  display: inline-block;
  border-radius: 0.25rem;
  padding: 0 0.25rem;
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
}
</style>
