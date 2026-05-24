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
import { computed, ref, watch } from 'vue'
import { useDictLabels } from '@/composables/useDictLabels'
import type { Shipment, ShipmentPayload } from '@/types/shipment'
import { emptyShipmentForm } from '@/types/shipment'
import { dateOnlyToTimestamp, formatDateOnlyForApi } from '@/utils/formatDateTime'
import { normalizeLastMileTrackingNumber } from '@/utils/lastMileTracking'

const { loadDictTypes, dictOptions } = useDictLabels()

const props = defineProps<{
  show: boolean
  mode: 'create' | 'edit'
  initial?: Shipment | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: ShipmentPayload]
}>()

const message = useMessage()
const form = ref<ShipmentPayload>(emptyShipmentForm())
const submitting = ref(false)
const etd = ref<number | null>(null)
const eta = ref<number | null>(null)
const atd = ref<number | null>(null)
const ata = ref<number | null>(null)

function syncVoyageDatesFromForm() {
  etd.value = dateOnlyToTimestamp(form.value.etd)
  eta.value = dateOnlyToTimestamp(form.value.eta)
  atd.value = dateOnlyToTimestamp(form.value.atd)
  ata.value = dateOnlyToTimestamp(form.value.ata)
}

function applyVoyageDatesToForm() {
  form.value.etd = etd.value != null ? formatDateOnlyForApi(etd.value) : null
  form.value.eta = eta.value != null ? formatDateOnlyForApi(eta.value) : null
  form.value.atd = atd.value != null ? formatDateOnlyForApi(atd.value) : null
  form.value.ata = ata.value != null ? formatDateOnlyForApi(ata.value) : null
}

const title = computed(() => (props.mode === 'create' ? '新增运单' : '编辑运单'))

const addressTypeOptions = dictOptions('address_type')

const statusOptions = [
  { label: '转运中', value: 'IN_TRANSIT' },
  { label: '已签收', value: 'DELIVERED' },
  { label: '查验', value: 'INSPECTION' },
  { label: '未知', value: 'UNKNOWN' },
]

watch(
  () => props.show,
  (visible) => {
    if (visible) void loadDictTypes('address_type')
  },
)

watch(
  () => [props.show, props.mode, props.initial] as const,
  ([visible]) => {
    if (!visible) return
    if (props.mode === 'edit' && props.initial) {
      form.value = {
        shipmentNo: props.initial.shipmentNo,
        customer: props.initial.customer,
        customerNo: props.initial.customerNo,
        channelCode: props.initial.channelCode,
        countryCode: props.initial.countryCode,
        addressType: props.initial.addressType,
        addressCode: props.initial.addressCode,
        deliveryAddress: props.initial.deliveryAddress,
        ctns: props.initial.ctns,
        zipcode: props.initial.zipcode,
        productName: props.initial.productName,
        originWarehouseCode: props.initial.originWarehouseCode,
        supplierName: props.initial.supplierName,
        carrierCode: props.initial.carrierCode,
        carrierId: props.initial.carrierId,
        trackingNumber: props.initial.trackingNumber,
        customerShipmentId: props.initial.customerShipmentId,
        amazonRefId: props.initial.amazonRefId,
        vesselName: props.initial.vesselName,
        voyageNo: props.initial.voyageNo,
        vesselVoyage: props.initial.vesselVoyage,
        etd: props.initial.etd,
        eta: props.initial.eta,
        atd: props.initial.atd,
        ata: props.initial.ata,
        originPortCode: props.initial.originPortCode,
        destinationPortCode: props.initial.destinationPortCode,
        deliveredTime: props.initial.deliveredTime,
        statusCode: props.initial.statusCode || 'UNKNOWN',
      }
      syncVoyageDatesFromForm()
    } else {
      form.value = emptyShipmentForm()
      etd.value = null
      eta.value = null
      atd.value = null
      ata.value = null
    }
  },
)

