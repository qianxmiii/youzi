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
    originPort.value = ''
    destPort.value = ''
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
  try {
    const result = await previewShipmentAmzPush(shipment.id)
    preview.value = result
    originPort.value = shipment.amzPushOriginPort?.trim() || result.originPort || ''
    destPort.value = shipment.amzPushDestPort?.trim() || result.destinationPort || ''
  } catch {
    preview.value = null
    originPort.value = shipment.amzPushOriginPort?.trim() || ''
    destPort.value = shipment.amzPushDestPort?.trim() || ''
  }
}

function submit() {
  emit('save', {
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
      派送仓库为 4 位时需核对货件号和亚马逊预约号。只填 1 视为未填。起运港、目的港已按规则填入默认值，可直接修改；保存货件号后按窗口里的港口推送。
    </p>
    <NForm label-placement="left" label-width="108" size="small">
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
    <div class="mt-2 flex justify-end gap-2">
      <NButton size="small" :disabled="saving" @click="emit('close')">取消</NButton>
      <NButton size="small" type="primary" :loading="saving" @click="submit">保存</NButton>
    </div>
  </NModal>
</template>
