<script setup lang="ts">
import {
  NButton,
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
    } else {
      form.value = emptyShipmentForm()
    }
  },
)

function handleSubmit() {
  const no = (form.value.shipmentNo || '').trim()
  if (!no) {
    message.warning('请填写运单号')
    return
  }
  submitting.value = true
  emit('submit', { ...form.value, shipmentNo: no })
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
          <NInput v-model:value="form.etd" placeholder="YYYY-MM-DD HH:mm:ss" />
        </NFormItem>
        <NFormItem label="ETA">
          <NInput v-model:value="form.eta" placeholder="YYYY-MM-DD HH:mm:ss" />
        </NFormItem>
        <NFormItem label="ATD">
          <NInput v-model:value="form.atd" placeholder="YYYY-MM-DD HH:mm:ss" />
        </NFormItem>
        <NFormItem label="ATA">
          <NInput v-model:value="form.ata" placeholder="YYYY-MM-DD HH:mm:ss" />
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