function handleSubmit() {
  const no = (form.value.shipmentNo || '').trim()
  if (!no) {
    message.warning('请填写运单号')
    return
  }
  applyVoyageDatesToForm()
  submitting.value = true
  const carrierId = normalizeLastMileTrackingNumber(form.value.carrierId) || null
  const trackingNumber = normalizeLastMileTrackingNumber(form.value.trackingNumber) || null
  emit('submit', {
    ...form.value,
    shipmentNo: no,
    carrierId,
    trackingNumber,
  })
  submitting.value = false
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    class="shipment-form-modal"
    style="width: min(720px, 96vw); max-height: 90vh"
    :mask-closable="false"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <NForm label-placement="top" size="small" class="max-h-[65vh] overflow-y-auto pr-1">
      <div class="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <NFormItem label="运单号" required>
          <NInput
            v-model:value="form.shipmentNo"
            placeholder="DPSECO..."
            :disabled="mode === 'edit'"
          />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect v-model:value="form.statusCode" :options="statusOptions" />
        </NFormItem>
        <NFormItem label="客户">
          <NInput v-model:value="form.customer" placeholder="用户名/客户名" />
        </NFormItem>
        <NFormItem label="客户订单号">
          <NInput v-model:value="form.customerNo" />
        </NFormItem>
        <NFormItem label="国家">
          <NInput v-model:value="form.countryCode" placeholder="US / 美国" />
        </NFormItem>
        <NFormItem label="件数">
          <NInputNumber v-model:value="form.ctns" :min="0" class="w-full" />
        </NFormItem>
        <NFormItem label="品名">
          <NInput v-model:value="form.productName" />
        </NFormItem>
        <NFormItem label="渠道">
          <NInput v-model:value="form.channelCode" />
        </NFormItem>
        <NFormItem label="承运商">
          <NInput v-model:value="form.carrierCode" />
        </NFormItem>
        <NFormItem label="承运单号">
          <NInput
            v-model:value="form.carrierId"
            placeholder="承运商侧主单号（同步可自动填入）"
            clearable
          />
        </NFormItem>
        <NFormItem label="转单号">
          <NInput
            v-model:value="form.trackingNumber"
            placeholder="尾程 UPS/FedEx 等"
            clearable
          />
        </NFormItem>
        <NFormItem label="地址类型">
          <NSelect v-model:value="form.addressType" clearable :options="addressTypeOptions" />
        </NFormItem>
        <NFormItem label="派送仓库/代码">
          <NInput v-model:value="form.addressCode" />
        </NFormItem>
        <NFormItem label="派送地址" class="sm:col-span-2">
          <NInput v-model:value="form.deliveryAddress" type="textarea" :rows="2" />
        </NFormItem>
        <NFormItem label="邮编">
          <NInput v-model:value="form.zipcode" />
        </NFormItem>
        <NFormItem label="交货仓库">
          <NInput v-model:value="form.originWarehouseCode" />
        </NFormItem>
        <NFormItem label="供应商">
          <NInput v-model:value="form.supplierName" />
        </NFormItem>
        <NFormItem label="货件号">
          <NInput v-model:value="form.customerShipmentId" />
        </NFormItem>
        <NFormItem label="亚马逊预约号">
          <NInput v-model:value="form.amazonRefId" />
        </NFormItem>
        <NFormItem label="船名">
          <NInput v-model:value="form.vesselName" />
        </NFormItem>
        <NFormItem label="航次">
          <NInput v-model:value="form.voyageNo" />
        </NFormItem>
        <NFormItem label="船名航次">
          <NInput v-model:value="form.vesselVoyage" />
        </NFormItem>
        <NFormItem label="ETD">
          <NDatePicker v-model:value="etd" type="date" clearable class="w-full" />
        </NFormItem>
        <NFormItem label="ETA">
          <NDatePicker v-model:value="eta" type="date" clearable class="w-full" />
        </NFormItem>
        <NFormItem label="ATD">
          <NDatePicker v-model:value="atd" type="date" clearable class="w-full" />
        </NFormItem>
        <NFormItem label="ATA">
          <NDatePicker v-model:value="ata" type="date" clearable class="w-full" />
        </NFormItem>
        <NFormItem label="出发港口">
          <NInput v-model:value="form.originPortCode" />
        </NFormItem>
        <NFormItem label="到达港口">
          <NInput v-model:value="form.destinationPortCode" />
        </NFormItem>
        <NFormItem label="签收时间">
          <NInput v-model:value="form.deliveredTime" placeholder="YYYY-MM-DD HH:mm:ss" />
        </NFormItem>
      </div>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" :loading="submitting" @click="handleSubmit">
          {{ mode === 'create' ? '创建' : '保存' }}
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
