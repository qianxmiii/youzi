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
import { listCodeTableRows } from '@/api/codeTables'
import { useDictLabels } from '@/composables/useDictLabels'
import type { CodeTableRow } from '@/types/codeTable'
import type { Shipment, ShipmentPayload } from '@/types/shipment'
import { emptyShipmentForm } from '@/types/shipment'
import { PAYMENT_STATUS_EDIT_OPTIONS } from '@/constants/shipmentFilters'
import {
  buildCarrierFormSelectOptionsWithCurrent,
  resolveCarrierFormSelectValue,
} from '@/utils/carrierFilterOptions'
import {
  dateOnlyToTimestamp,
  formatDateOnlyForApi,
  formatTimestampForApi,
  parseDateTimeInput,
} from '@/utils/formatDateTime'
import { EXPRESS_CODE_OPTIONS } from '@/constants/expressCodes'
import { normalizeLastMileTrackingNumber } from '@/utils/lastMileTracking'

const { loadDictTypes, dictOptions } = useDictLabels()

const props = defineProps<{
  show: boolean
  mode: 'create' | 'edit'
  initial?: Shipment | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: Partial<ShipmentPayload> & { shipmentNo: string }]
}>()

const message = useMessage()
const form = ref<ShipmentPayload>(emptyShipmentForm())
const submitting = ref(false)
const carrierCodeRows = ref<CodeTableRow[]>([])
const initialCarrierNameZh = ref<string | null>(null)
const etd = ref<number | null>(null)
const eta = ref<number | null>(null)
const atd = ref<number | null>(null)
const ata = ref<number | null>(null)
const expectedDeliveryAt = ref<number | null>(null)
const warehouseEntryAt = ref<number | null>(null)
const deliveredAt = ref<number | null>(null)

function syncVoyageDatesFromForm() {
  etd.value = dateOnlyToTimestamp(form.value.etd)
  eta.value = dateOnlyToTimestamp(form.value.eta)
  atd.value = dateOnlyToTimestamp(form.value.atd)
  ata.value = dateOnlyToTimestamp(form.value.ata)
  expectedDeliveryAt.value = dateOnlyToTimestamp(form.value.expectedDeliveryTime)
}

function applyVoyageDatesToForm() {
  form.value.etd = etd.value != null ? formatDateOnlyForApi(etd.value) : null
  form.value.eta = eta.value != null ? formatDateOnlyForApi(eta.value) : null
  form.value.atd = atd.value != null ? formatDateOnlyForApi(atd.value) : null
  form.value.ata = ata.value != null ? formatDateOnlyForApi(ata.value) : null
  form.value.expectedDeliveryTime =
    expectedDeliveryAt.value != null ? formatDateOnlyForApi(expectedDeliveryAt.value) : null
}

function syncDeliveredTimeFromForm() {
  const parsed = parseDateTimeInput(form.value.deliveredTime)
  deliveredAt.value = parsed ? parsed.getTime() : null
}

function syncWarehouseEntryTimeFromForm() {
  const parsed = parseDateTimeInput(form.value.warehouseEntryTime)
  warehouseEntryAt.value = parsed ? parsed.getTime() : null
}

function applyDeliveredTimeToForm() {
  form.value.deliveredTime =
    deliveredAt.value != null ? formatTimestampForApi(deliveredAt.value) : null
}

function applyWarehouseEntryTimeToForm() {
  form.value.warehouseEntryTime =
    warehouseEntryAt.value != null ? formatTimestampForApi(warehouseEntryAt.value) : null
}

const title = computed(() => (props.mode === 'create' ? '新增运单' : '编辑运单'))

/** 已付款运单仅允许改回未付款，其它字段只读 */
const paidLocked = computed(
  () =>
    props.mode === 'edit' &&
    (props.initial?.paymentStatus || '').trim().toUpperCase() === 'PAID',
)

const addressTypeOptions = dictOptions('address_type')

const carrierSelectOptions = computed(() =>
  buildCarrierFormSelectOptionsWithCurrent(
    carrierCodeRows.value,
    form.value.carrierCode,
    initialCarrierNameZh.value,
  ),
)

