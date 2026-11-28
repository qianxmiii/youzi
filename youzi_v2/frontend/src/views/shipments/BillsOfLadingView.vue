<script setup lang="ts">
import { computed, h, nextTick, onActivated, ref, watch } from 'vue'
import { NButton, NDataTable, NDrawer, NDrawerContent, NInput, NModal, NPagination, NSelect, NSpin, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import { useDebounceFn } from '@vueuse/core'
import { useRoute, useRouter } from 'vue-router'
import { bindBillOfLading, getBillOfLading, listBillsOfLading, type BillDeliveryScope, type BillDetail, type BillOfLading, type BillPortOptions, type BillState, type CustomsEvidence } from '@/api/billsOfLading'
import { getShipment } from '@/api/shipments'
import { createVesselSchedule, getVesselSchedule, listVesselSchedules } from '@/api/vesselSchedules'
import ShipmentTrackingDrawer from '@/components/shipments/ShipmentTrackingDrawer.vue'
import BillPortCallPicker from '@/components/vessel-schedules/BillPortCallPicker.vue'
import VoyageFormModal from '@/components/vessel-schedules/VoyageFormModal.vue'
import { routeStatusLabelZh } from '@/constants/shipmentRouteStatus'
import type { Shipment } from '@/types/shipment'
import type { VesselVoyagePayload, VoyagePortCall } from '@/types/vesselSchedule'
import { apiErrorMessage } from '@/utils/apiError'

const message = useMessage()
const route = useRoute()
const router = useRouter()
const items = ref<BillOfLading[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 30
const search = ref('')
const keyword = ref('')
const country = ref('US')
const state = ref<BillState>('')
const deliveryScope = ref<BillDeliveryScope>('open')
const originPort = ref<string | null>(null)
const destinationPort = ref<string | null>(null)
const portOptions = ref<BillPortOptions>({ origins: [], destinations: [] })
const loading = ref(false)
const error = ref('')
const detailShow = ref(false)
const detailLoading = ref(false)
const detail = ref<BillDetail | null>(null)
const detailBody = ref<HTMLElement | null>(null)
const bindingShow = ref(false)
const createVoyageShow = ref(false)
const creatingVoyage = ref(false)
const saving = ref(false)
const bindingError = ref('')
const vesselOptions = ref<{ label: string; value: string }[]>([])
const vesselsLoading = ref(false)
const portsLoading = ref(false)
const portCalls = ref<VoyagePortCall[]>([])
const voyageId = ref<string | null>(null)
const originId = ref<string | null>(null)
const destinationId = ref<string | null>(null)
const trackingShow = ref(false)
const trackingShipment = ref<Shipment | null>(null)

const states = [
  { label: '全部状态', value: '' }, { label: '待绑航次', value: 'unbound' },
  { label: '待核对挂靠', value: 'review' }, { label: '已排期', value: 'planned' },
  { label: '已离港', value: 'departed' }, { label: '已到港', value: 'arrived' },
  { label: '有查验', value: 'inspection' },
]
const deliveryScopes = [
  { label: '未全部签收', value: 'open' },
  { label: '已全部签收', value: 'delivered' },
  { label: '全部提单', value: 'all' },
]
const countries = [{ label: '美国', value: 'US' }, { label: '加拿大', value: 'CA' }, { label: '全部国家', value: '' }]
const phases = [
  { key: 'export', label: '出口' }, { key: 'import', label: '进口' },
] as const
const billStatusTones: Record<BillOfLading['state'], string> = {
  unbound: 'slate',
  review: 'orange',
  planned: 'violet',
  departed: 'sky',
  arrived: 'teal',
}
const rowKey = (row: BillOfLading) => row.billNo
const focusedContainer = computed(() => route.name === 'bills-of-lading' && typeof route.query.container === 'string'
  ? route.query.container : null)
const canSave = computed(() => {
  const origin = portCalls.value.find(port => port.id === originId.value)
  const destination = portCalls.value.find(port => port.id === destinationId.value)
  return Boolean(voyageId.value && origin && destination && origin.sequence < destination.sequence && !portsLoading.value)
})

function stateLabel(value: BillOfLading['state']) {
  return states.find(option => option.value === value)?.label || '—'
}

function billStatus(row: BillOfLading) {
  if (row.deliveredCount === row.shipmentCount) return '已全部签收'
  if (row.deliveredCount > 0) return `签收 ${row.deliveredCount}/${row.shipmentCount}`
  return stateLabel(row.state)
}

function renderBillStatus(row: BillOfLading) {
  const delivered = row.deliveredCount === row.shipmentCount
  const tone = row.deliveredCount > 0 ? 'indigo' : billStatusTones[row.state]
  return h(NTag, {
    size: 'small',
    bordered: false,
    type: delivered ? 'success' : 'default',
    color: delivered ? undefined : { color: `var(--tag-${tone}-bg)`, textColor: `var(--tag-${tone}-fg)` },
  }, () => billStatus(row))
}

function customsLabel(phase: string, evidence: CustomsEvidence) {
  return evidence.status === 'inspection' ? `${phase}查验` : `${phase}已放行`
}

function dateText(value?: string | null) {
  return value?.slice(0, 10) || '—'
}

function conflict(voyage: string | null) {
  const assigned = detail.value?.binding?.vesselVoyage
  return Boolean(assigned && voyage && voyage.trim().toUpperCase() !== assigned.trim().toUpperCase())
}

let listRevision = 0
async function load() {
  const revision = ++listRevision
  loading.value = true
  error.value = ''
  try {
    const result = await listBillsOfLading({
      country: country.value, search: keyword.value, state: state.value,
      delivery_scope: deliveryScope.value,
      origin_port: originPort.value ?? undefined, destination_port: destinationPort.value ?? undefined,
      limit: pageSize, offset: (page.value - 1) * pageSize,
    })
    if (revision === listRevision) {
      items.value = result.items
      total.value = result.total
      portOptions.value = result.portOptions
      const lastPage = Math.max(1, Math.ceil(total.value / pageSize))
      if (page.value > lastPage) page.value = lastPage
    }
  } catch (e) {
    if (revision === listRevision) error.value = e instanceof Error ? e.message : '提单加载失败'
  } finally {
    if (revision === listRevision) loading.value = false
  }
}

const updateKeyword = useDebounceFn(() => { keyword.value = search.value.trim() }, 220)
watch(search, updateKeyword)
watch(country, () => {
  originPort.value = null
  destinationPort.value = null
}, { flush: 'sync' })
watch([country, state, deliveryScope, keyword, originPort, destinationPort], () => { page.value = 1 }, { flush: 'sync' })
watch([page, country, state, deliveryScope, keyword, originPort, destinationPort], load)

let detailRevision = 0
async function openDetail(billNo: string) {
  const revision = ++detailRevision
  detail.value = null
  detailLoading.value = true
  detailShow.value = true
  try {
    const bill = await getBillOfLading(billNo)
    if (revision === detailRevision) {
      detail.value = bill
      await nextTick()
      scrollToContainer()
    }
  } catch (e) {
    if (revision === detailRevision) message.error(e instanceof Error ? e.message : '提单详情加载失败')
  } finally {
    if (revision === detailRevision) detailLoading.value = false
  }
}

function scrollToContainer() {
  if (focusedContainer.value === null || !detailBody.value || route.query.billNo !== detail.value?.billNo) return
  const sections = Array.from(detailBody.value.querySelectorAll<HTMLElement>('[data-container-no]'))
  sections.find(section => section.dataset.containerNo === focusedContainer.value)?.scrollIntoView({ block: 'nearest' })
}

watch(() => [route.name, route.query.billNo, route.query.container], ([name, billNo], previous) => {
  if (name !== 'bills-of-lading') {
    detailShow.value = false
    return
  }
  if (typeof billNo === 'string' && billNo) {
    if (!detailShow.value || detail.value?.billNo !== billNo) void openDetail(billNo)
    else void nextTick(scrollToContainer)
  } else if (previous?.[0] === 'bills-of-lading' && previous[1]) {
    detailShow.value = false
  }
}, { immediate: true })

function closeDetail(show: boolean) {
  detailShow.value = show
  if (!show && route.name === 'bills-of-lading' && route.query.billNo) {
    void router.replace({ query: { ...route.query, billNo: undefined, container: undefined } })
  }
}

function openBoundVoyage() {
  const binding = detail.value?.binding
  if (binding?.vesselVoyage) {
    void router.push({
      name: 'vessel-schedules',
      query: { voyageId: binding.voyageId, portCallId: binding.needsReview ? undefined : binding.destinationCallId },
    })
  }
}

let vesselRevision = 0
async function searchVoyages(query: string) {
  const revision = ++vesselRevision
  vesselsLoading.value = true
  try {
    const result = await listVesselSchedules({ search: query, limit: 40 })
    if (revision !== vesselRevision) return
    const options = result.items.map(vessel => ({ label: vessel.vesselVoyage, value: vessel.id }))
    const selected = vesselOptions.value.find(option => option.value === voyageId.value)
    if (selected && !options.some(option => option.value === selected.value)) options.unshift(selected)
    vesselOptions.value = options
  } catch {
    if (revision === vesselRevision) bindingError.value = '船名航次加载失败'
  } finally {
    if (revision === vesselRevision) vesselsLoading.value = false
  }
}

let portsRevision = 0
async function loadPorts(id: string | null, origin: string | null = null, destination: string | null = null) {
  const revision = ++portsRevision
  voyageId.value = id
  originId.value = null
  destinationId.value = null
  portCalls.value = []
  bindingError.value = ''
  portsLoading.value = Boolean(id)
  if (!id) return
  try {
    const voyage = await getVesselSchedule(id)
    if (revision !== portsRevision) return
    portCalls.value = voyage.portCalls
    const originCall = portCalls.value.find(port => port.id === origin)
    const destinationCall = portCalls.value.find(port => port.id === destination)
    originId.value = originCall ? origin : null
    destinationId.value = originCall && destinationCall && destinationCall.sequence > originCall.sequence ? destination : null
  } catch {
    if (revision === portsRevision) bindingError.value = '挂靠港加载失败，请重新选择航次'
  } finally {
    if (revision === portsRevision) portsLoading.value = false
  }
}

function openBinding() {
  const binding = detail.value?.binding
  vesselOptions.value = binding?.vesselVoyage ? [{ label: binding.vesselVoyage, value: binding.voyageId }] : []
  bindingShow.value = true
  void loadPorts(binding?.vesselVoyage ? binding.voyageId : null, binding?.originCallId, binding?.destinationCallId)
  void searchVoyages('')
}

async function createVoyage(payload: VesselVoyagePayload) {
  if (creatingVoyage.value) return
  creatingVoyage.value = true
  try {
    const saved = await createVesselSchedule(payload)
    ++vesselRevision
    ++portsRevision
    vesselOptions.value = [
      { label: saved.vesselVoyage, value: saved.id },
      ...vesselOptions.value.filter(option => option.value !== saved.id),
    ]
    voyageId.value = saved.id
    portCalls.value = saved.portCalls
    originId.value = null
    destinationId.value = null
    vesselsLoading.value = false
    portsLoading.value = false
    bindingError.value = ''
    createVoyageShow.value = false
    message.success('航次已新增')
  } catch (e) {
    message.error(apiErrorMessage(e, '新增航次失败'))
  } finally {
    creatingVoyage.value = false
  }
}

async function save(unbind = false) {
  const bill = detail.value
  if (!bill || saving.value || (!unbind && !canSave.value)) return
  saving.value = true
  bindingError.value = ''
  try {
    detail.value = await bindBillOfLading(bill.billNo, unbind ? null : voyageId.value, originId.value, destinationId.value)
    bindingShow.value = false
    void load()
  } catch (e) {
    bindingError.value = e instanceof Error ? e.message : '航次保存失败'
  } finally {
    saving.value = false
  }
}

let trackingRevision = 0
async function openTracking(id: string) {
  const revision = ++trackingRevision
  const billNo = detail.value?.billNo
  try {
    const shipment = await getShipment(id)
    if (revision !== trackingRevision || !detailShow.value || detail.value?.billNo !== billNo) return
    trackingShipment.value = shipment
    trackingShow.value = true
  } catch {
    if (revision === trackingRevision) message.error('运单轨迹加载失败')
  }
}

async function reloadDetail() {
  const bill = detail.value
  if (!bill) return
  try {
    const refreshed = await getBillOfLading(bill.billNo)
    if (detail.value?.billNo === bill.billNo) detail.value = refreshed
  } catch {
    message.warning('提单刷新失败')
  }
}

function refreshDetail(shipment: Shipment) {
  trackingShipment.value = shipment
  void reloadDetail()
  void load()
}

onActivated(() => {
  void load()
  if (detailShow.value && detail.value) void reloadDetail()
})

const portTones: ReadonlyMap<string, string> = new Map([
  ['shanghai', 'sky'], ['上海', 'sky'], ['cnsha', 'sky'],
  ['ningbo', 'teal'], ['宁波', 'teal'], ['cnnbo', 'teal'],
  ['yantian', 'violet'], ['盐田', 'violet'], ['cnytn', 'violet'],
  ['xiamen', 'success'], ['厦门', 'success'], ['cnxmn', 'success'],
  ['los angeles', 'orange'], ['洛杉矶', 'orange'], ['uslax', 'orange'],
  ['long beach', 'cyan'], ['长滩', 'cyan'], ['uslgb', 'cyan'],
  ['new york', 'rose'], ['纽约', 'rose'], ['usnyc', 'rose'],
  ['oakland', 'indigo'], ['奥克兰', 'indigo'], ['usoak', 'indigo'],
])

function renderPorts(boundPort?: string | null, shipmentPorts?: string[] | null) {
  const ports = boundPort ? [boundPort] : shipmentPorts
  if (!ports?.length) return '—'

  return h('div', { class: 'flex flex-wrap gap-1' }, ports.map(port => {
    const tone = portTones.get(port.trim().toLowerCase()) ?? 'slate'
    return h('span', {
      class: 'max-w-full truncate rounded px-1.5 py-0.5 text-xs font-medium',
      style: { backgroundColor: `var(--tag-${tone}-bg)`, color: `var(--tag-${tone}-fg)` },
      title: port,
    }, port)
  }))
}

const columns: DataTableColumns<BillOfLading> = [
  { title: '提单号', key: 'billNo', width: 180, render: row => h(NButton, { text: true, type: 'primary', onClick: () => openDetail(row.billNo) }, () => row.billNo) },
  { title: '柜号', key: 'containers', width: 150, ellipsis: { tooltip: true }, render: row => row.containers.map(c => c.containerNo).filter(Boolean).join('、') || '—' },
  { title: '票数', key: 'shipmentCount', width: 70, align: 'right' },
  { title: '状态', key: 'billStatus', width: 124, render: renderBillStatus },
  { title: '国家', key: 'countries', width: 90, render: row => row.countries.join('、') || '—' },
  { title: '船名航次', key: 'voyage', width: 180, ellipsis: { tooltip: true }, render: row => row.binding?.vesselVoyage || '—' },
  { title: '起运港', key: 'originPort', width: 116, render: row => renderPorts(row.binding?.originPort, row.originPorts) },
  { title: '目的港', key: 'destinationPort', width: 116, render: row => renderPorts(row.binding?.destinationPort, row.destinationPorts) },
  { title: '预计离港', key: 'etd', width: 104, render: row => dateText(row.binding?.etd) },
  { title: '实际离港', key: 'atd', width: 104, render: row => dateText(row.binding?.atd) },
  { title: '预计到港', key: 'eta', width: 104, render: row => dateText(row.binding?.eta) },
  { title: '实际到港', key: 'ata', width: 104, render: row => dateText(row.binding?.ata) },
  { title: '清关', key: 'customs', minWidth: 166, render: row => {
    const tags = phases.flatMap(phase => {
      const states = row.containers.filter(c => !c.unassigned).map(c => c.customs[phase.key]?.status).filter(Boolean)
      if (states.includes('inspection')) return [h(NTag, { size: 'small', type: 'warning', bordered: false }, () => `${phase.label}查验`)]
      if (states.length && states.length === row.containers.length && states.every(value => value === 'released')) {
        return [h(NTag, { size: 'small', type: 'success', bordered: false }, () => `${phase.label}已放行`)]
      }
      return []
    })
    if (row.containers.some(c => c.unassigned && Object.values(c.customs).some(event => event?.status === 'inspection'))) {
      tags.push(h(NTag, { size: 'small', type: 'warning', bordered: false }, () => '查验柜号待核对'))
    }
    return tags.length ? h('div', { class: 'flex flex-wrap gap-1' }, tags) : '—'
  } },
]
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-2">
    <header class="flex min-w-0 shrink-0 items-center gap-2 overflow-x-auto pb-1">
      <h1 class="page-h2 mr-2 shrink-0 whitespace-nowrap">提单管理</h1>
      <div class="w-64 min-w-48">
        <NInput v-model:value="search" size="small" clearable placeholder="提单号／柜号／船名航次" aria-label="搜索提单" />
      </div>
      <div class="w-28 shrink-0">
        <NSelect v-model:value="country" :options="countries" size="small" aria-label="国家" />
      </div>
      <div class="w-32 shrink-0">
        <NSelect v-model:value="deliveryScope" :options="deliveryScopes" size="small" aria-label="签收情况" />
      </div>
      <div class="w-32 shrink-0">
        <NSelect v-model:value="state" :options="states" size="small" aria-label="提单状态" />
      </div>
      <div class="w-36 shrink-0">
        <NSelect v-model:value="originPort" :options="portOptions.origins" size="small" filterable clearable placeholder="起运港" aria-label="起运港筛选" />
      </div>
      <div class="w-36 shrink-0">
        <NSelect v-model:value="destinationPort" :options="portOptions.destinations" size="small" filterable clearable placeholder="目的港" aria-label="目的港筛选" />
      </div>
      <span class="ml-auto shrink-0 whitespace-nowrap text-sm text-[var(--color-muted)]">{{ total }} 个提单</span>
    </header>
    <p v-if="error" role="alert" class="text-sm text-red-600">{{ error }} <NButton text @click="load">重试</NButton></p>
    <div class="panel min-h-0 flex-1 overflow-hidden p-0">
      <NDataTable :columns="columns" :data="items" :row-key="rowKey" :loading="loading" :scroll-x="1608" :bordered="false" size="small" flex-height class="h-full" />
    </div>
    <NPagination v-if="total > pageSize" v-model:page="page" :page-size="pageSize" :item-count="total" class="self-end" />
  </div>

  <NDrawer :show="detailShow" :width="'min(860px, 100vw)'" :mask-closable="!bindingShow && !trackingShow" :close-on-esc="!bindingShow && !trackingShow" @update:show="closeDetail" @after-enter="scrollToContainer">
    <NDrawerContent :title="detail?.billNo || '提单详情'" closable>
      <NSpin :show="detailLoading">
        <div v-if="detail" ref="detailBody" class="space-y-4">
          <section class="panel space-y-2 p-3">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <NButton v-if="detail.binding?.vesselVoyage" text type="primary" title="在船期监控查看此航次" @click="openBoundVoyage">{{ detail.binding.vesselVoyage }}</NButton>
                <strong v-else>船名航次</strong>
                <NTag size="small" :type="detail.binding?.needsReview ? 'warning' : 'default'">{{ stateLabel(detail.state) }}</NTag>
              </div>
              <NButton size="small" secondary @click="openBinding">{{ detail.binding ? '修改绑定' : '绑定航次' }}</NButton>
            </div>
            <div v-if="detail.binding" class="grid gap-2 text-sm sm:grid-cols-2">
              <div><strong>{{ detail.binding.originPort || '起运港' }}</strong><p>实际离港 {{ dateText(detail.binding.atd) }} · 预计 {{ dateText(detail.binding.etd) }}</p></div>
              <div><strong>{{ detail.binding.destinationPort || '目的港' }}</strong><p>实际到港 {{ dateText(detail.binding.ata) }} · 预计 {{ dateText(detail.binding.eta) }}</p></div>
            </div>
          </section>
          <section v-for="container in detail.containers" :key="container.containerNo || ''" class="panel space-y-3 p-3"
            :data-container-no="container.containerNo ?? ''"
            :class="{ 'ring-1 ring-[var(--color-accent-text)]': focusedContainer === (container.containerNo ?? '') }">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="font-semibold">{{ container.containerNo || (container.unassigned ? '柜号待核对' : '柜号未录入') }}</h3>
              <span class="text-sm text-[var(--color-muted)]">{{ container.shipmentCount }} 票</span>
              <template v-for="phase in phases" :key="phase.key">
                <NTag v-if="container.customs[phase.key]" size="small" :type="container.customs[phase.key]?.status === 'inspection' ? 'warning' : 'success'">
                  {{ customsLabel(phase.label, container.customs[phase.key]!) }}
                </NTag>
              </template>
            </div>
            <dl v-if="Object.values(container.customs).some(Boolean)" class="grid gap-2 text-sm sm:grid-cols-2">
              <template v-for="phase in phases" :key="phase.key">
                <div v-if="container.customs[phase.key]" class="rounded border border-[var(--color-border)] px-2 py-1.5">
                  <dt>{{ phase.label }}来源 · {{ container.customs[phase.key]?.shipmentNo }}</dt>
                  <dd v-if="container.customs[phase.key]?.time" class="text-[var(--color-muted)]">{{ container.customs[phase.key]?.time }}</dd>
                  <dd v-if="container.customs[phase.key]?.description" class="break-words">{{ container.customs[phase.key]?.description }}</dd>
                </div>
              </template>
            </dl>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-sm">
                <thead class="text-[var(--color-muted)]">
                  <tr><th class="px-2 py-1">运单号</th><th class="px-2 py-1">客户</th><th class="px-2 py-1">渠道</th><th class="px-2 py-1">派送仓</th><th class="px-2 py-1">明细状态</th><th class="px-2 py-1">最新内部轨迹</th></tr>
                </thead>
                <tbody>
                  <tr v-for="row in container.shipments" :key="row.id" class="border-t border-[var(--color-border)]">
                    <td class="px-2 py-2 whitespace-nowrap"><NButton text type="primary" @click="openTracking(row.id)">{{ row.shipmentNo }}</NButton></td>
                    <td class="px-2 py-2">{{ row.customer || '—' }}</td>
                    <td class="px-2 py-2 whitespace-nowrap">{{ row.channelNameZh || row.channelCode?.trim() || '—' }}</td>
                    <td class="px-2 py-2 whitespace-nowrap">{{ row.addressCode || '—' }}</td>
                    <td class="px-2 py-2">
                      {{ routeStatusLabelZh(row.routeStatus) || '—' }}
                      <NTag v-if="conflict(row.vesselVoyage)" size="small" type="warning" :title="row.vesselVoyage || ''">航次不一致</NTag>
                    </td>
                    <td class="min-w-48 px-2 py-2">
                      <div v-if="row.latestTrackingTime" class="text-xs text-[var(--color-muted)]">{{ row.latestTrackingTime }}</div>
                      <div>{{ row.latestTrackingDesc || '—' }}</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </NSpin>
    </NDrawerContent>
  </NDrawer>

  <NModal :show="bindingShow && !createVoyageShow" preset="card" title="绑定船名航次" :style="{ width: 'min(640px, calc(100vw - 2rem))' }" :mask-closable="!saving" :close-on-esc="!saving" :closable="!saving" @update:show="bindingShow = $event">
    <div class="space-y-3">
      <div class="flex items-end gap-2">
        <label class="block min-w-0 flex-1 text-sm">船名航次
          <NSelect :value="voyageId" :options="vesselOptions" :loading="vesselsLoading" :disabled="saving" filterable remote placeholder="搜索现有航次" aria-label="船名航次" @search="searchVoyages" @update:value="id => loadPorts(id)" />
        </label>
        <NButton secondary :disabled="saving" @click="createVoyageShow = true">新增航次</NButton>
      </div>
      <NSpin v-if="voyageId && (portsLoading || portCalls.length)" :show="portsLoading">
        <BillPortCallPicker v-if="portCalls.length" :key="voyageId"
          v-model:origin-id="originId" v-model:destination-id="destinationId"
          :ports="portCalls" :disabled="saving || portsLoading" />
        <div v-else class="min-h-16" />
      </NSpin>
      <p v-else-if="voyageId && !bindingError" class="text-sm text-[var(--color-muted)]">该航次暂无挂靠港。</p>
      <p v-if="bindingError" role="alert" class="text-sm text-red-600">{{ bindingError }}</p>
      <div class="flex items-center gap-2">
        <NButton v-if="detail?.binding" quaternary :disabled="saving" @click="save(true)">解除绑定</NButton>
        <div class="ml-auto flex gap-2">
          <NButton :disabled="saving" @click="bindingShow = false">取消</NButton>
          <NButton type="primary" :loading="saving" :disabled="!canSave" @click="save()">保存</NButton>
        </div>
      </div>
    </div>
  </NModal>
  <VoyageFormModal v-if="bindingShow" v-model:show="createVoyageShow" mode="create" :initial="null" :submitting="creatingVoyage" require-port-pair @submit="createVoyage" />
  <ShipmentTrackingDrawer v-model:show="trackingShow" :shipment="trackingShipment" @shipment-updated="refreshDetail" />
</template>
