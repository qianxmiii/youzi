<script setup lang="ts">
import {
  NButton,
  NDatePicker,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSpace,
  useMessage,
} from 'naive-ui'
import { computed, onMounted, ref, watch } from 'vue'
import {
  listMaritimeScheduleProviders,
  previewExternalVesselSchedule,
} from '@/api/vesselSchedules'
import CarrierVesselSelect from '@/components/vessel-schedules/CarrierVesselSelect.vue'
import type {
  MaritimeScheduleProviderInfo,
  VesselVoyageDetail,
  VesselVoyagePayload,
} from '@/types/vesselSchedule'

const props = defineProps<{
  show: boolean
  mode: 'create' | 'edit'
  initial: VesselVoyageDetail | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  submit: [payload: VesselVoyagePayload]
}>()

const message = useMessage()

interface PortCallDraft {
  portName: string
  sequence: number
  eta: number | null
  ata: number | null
  etd: number | null
  atd: number | null
}

const vesselName = ref('')
const voyageNo = ref('')
const vesselCode = ref('')
const shippingCompany = ref('')
const vesselVoyage = ref('')
const notes = ref('')
const portCalls = ref<PortCallDraft[]>([])
const scheduleProviders = ref<MaritimeScheduleProviderInfo[]>([])
const fetchLoading = ref(false)
const fetchPeriod = ref(90)

const providerOptions = computed(() =>
  scheduleProviders.value.map((p) => ({
    label: p.label,
    value: p.shippingCompany,
  })),
)

const activeProvider = computed(() =>
  scheduleProviders.value.find((p) => p.shippingCompany === shippingCompany.value),
)

const carrierVesselSearchEnabled = computed(
  () => Boolean(activeProvider.value?.features?.vesselSearch),
)

onMounted(async () => {
  try {
    const res = await listMaritimeScheduleProviders()
    scheduleProviders.value = res.items
  } catch {
    /* 列表失败不阻塞手工录入 */
  }
})

function parseTs(raw: string | null | undefined): number | null {
  if (!raw) return null
  const t = Date.parse(raw.replace(' ', 'T'))
  return Number.isNaN(t) ? null : t
}