async function loadCarrierOptions() {
  try {
    const res = await listCodeTableRows('carrier_codes', { limit: 500 })
    carrierCodeRows.value = res.items
  } catch {
    carrierCodeRows.value = []
  }
}

const statusOptions = [
  { label: '转运中', value: 'IN_TRANSIT' },
  { label: '已签收', value: 'DELIVERED' },
  { label: '查验', value: 'INSPECTION' },
  { label: '未知', value: 'UNKNOWN' },
]

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      void loadDictTypes('address_type')
      void loadCarrierOptions()
    }
  },
)

watch(
  () => [props.show, props.mode, props.initial, carrierCodeRows.value] as const,
  ([visible]) => {
    if (!visible) return
    if (props.mode === 'edit' && props.initial) {
      initialCarrierNameZh.value = props.initial.carrierNameZh ?? null
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
        carrierCode: resolveCarrierFormSelectValue(
          props.initial.carrierCode,
          carrierCodeRows.value,
        ),
        carrierId: props.initial.carrierId,
        trackingNumber: props.initial.trackingNumber,
        expressCode: props.initial.expressCode ?? null,
        customerShipmentId: props.initial.customerShipmentId,
        amazonRefId: props.initial.amazonRefId,
        billOfLadingNo: props.initial.billOfLadingNo,
        containerNo: props.initial.containerNo,
        vesselName: props.initial.vesselName,
        voyageNo: props.initial.voyageNo,
        vesselVoyage: props.initial.vesselVoyage,
        etd: props.initial.etd,
        eta: props.initial.eta,
        atd: props.initial.atd,
        ata: props.initial.ata,
        originPortCode: props.initial.originPortCode,
        destinationPortCode: props.initial.destinationPortCode,
        expectedDeliveryTime: props.initial.expectedDeliveryTime,
        warehouseEntryTime: props.initial.warehouseEntryTime,
        deliveredTime: props.initial.deliveredTime,
        statusCode: props.initial.statusCode || 'UNKNOWN',
        paymentStatus: props.initial.paymentStatus ?? null,
      }
      syncVoyageDatesFromForm()
      syncWarehouseEntryTimeFromForm()
      syncDeliveredTimeFromForm()
    } else {
      initialCarrierNameZh.value = null
      form.value = emptyShipmentForm()
      etd.value = null
      eta.value = null
      atd.value = null
      ata.value = null
      expectedDeliveryAt.value = null
      warehouseEntryAt.value = null
      deliveredAt.value = null
    }
  },
)

