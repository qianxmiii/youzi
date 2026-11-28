<script setup lang="ts">
import { carrierVisible } from '@/composables/useCarrierPrivacy'
import CarrierVisibilityToggle from '@/components/common/CarrierVisibilityToggle.vue'
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
import { buildChannelSelectOptions } from '@/utils/channelFilterOptions'
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
const channelCodeRows = ref<CodeTableRow[]>([])
const loadingCarriers = ref(false)
const loadingChannels = ref(false)
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

const addressTypeOptions = dictOptions('address_type')

const channelSelectOptions = computed(() => {
  const options = buildChannelSelectOptions(channelCodeRows.value.filter((row) => row.isActive))
  const current = props.initial?.channelCode?.trim()
  if (current && !options.some((option) => option.value === current)) {
    options.unshift({ label: props.initial?.channelNameZh?.trim() || current, value: current })
  }
  return options
})

const carrierSelectOptions = computed(() => {
  const initial = props.initial?.carrierCode?.trim()
  const canonical = resolveCarrierFormSelectValue(initial, carrierCodeRows.value)
  const options = buildCarrierFormSelectOptionsWithCurrent(
    carrierCodeRows.value,
    canonical,
    initialCarrierNameZh.value,
  )
  return options.map((option) =>
    initial && option.value === canonical ? { ...option, value: initial } : option,
  )
})

async function loadCarrierOptions() {
  if (loadingCarriers.value) return
  loadingCarriers.value = true
  try {
    const res = await listCodeTableRows('carrier_codes', { limit: 500 })
    carrierCodeRows.value = res.items
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载承运商选项失败')
  } finally {
    loadingCarriers.value = false
  }
}

async function loadChannelOptions() {
  if (loadingChannels.value) return
  loadingChannels.value = true
  try {
    const res = await listCodeTableRows('channel_codes', { limit: 500 })
    channelCodeRows.value = res.items
  } catch (error) {
    message.error(error instanceof Error ? error.message : '加载渠道选项失败')
  } finally {
    loadingChannels.value = false
  }
}

const statusOptions = [
  { label: '已下单', value: '0' },
  { label: '提货中', value: '01' },
  { label: '已入仓', value: '1' },
  { label: '转运中', value: '2' },
  { label: '已签收', value: '3' },
  { label: '已取消', value: '4' },
]

watch(
  () => [props.show, props.mode] as const,
  ([visible, mode]) => {
    if (visible) {
      void loadDictTypes('address_type')
      void loadCarrierOptions()
      if (mode === 'edit') void loadChannelOptions()
    }
  },
)

