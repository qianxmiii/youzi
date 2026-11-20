<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { NButton, NDatePicker, NInput, NModal, NPopconfirm, NSelect, useMessage, type InputInst } from 'naive-ui'
import { Check, ChevronDown } from 'lucide-vue-next'
import { api } from '@/api/client'
import type { Shipment } from '@/types/shipment'
import { syncShipmentsRouteStatusFromDps } from '@/api/shipments'
import { ICON_STROKE } from '@/constants/icons'
import { normalizeRouteStatusLocalCode, ROUTE_STATUS_BADGE_TONE } from '@/constants/shipmentRouteStatus'

const props = defineProps<{ show: boolean; shipments: Shipment[] }>()
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
let revision = 0
watch(() => props.show, async show => {
  const current = ++revision
  if (!show) return
  const now = new Date(), delivery = new Date(now)
  delivery.setDate(delivery.getDate() + 15)
  nodeTime.value = now.getTime(); deliveryTime.value = delivery.getTime()
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
async function submit() {
  if (busy.value || attempted.value || invalid.value) return
  attempted.value = true; busy.value = true; error.value = ''
  try {
    const result = await api<{ items: Result[] }>('/api/v1/shipment-routes', {
      method: 'POST', retry: 0, timeout: 900_000,
      body: { ids: props.shipments.map(s => s.id), nodeTime: formatTime(nodeTime.value), estimatedDeliveryDate: formatTime(deliveryTime.value), nodeDesc: resolvedDescription.value, status: status.value },
    })
    results.value = result.items
    if (result.items.every(r => r.status === 'success')) message.success('路由新增成功')
    else message.warning('部分运单需要核对，请查看逐票结果')
    const successful = result.items.filter(r => r.status === 'success').map(r => r.shipmentNo)
    if (successful.length) {
      try {
        const sync = await syncShipmentsRouteStatusFromDps(successful)
        if (sync.failed) error.value = '新增结果已保留，部分明细状态回读失败，请手动更新明细状态；勿重复新增节点'
      } catch { error.value = '节点已新增，明细状态回读失败，请手动更新明细状态；勿重复新增节点' }
    }
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
      <p class="mb-3 text-xs text-[var(--color-muted)]">
        描述可使用 <code>{{ appointmentDatePlaceholder }}</code>、<code>{{ deliveredDatePlaceholder }}</code> 或 <code>{{ warehousePlaceholder }}</code>。
      </p>
      <div class="max-h-[55vh] space-y-3 overflow-y-auto p-1">
        <p v-if="!draftPresets.length" class="text-sm text-[var(--color-muted)]">暂无常用节点。</p>
        <div v-for="(preset, index) in draftPresets" :key="preset.key" class="rounded border border-[var(--color-border)] p-3">
          <div class="mb-2 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <NInput v-model:value="preset.label" :disabled="configSaving" :maxlength="100" placeholder="按钮名称" :input-props="{ 'aria-label': '按钮名称' }" />
            <NSelect v-model:value="preset.status" :disabled="configSaving" :options="presetStatusOptions(preset.status)" filterable placeholder="明细状态" aria-label="明细状态" />
            <NButton size="small" :disabled="configSaving" @click="draftPresets.splice(index, 1)">移除</NButton>
          </div>
          <NInput v-model:value="preset.text" :disabled="configSaving" type="textarea" :maxlength="2000" :autosize="{ minRows: 2, maxRows: 4 }" placeholder="节点描述" :input-props="{ 'aria-label': '节点描述' }" />
        </div>
      </div>
      <p v-if="configError" role="alert" class="mt-3 text-sm text-red-600">{{ configError }}</p>
      <div class="mt-4 flex justify-end gap-2">
        <NButton :disabled="configSaving" @click="configOpen = false">取消</NButton>
        <NButton type="primary" :loading="configSaving" @click="savePresetConfig">保存配置</NButton>
      </div>
    </section>
    <template v-else>
    <p class="mb-3 text-sm text-[var(--color-muted)]">本次为 {{ shipments.length }} 票新增同一节点，最多 50 票。</p>
    <div class="mb-4 max-h-24 overflow-auto rounded border border-[var(--color-border)] p-2 text-sm">{{ shipments.map(s => s.shipmentNo).join(', ') }}</div>
    <p v-if="shipments.some(s => !s.waybillId)" class="mb-3 text-sm text-red-600">部分运单缺少 DPS ID，请先更新运单。</p>
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
          <p class="px-3 pt-2 pb-1 text-xs text-[var(--color-muted)]">匹配的常用描述 · {{ descriptionSuggestions.length }}</p>
          <ul class="max-h-36 overflow-auto px-1 pb-1">
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
        <p v-if="shipments.length > 1" class="text-xs text-[var(--color-muted)] sm:col-span-2">本批运单共用所选日期。</p>
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
          <div><label class="mb-1 block text-sm">节点时间</label><NDatePicker v-model:value="nodeTime" type="datetime" :disabled="busy || attempted" aria-label="节点时间" class="w-full" /></div>
          <div><label class="mb-1 block text-sm">预计派送时间（默认当前日期＋15天）</label><NDatePicker v-model:value="deliveryTime" type="datetime" :disabled="busy || attempted" aria-label="预计派送时间" class="w-full" /></div>
        </div>
      </div>
    </fieldset>
    <p v-if="error" role="alert" class="mt-3 text-sm text-red-600">{{ error }}</p>
    <div v-if="results" class="mt-4 max-h-52 overflow-auto text-sm" role="status">
      <p v-for="row in results" :key="row.id" class="mb-1">{{ row.shipmentNo }} · {{ row.status === 'success' ? '成功' : row.status === 'failed' ? '失败' : '待核对' }} · {{ row.message }}</p>
      <p class="mt-2 text-[var(--color-muted)]">已自动回读成功运单的明细状态；完整轨迹请使用“更新内部轨迹”。本次结果已保留，关闭前请核对。</p>
    </div>
    <section v-if="!attempted && resolvedDescription" aria-label="提交预览" class="mt-3 space-y-2 rounded-lg border border-[var(--color-border)] px-3 py-2.5 text-sm">
      <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <h3 class="text-sm font-semibold">提交预览</h3>
        <span class="text-xs text-[var(--color-muted)]">{{ selectedStatusLabel || '明细状态未选择' }}</span>
      </div>
      <div v-if="needsWarehouse && missingWarehouseShipments.length" role="alert" class="text-xs text-red-600">
        <p>以下运单缺少派送仓库，请补齐后再提交。</p>
        <p class="mt-1 max-h-20 overflow-auto break-words">{{ missingWarehouseShipments.map(shipment => shipment.shipmentNo).join('、') }}</p>
      </div>
      <p v-if="missingDescriptionDate" class="text-xs text-[var(--color-muted)]">请选择上方日期以生成完整描述。</p>
      <template v-else-if="needsWarehouse && shipments.length > 1">
        <div v-if="warehousePreviews.length" class="max-h-40 space-y-1 overflow-y-auto">
          <div v-for="group in warehousePreviews" :key="group.code" class="rounded border border-[var(--color-border)] px-2.5 py-1.5">
            <h4 class="font-medium">{{ group.code }} · {{ group.count }} 票</h4>
            <p class="mt-1.5 whitespace-pre-wrap break-words">{{ group.description }}</p>
          </div>
        </div>
      </template>
      <p v-else-if="!needsWarehouse || warehousePreviews.length" class="whitespace-pre-wrap break-words">{{ needsWarehouse ? warehousePreviews[0]?.description : resolvedDescription }}</p>
    </section>
    <div class="mt-4 flex justify-end gap-2">
      <NButton :disabled="busy" @click="emit('close')">{{ attempted ? '关闭' : '取消' }}</NButton>
      <NPopconfirm @positive-click="submit">
        <template #trigger><NButton type="primary" :loading="busy" :disabled="invalid || optionsLoading || attempted">确认新增</NButton></template>
        将为 {{ shipments.length }} 票运单向 DPS 新增此节点，确认时间、描述和状态无误？
      </NPopconfirm>
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
