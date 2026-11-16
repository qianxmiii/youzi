<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NModal } from 'naive-ui'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { previewShipmentAmzPush, type AmzPushResult } from '@/api/shipments'
import type { Shipment } from '@/types/shipment'

const props = defineProps<{
  show: boolean
  shipment: Shipment | null
  saving?: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [
    payload: {
      pushAmzUpdate: boolean
      customerShipmentId: string
      amazonRefId: string
      amzPushOriginPort: string
      amzPushDestPort: string
    },
  ]
}>()

const customerShipmentId = ref('')
const amazonRefId = ref('')
const originPort = ref('')
const destPort = ref('')
const previewLoading = ref(false)
let previewVersion = 0
const preview = ref<AmzPushResult | null>(null)
const nowMs = ref(Date.now())
let tickTimer: ReturnType<typeof setInterval> | null = null

const cooldownSec = computed(() => {
  const raw = props.shipment?.amzPushAt?.trim()
  if (!raw) return 0
  const pushed = Date.parse(raw.replace(' ', 'T'))
  if (!Number.isFinite(pushed)) return 0
  const left = 60 - Math.floor((nowMs.value - pushed) / 1000)
  return left > 0 ? left : 0
})

const currentPayload = computed(() => JSON.stringify([
  customerShipmentId.value.trim(), amazonRefId.value.trim(),
  originPort.value.trim().toUpperCase(), destPort.value.trim().toUpperCase(),
]))
const lastResult = computed(() => {
  try { return JSON.parse(props.shipment?.amzPushResult || 'null') as (AmzPushResult & { recordedAt?: string }) | null }
  catch { return null }
})
const synced = computed(() => props.shipment?.amzPushSuccessPayload === currentPayload.value)
const savedPayload = computed(() => JSON.stringify([
  props.shipment?.customerShipmentId?.trim() || '', props.shipment?.amazonRefId?.trim() || '',
  props.shipment?.amzPushOriginPort?.trim().toUpperCase() || '', props.shipment?.amzPushDestPort?.trim().toUpperCase() || '',
]))
const retry = computed(() => !!lastResult.value && !lastResult.value.ok && currentPayload.value === savedPayload.value)
const previewHint = computed(() => {
  const message = preview.value?.message?.trim()
  if (!message) return ''
  return message
})

watch(
  () => [props.show, props.shipment?.id] as const,
  ([visible]) => {
    if (!visible || !props.shipment) return
    customerShipmentId.value = props.shipment.customerShipmentId?.trim() ?? ''
    amazonRefId.value = props.shipment.amazonRefId?.trim() ?? ''
    originPort.value = props.shipment.amzPushOriginPort?.trim() || ''
    destPort.value = props.shipment.amzPushDestPort?.trim() || ''
    preview.value = null
    void loadPreview()
  },
)

watch(
  () => props.show,
  (visible) => {
    if (tickTimer) {
      clearInterval(tickTimer)
      tickTimer = null
    }
    if (!visible) return
    nowMs.value = Date.now()
    tickTimer = setInterval(() => {
      nowMs.value = Date.now()
    }, 1000)
  },
)

onBeforeUnmount(() => {
  if (tickTimer) clearInterval(tickTimer)
})

async function loadPreview() {
  const shipment = props.shipment
  if (!props.show || !shipment) return
  const version = ++previewVersion
  previewLoading.value = true
  try {
    const result = await previewShipmentAmzPush(shipment.id)
    if (version !== previewVersion || !props.show || props.shipment?.id !== shipment.id) return
    preview.value = result
    if (!originPort.value) originPort.value = shipment.amzPushOriginPort?.trim() || result.originPort || ''
    if (!destPort.value) destPort.value = shipment.amzPushDestPort?.trim() || result.destinationPort || ''
  } catch {
    if (version === previewVersion) preview.value = null
  } finally {
    if (version === previewVersion) previewLoading.value = false
  }
}

function submit(pushAmzUpdate: boolean) {
  if (props.saving || previewLoading.value || (pushAmzUpdate && cooldownSec.value > 0)) return
  emit('save', {
    pushAmzUpdate,
    customerShipmentId: customerShipmentId.value.trim(),
    amazonRefId: amazonRefId.value.trim(),
    amzPushOriginPort: originPort.value.trim().toUpperCase(),
    amzPushDestPort: destPort.value.trim().toUpperCase(),
  })
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="补货件号 / 预约号"
    :style="{ width: '440px', maxWidth: 'calc(100vw - 2rem)' }"
    :mask-closable="!saving"
    @update:show="(v: boolean) => { if (!v) emit('close') }"
  >
    <p class="mb-3 text-xs leading-relaxed text-[var(--color-fg-secondary)]">
      派送仓库为 4 位时需核对货件号和亚马逊预约号。只填 1 视为未填。起运港、目的港已按规则填入默认值，可直接修改；可只保存到本地，或保存后按窗口里的港口推送。
    </p>
    <NForm :disabled="saving || previewLoading" label-placement="left" label-width="108" size="small">
      <NFormItem label="运单号">
        <span class="text-sm text-[var(--color-fg)]">{{ shipment?.shipmentNo || '—' }}</span>
      </NFormItem>
      <NFormItem label="派送仓库">
        <span class="text-sm text-[var(--color-fg)]">{{ shipment?.addressCode || '—' }}</span>
      </NFormItem>
      <NFormItem label="货件号">
        <NInput v-model:value="customerShipmentId" placeholder="货件号" clearable />
      </NFormItem>
      <NFormItem label="亚马逊预约号">
        <NInput v-model:value="amazonRefId" placeholder="亚马逊预约号" clearable />
      </NFormItem>
      <NFormItem label="起运港">
        <NInput v-model:value="originPort" placeholder="默认按规则填入" clearable />
      </NFormItem>
      <NFormItem label="目的港">
        <NInput v-model:value="destPort" placeholder="默认按规则填入" clearable />
      </NFormItem>
    </NForm>
    <p v-if="previewHint" class="mt-1 text-xs leading-relaxed text-[var(--color-fg-secondary)]">
      {{ previewHint }}
    </p>
    <p v-if="cooldownSec > 0" class="mt-1 text-xs text-amber-600">
      这一票推送冷却中，还需 {{ cooldownSec }} 秒
    </p>
    <p class="mt-2 text-xs" :class="synced ? 'text-green-600' : 'text-amber-600'">
      {{ synced ? '已同步' : '有修改待推送 / 尚未同步' }}
    </p>
    <p v-if="lastResult" class="mt-1 text-xs text-[var(--color-fg-secondary)]">
      最近结果 {{ lastResult.recordedAt }}：{{ lastResult.message }}
    </p>
    <div class="mt-2 flex justify-end gap-2">
      <NButton size="small" :disabled="saving" @click="emit('close')">关闭</NButton>
      <NButton size="small" :disabled="saving || previewLoading" @click="submit(false)">保存</NButton>
      <NButton size="small" type="primary" :loading="saving" :disabled="saving || previewLoading || cooldownSec > 0" @click="submit(true)">
        {{ cooldownSec > 0 ? `还需等待 ${cooldownSec} 秒` : retry ? '重试推送' : '保存并推送' }}
      </NButton>
    </div>
  </NModal>
</template>