watch(
  () => [props.show, props.mode, props.initial] as const,
  ([visible]) => {
    if (!visible) return
    if (props.mode === 'edit' && props.initial) {
      initialCarrierNameZh.value = props.initial.carrierNameZh ?? null
      form.value = {
        shipmentNo: props.initial.shipmentNo,
        customer: props.initial.customer,
        customerNo: props.initial.customerNo,
        refShipmentNo: props.initial.refShipmentNo ?? null,
        channelCode: props.initial.channelCode?.trim() || null,
        countryCode: props.initial.countryCode,
        addressType: props.initial.addressType,
        addressCode: props.initial.addressCode,
        deliveryAddress: props.initial.deliveryAddress,
        ctns: props.initial.ctns,
        zipcode: props.initial.zipcode,
        productName: props.initial.productName,
        originWarehouseCode: props.initial.originWarehouseCode,
        supplierName: props.initial.supplierName,
        carrierCode: props.initial.carrierCode?.trim() || null,
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
        statusCode: props.initial.statusCode || '0',
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
          />
        </NFormItem>
        <NFormItem label="客户订单号">
          <NInput v-model:value="form.customerNo" />
        </NFormItem>
        <NFormItem label="关联单号">
          <NInput v-model:value="form.refShipmentNo" />
        </NFormItem>
        <NFormItem label="国家">
          <NInput
            v-model:value="form.countryCode"
            placeholder="US / 美国"
          />
        </NFormItem>
        <NFormItem label="件数">
          <NInputNumber
            v-model:value="form.ctns"
            :min="0"
            class="w-full"
          />
        </NFormItem>
        <NFormItem label="品名">
          <NInput v-model:value="form.productName" />
        </NFormItem>
        <NFormItem label="渠道">
          <NSelect
            v-if="mode === 'edit'"
            v-model:value="form.channelCode"
            :options="channelSelectOptions"
            :loading="loadingChannels"
            filterable
            clearable
            placeholder="选择渠道"
          />
          <NInput v-else v-model:value="form.channelCode" />
        </NFormItem>
        <NFormItem label="承运商">
          <div class="flex w-full items-center gap-2">
            <NButton v-if="!carrierVisible" size="small" quaternary @click="carrierVisible = true">
              显示承运商
            </NButton>
            <NSelect
              v-else
              v-model:value="form.carrierCode"
              :options="carrierSelectOptions"
              :loading="loadingCarriers"
              clearable
              filterable
              placeholder="选择承运商"
            />
            <CarrierVisibilityToggle v-if="carrierVisible" />
          </div>
        </NFormItem>
        <NFormItem label="承运单号">
          <span v-if="!carrierVisible">***</span>
          <NInput
            v-else
            v-model:value="form.carrierId"
            placeholder="承运商侧主单号（同步可自动填入）"
            clearable
          />
        </NFormItem>
        <NFormItem label="转单号">
          <span v-if="!carrierVisible">***</span>
          <NInput
            v-else
            v-model:value="form.trackingNumber"
            placeholder="尾程 UPS/FedEx 等"
            clearable
          />
        </NFormItem>
        <NFormItem label="尾程快递">
          <span v-if="!carrierVisible">***</span>
          <NSelect
            v-else
            v-model:value="form.expressCode"
            :options="EXPRESS_CODE_OPTIONS"
            clearable
            placeholder="自动识别"
          />
        </NFormItem>
        <NFormItem label="地址类型">
          <NSelect
            v-model:value="form.addressType"
            clearable
            :options="addressTypeOptions"
          />
        </NFormItem>
        <NFormItem label="派送仓库/代码">
          <NInput v-model:value="form.addressCode" />
        </NFormItem>
        <NFormItem label="派送地址" class="sm:col-span-2">
          <NInput
            v-model:value="form.deliveryAddress"
            type="textarea"
            :rows="2"
          />
        </NFormItem>
        <NFormItem label="邮编">
          <NInput v-model:value="form.zipcode" />
        </NFormItem>
        <NFormItem label="收货仓">
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
        <NFormItem label="提单号">
          <NInput
            v-model:value="form.billOfLadingNo"
            placeholder="海运提单号"
            clearable
          />
        </NFormItem>
        <NFormItem label="柜号">
          <NInput
            v-model:value="form.containerNo"
            placeholder="集装箱号"
            clearable
          />
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
          <NDatePicker
            v-model:value="etd"
            type="date"
            clearable
            class="w-full"
          />
        </NFormItem>
        <NFormItem label="ETA">
          <NDatePicker
            v-model:value="eta"
            type="date"
            clearable
            class="w-full"
          />
        </NFormItem>
        <NFormItem label="ATD">
          <NDatePicker
            v-model:value="atd"
            type="date"
            clearable
            class="w-full"
          />
        </NFormItem>
        <NFormItem label="ATA">
          <NDatePicker
            v-model:value="ata"
            type="date"
            clearable
            class="w-full"
          />
        </NFormItem>
        <NFormItem label="入仓时间">
          <NDatePicker
            v-model:value="warehouseEntryAt"
            type="datetime"
            clearable
            class="w-full"
            format="yyyy-MM-dd HH:mm:ss"
          />
        </NFormItem>
        <NFormItem label="预计送仓">
          <NDatePicker
            v-model:value="expectedDeliveryAt"
            type="date"
            clearable
            class="w-full"
          />
        </NFormItem>
        <NFormItem label="出发港口">
          <NInput v-model:value="form.originPortCode" />
        </NFormItem>
        <NFormItem label="到达港口">
          <NInput v-model:value="form.destinationPortCode" />
        </NFormItem>
        <NFormItem label="签收时间">
          <NDatePicker
            v-model:value="deliveredAt"
            type="datetime"
            clearable
            class="w-full"
            format="yyyy-MM-dd HH:mm:ss"
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
