<script setup lang="ts">
import {
  NButton,
  NDatePicker,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSpace,
  useMessage,
} from 'naive-ui'
import { computed, ref, watch } from 'vue'
import type { VesselVoyageDetail, VesselVoyagePayload } from '@/types/vesselSchedule'

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

const vesselVoyage = ref('')
const notes = ref('')
const portCalls = ref<PortCallDraft[]>([])

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

function handleSubmit() {
  const vv = vesselVoyage.value.trim()
  if (!vv) {
    message.warning('请填写船名航次')
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
    vesselVoyage: vv,
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
    class="max-w-4xl"
    @update:show="emit('update:show', $event)"
  >
    <NForm label-placement="top">
      <div class="grid gap-4 sm:grid-cols-2">
        <NFormItem label="船名航次" required>
          <NInput v-model:value="vesselVoyage" placeholder="如 CSCL BOHAI SEA/076E" />
        </NFormItem>
        <NFormItem label="备注">
          <NInput v-model:value="notes" placeholder="可选" />
        </NFormItem>
      </div>

      <div class="mb-2 flex items-center justify-between">
        <div class="text-sm font-medium text-zinc-300">挂靠港口</div>
        <NButton size="small" @click="addPortCall">添加港口</NButton>
      </div>

      <div class="space-y-3">
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
              <NInput v-model:value="pc.portName" placeholder="Yantian" />
            </NFormItem>
            <NFormItem label="ETA">
              <NDatePicker v-model:value="pc.eta" type="datetime" clearable class="w-full" />
            </NFormItem>
            <NFormItem label="ATA">
              <NDatePicker v-model:value="pc.ata" type="datetime" clearable class="w-full" />
            </NFormItem>
            <NFormItem label="ETD">
              <NDatePicker v-model:value="pc.etd" type="datetime" clearable class="w-full" />
            </NFormItem>
            <NFormItem label="ATD">
              <NDatePicker v-model:value="pc.atd" type="datetime" clearable class="w-full" />
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