function handleSubmit() {
  const no = (form.value.shipmentNo || '').trim()
  if (!no) {
    message.warning('请填写运单号')
    return
  }
  if (paidLocked.value) {
    const ps = (form.value.paymentStatus || '').trim().toUpperCase()
    if (ps !== 'UNPAID') {
      message.warning('已付款运单仅可改为未付款；改回未付款后再编辑其它字段')
      return
    }
    submitting.value = true
    emit('submit', { shipmentNo: no, paymentStatus: 'UNPAID' })
    submitting.value = false
    return
  }
  applyVoyageDatesToForm()
  applyWarehouseEntryTimeToForm()
  applyDeliveredTimeToForm()
  submitting.value = true
  const carrierId = normalizeLastMileTrackingNumber(form.value.carrierId) || null
  const trackingNumber = normalizeLastMileTrackingNumber(form.value.trackingNumber) || null
  const expressCode = (form.value.expressCode || '').trim() || null
  const carrierCode = (form.value.carrierCode || '').trim() || null
  const billOfLadingNo = (form.value.billOfLadingNo || '').trim() || null
  const containerNo = (form.value.containerNo || '').trim() || null
  emit('submit', {
    ...form.value,
    shipmentNo: no,
    carrierCode,
    carrierId,
    trackingNumber,
    expressCode,
    billOfLadingNo,
    containerNo,
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
      <p
        v-if="paidLocked"
        class="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800"
      >
        已付款运单已锁定，仅可将付款状态改为「未付款」；改回后再编辑其它字段。
      </p>
      <div class="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <NFormItem label="运单号" required>
          <NInput
            v-model:value="form.shipmentNo"
            placeholder="DPSECO..."
            :disabled="mode === 'edit'"
          />
        </NFormItem>
        <NFormItem label="状态">
          <NSelect
            v-model:value="form.statusCode"
            :options="statusOptions"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="付款状态">
          <NSelect
            v-model:value="form.paymentStatus"
            :options="[...PAYMENT_STATUS_EDIT_OPTIONS]"
            clearable
            placeholder="未设置"
          />
        </NFormItem>
        <NFormItem label="客户">
          <NInput
            v-model:value="form.customer"
            placeholder="用户名/客户名"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="客户订单号">
          <NInput v-model:value="form.customerNo" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="国家">
          <NInput
            v-model:value="form.countryCode"
            placeholder="US / 美国"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="件数">
          <NInputNumber
            v-model:value="form.ctns"
            :min="0"
            class="w-full"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="品名">
          <NInput v-model:value="form.productName" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="渠道">
          <NInput v-model:value="form.channelCode" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="承运商">
          <NSelect
            v-model:value="form.carrierCode"
            :options="carrierSelectOptions"
            clearable
            filterable
            placeholder="选择承运商"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="承运单号">
          <NInput
            v-model:value="form.carrierId"
            placeholder="承运商侧主单号（同步可自动填入）"
            clearable
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="转单号">
          <NInput
            v-model:value="form.trackingNumber"
            placeholder="尾程 UPS/FedEx 等"
            clearable
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="尾程快递">
          <NSelect
            v-model:value="form.expressCode"
            :options="EXPRESS_CODE_OPTIONS"
            clearable
            placeholder="自动识别"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="地址类型">
          <NSelect
            v-model:value="form.addressType"
            clearable
            :options="addressTypeOptions"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="派送仓库/代码">
          <NInput v-model:value="form.addressCode" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="派送地址" class="sm:col-span-2">
          <NInput
            v-model:value="form.deliveryAddress"
            type="textarea"
            :rows="2"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="邮编">
          <NInput v-model:value="form.zipcode" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="交货仓库">
          <NInput v-model:value="form.originWarehouseCode" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="供应商">
          <NInput v-model:value="form.supplierName" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="货件号">
          <NInput v-model:value="form.customerShipmentId" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="亚马逊预约号">
          <NInput v-model:value="form.amazonRefId" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="提单号">
          <NInput
            v-model:value="form.billOfLadingNo"
            placeholder="海运提单号"
            clearable
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="柜号">
          <NInput
            v-model:value="form.containerNo"
            placeholder="集装箱号"
            clearable
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="船名">
          <NInput v-model:value="form.vesselName" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="航次">
          <NInput v-model:value="form.voyageNo" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="船名航次">
          <NInput v-model:value="form.vesselVoyage" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="ETD">
          <NDatePicker
            v-model:value="etd"
            type="date"
            clearable
            class="w-full"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="ETA">
          <NDatePicker
            v-model:value="eta"
            type="date"
            clearable
            class="w-full"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="ATD">
          <NDatePicker
            v-model:value="atd"
            type="date"
            clearable
            class="w-full"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="ATA">
          <NDatePicker
            v-model:value="ata"
            type="date"
            clearable
            class="w-full"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="入仓时间">
          <NDatePicker
            v-model:value="warehouseEntryAt"
            type="datetime"
            clearable
            class="w-full"
            format="yyyy-MM-dd HH:mm:ss"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="预计送仓">
          <NDatePicker
            v-model:value="expectedDeliveryAt"
            type="date"
            clearable
            class="w-full"
            :disabled="paidLocked"
          />
        </NFormItem>
        <NFormItem label="出发港口">
          <NInput v-model:value="form.originPortCode" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="到达港口">
          <NInput v-model:value="form.destinationPortCode" :disabled="paidLocked" />
        </NFormItem>
        <NFormItem label="签收时间">
          <NDatePicker
            v-model:value="deliveredAt"
            type="datetime"
            clearable
            class="w-full"
            format="yyyy-MM-dd HH:mm:ss"
            :disabled="paidLocked"
          />
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