function formatTs(ts: number | null): string | null {
  if (ts == null) return null
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:00`
}

function resetForm() {
  if (props.mode === 'edit' && props.initial) {
    vesselName.value = props.initial.vesselName || ''
    voyageNo.value = props.initial.voyageNo || ''
    vesselCode.value = props.initial.vesselCode || ''
    shippingCompany.value = props.initial.shippingCompany || ''
    vesselVoyage.value = props.initial.vesselVoyage
    notes.value = props.initial.notes || ''
    portCalls.value = (props.initial.portCalls || []).map((pc) => ({
      portName: pc.portName,
      sequence: pc.sequence,
      eta: parseTs(pc.eta),
      ata: parseTs(pc.ata),
      etd: parseTs(pc.etd),
      atd: parseTs(pc.atd),
    }))
  } else {
    vesselName.value = ''
    voyageNo.value = ''
    vesselCode.value = ''
    shippingCompany.value = ''
    vesselVoyage.value = ''
    notes.value = ''
    portCalls.value = [{ portName: '', sequence: 1, eta: null, ata: null, etd: null, atd: null }]
  }
}

watch(
  () => [props.show, props.mode, props.initial] as const,
  ([visible]) => {
    if (visible) resetForm()
  },
)

const title = computed(() => (props.mode === 'create' ? '新建航次' : '编辑航次'))
const portCallCount = computed(() => portCalls.value.length)

function addPortCall() {
  portCalls.value.push({
    portName: '',
    sequence: portCalls.value.length + 1,
    eta: null,
    ata: null,
    etd: null,
    atd: null,
  })
}

function removePortCall(index: number) {
  portCalls.value.splice(index, 1)
  portCalls.value.forEach((pc, i) => {
    pc.sequence = i + 1
  })
}

function movePortCall(index: number, delta: number) {
  const target = index + delta
  if (target < 0 || target >= portCalls.value.length) return
  const copy = [...portCalls.value]
  const [item] = copy.splice(index, 1)
  copy.splice(target, 0, item)
  copy.forEach((pc, i) => {
    pc.sequence = i + 1
  })
  portCalls.value = copy
}

async function pullFromCarrier() {
  const company = shippingCompany.value.trim()
  const code = vesselCode.value.trim().toUpperCase()
  if (!company) {
    message.warning('请选择或填写船公司')
    return
  }
  if (!code) {
    message.warning('请先填写船舶代码')
    return
  }
  fetchLoading.value = true
  try {
    const data = await previewExternalVesselSchedule(company, code, fetchPeriod.value)
    vesselName.value = data.vesselName || ''
    voyageNo.value = data.voyageNo || ''
    vesselCode.value = data.vesselCode || code
    shippingCompany.value = data.shippingCompany || company
    vesselVoyage.value = data.vesselVoyage
    notes.value = data.notes || ''
    portCalls.value = (data.portCalls || []).map((pc) => ({
      portName: pc.portName,
      sequence: pc.sequence,
      eta: parseTs(pc.eta),
      ata: parseTs(pc.ata),
      etd: parseTs(pc.etd),
      atd: parseTs(pc.atd),
    }))
    if (!portCalls.value.length) {
      portCalls.value = [
        { portName: '', sequence: 1, eta: null, ata: null, etd: null, atd: null },
      ]
    }
    const label =
      scheduleProviders.value.find((p) => p.shippingCompany === data.shippingCompany)?.label ||
      data.shippingCompany
    message.success(`已从 ${label} 拉取 ${data.portCalls?.length ?? 0} 个挂靠港`)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '船期拉取失败')
  } finally {
    fetchLoading.value = false
  }
}

function handleSubmit() {
  const name = vesselName.value.trim()
  const voy = voyageNo.value.trim()
  const vv = vesselVoyage.value.trim()
  if (!vv && !name && !voy) {
    message.warning('请填写船名与航次，或填写船名航次')
    return
  }
  const cleaned = portCalls.value
    .map((pc, i) => ({
      portName: pc.portName.trim(),
      sequence: i + 1,
      eta: formatTs(pc.eta),
      ata: formatTs(pc.ata),
      etd: formatTs(pc.etd),
      atd: formatTs(pc.atd),
    }))
    .filter((pc) => pc.portName)
  if (!cleaned.length) {
    message.warning('请至少添加一个挂靠港口')
    return
  }
  emit('submit', {
    vesselVoyage: vv || null,
    vesselName: name || null,
    voyageNo: voy || null,
    vesselCode: vesselCode.value.trim() || null,
    shippingCompany: shippingCompany.value.trim() || null,
    notes: notes.value.trim(),
    portCalls: cleaned,
  })
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    class="voyage-form-modal"
    style="width: min(56rem, 96vw)"
    @update:show="emit('update:show', $event)"
  >
    <NForm label-placement="top" class="voyage-form-modal__form">
      <div class="grid gap-4 sm:grid-cols-2">
        <NFormItem label="船公司" class="sm:col-span-2">
          <NSelect
            v-model:value="shippingCompany"
            :options="providerOptions"
            filterable
            tag
            placeholder="选择已接入船公司"
          />
        </NFormItem>
        <NFormItem label="船名">
          <CarrierVesselSelect
            v-if="carrierVesselSearchEnabled"
            v-model:vessel-code="vesselCode"
            v-model:vessel-name="vesselName"
            :shipping-company="shippingCompany"
            :enabled="carrierVesselSearchEnabled"
          />
          <NInput v-else v-model:value="vesselName" placeholder="如 CSCL BOHAI SEA" />
        </NFormItem>
        <NFormItem label="航次">
          <NInput
            v-model:value="voyageNo"
            :placeholder="carrierVesselSearchEnabled ? '拉取船期后自动填充' : '如 076E'"
          />
        </NFormItem>
        <NFormItem v-if="!carrierVesselSearchEnabled" label="船舶代码">
          <NInput v-model:value="vesselCode" placeholder="船公司船舶代码" />
        </NFormItem>
        <NFormItem v-else label="船舶代码">
          <NInput v-model:value="vesselCode" readonly placeholder="选择船名后自动填入" />
        </NFormItem>
        <NFormItem label="拉取船期" class="sm:col-span-2">
          <div class="flex w-full flex-wrap items-center gap-2">
            <NInputNumber
              v-model:value="fetchPeriod"
              class="w-28"
              :min="7"
              :max="90"
              placeholder="查询天数"
            />
            <NButton :loading="fetchLoading" :disabled="!vesselCode" @click="pullFromCarrier">
              拉取挂靠港
            </NButton>
            <span v-if="carrierVesselSearchEnabled" class="text-xs text-[var(--color-muted)]">
              先选船名，再拉取挂靠；航次由船公司接口返回
            </span>
          </div>
        </NFormItem>
        <NFormItem label="船名航次" class="sm:col-span-2">
          <NInput
            v-model:value="vesselVoyage"
            placeholder="可选；留空时由船名/航次自动组合，如 CSCL BOHAI SEA/076E"
          />
        </NFormItem>
        <NFormItem label="备注" class="sm:col-span-2">
          <NInput v-model:value="notes" placeholder="可选" />
        </NFormItem>
      </div>

      <div class="mb-2 flex shrink-0 items-center justify-between gap-2">
        <div class="min-w-0">
          <div class="text-sm font-medium text-zinc-300">挂靠港口</div>
          <div v-if="portCallCount > 0" class="text-xs text-[var(--color-muted)]">
            共 {{ portCallCount }} 个，列表可滚动
          </div>
        </div>
        <NButton size="small" class="shrink-0" @click="addPortCall">添加港口</NButton>
      </div>

      <div class="voyage-form-modal__ports space-y-3">
        <div
          v-for="(pc, index) in portCalls"
          :key="index"
          class="rounded-lg border border-[var(--color-border)] p-3"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <span class="text-xs text-zinc-500">#{{ index + 1 }}</span>
            <NSpace size="small">
              <NButton size="tiny" quaternary :disabled="index === 0" @click="movePortCall(index, -1)">
                上移
              </NButton>
              <NButton
                size="tiny"
                quaternary
                :disabled="index === portCalls.length - 1"
                @click="movePortCall(index, 1)"
              >
                下移
              </NButton>
              <NButton
                size="tiny"
                quaternary
                type="error"
                :disabled="portCalls.length <= 1"
                @click="removePortCall(index)"
              >
                删除
              </NButton>
            </NSpace>
          </div>
          <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <NFormItem label="港口" class="sm:col-span-2 lg:col-span-1">
              <NInput
                v-model:value="pc.portName"
                placeholder="船公司返回名称，如 Yantian"
              />
            </NFormItem>
            <NFormItem label="ETD">
              <NDatePicker v-model:value="pc.etd" type="datetime" clearable class="w-full" />
            </NFormItem>
            <NFormItem label="ATD">
              <NDatePicker v-model:value="pc.atd" type="datetime" clearable class="w-full" />
            </NFormItem>
            <NFormItem label="ETA">
              <NDatePicker v-model:value="pc.eta" type="datetime" clearable class="w-full" />
            </NFormItem>
            <NFormItem label="ATA">
              <NDatePicker v-model:value="pc.ata" type="datetime" clearable class="w-full" />
            </NFormItem>
          </div>
        </div>
      </div>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" @click="handleSubmit">保存</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<style scoped>
.voyage-form-modal :deep(.n-card) {
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.voyage-form-modal :deep(.n-card__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.voyage-form-modal__form {
  display: flex;
  flex-direction: column;
  min-height: 0;
  max-height: calc(90vh - 7.5rem);
}

.voyage-form-modal__ports {
  flex: 1;
  min-height: 8rem;
  max-height: min(50vh, 28rem);
  overflow-y: auto;
  padding-right: 0.25rem;
}
</style>
