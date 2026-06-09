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
import { ref, watch } from 'vue'
import { useDictLabels } from '@/composables/useDictLabels'
import type { ShipmentPayload } from '@/types/shipment'
import { EXPRESS_CODE_BATCH_OPTIONS } from '@/constants/expressCodes'
import { formatDateOnlyForApi } from '@/utils/formatDateTime'

const props = defineProps<{
  show: boolean
  count: number
  statusOptions: { label: string; value: string }[]
  channelOptions: { label: string; value: string }[]
  carrierOptions: { label: string; value: string }[]
  countryOptions: { label: string; value: string }[]
}>()

const emit = defineEmits<{
  close: []
  submit: [updates: Partial<ShipmentPayload>]
}>()

const message = useMessage()
const { loadDictTypes, dictOptions } = useDictLabels()
const addressTypeOptions = dictOptions('address_type')

const statusCode = ref<string | null>(null)
const customer = ref('')
const customerNo = ref('')
const channelCode = ref<string | null>(null)
const countryCode = ref<string | null>(null)
const carrierCode = ref<string | null>(null)
const expressCodePick = ref<string | null>('__UNCHANGED__')
const addressType = ref<string | null>(null)
const addressCode = ref('')
const ctns = ref<number | null>(null)
const productName = ref('')
const supplierName = ref('')
const vesselVoyage = ref('')
const etd = ref<number | null>(null)
const eta = ref<number | null>(null)
const atd = ref<number | null>(null)
const ata = ref<number | null>(null)
const originPortCode = ref('')
const destinationPortCode = ref('')

watch(
  () => props.show,
  (visible) => {
    if (!visible) return
    void loadDictTypes('address_type')
    statusCode.value = null
    customer.value = ''
    customerNo.value = ''
    channelCode.value = null
    countryCode.value = null
    carrierCode.value = null
    expressCodePick.value = '__UNCHANGED__'
    addressType.value = null
    addressCode.value = ''
    ctns.value = null
    productName.value = ''
    supplierName.value = ''
    vesselVoyage.value = ''
    etd.value = null
    eta.value = null
    atd.value = null
    ata.value = null
    originPortCode.value = ''
    destinationPortCode.value = ''
  },
)

function applyDateField(
  updates: Partial<ShipmentPayload>,
  key: 'etd' | 'eta' | 'atd' | 'ata',
  ts: number | null,
) {
  if (ts != null) updates[key] = formatDateOnlyForApi(ts)
}

function buildUpdates(): Partial<ShipmentPayload> | null {
  const updates: Partial<ShipmentPayload> = {}
  if (statusCode.value) updates.statusCode = statusCode.value
  if (customer.value.trim()) updates.customer = customer.value.trim()
  if (customerNo.value.trim()) updates.customerNo = customerNo.value.trim()
  if (channelCode.value) updates.channelCode = channelCode.value
  if (countryCode.value) updates.countryCode = countryCode.value
  if (carrierCode.value) updates.carrierCode = carrierCode.value
  if (expressCodePick.value !== '__UNCHANGED__') {
    updates.expressCode = expressCodePick.value
  }
  if (addressType.value) updates.addressType = addressType.value
  if (addressCode.value.trim()) updates.addressCode = addressCode.value.trim()
  if (ctns.value != null && !Number.isNaN(ctns.value)) updates.ctns = ctns.value
  if (productName.value.trim()) updates.productName = productName.value.trim()
  if (supplierName.value.trim()) updates.supplierName = supplierName.value.trim()
  if (vesselVoyage.value.trim()) updates.vesselVoyage = vesselVoyage.value.trim()
  applyDateField(updates, 'etd', etd.value)
  applyDateField(updates, 'eta', eta.value)
  applyDateField(updates, 'atd', atd.value)
  applyDateField(updates, 'ata', ata.value)
  if (originPortCode.value.trim()) updates.originPortCode = originPortCode.value.trim()
  if (destinationPortCode.value.trim()) {
    updates.destinationPortCode = destinationPortCode.value.trim()
  }
  if (Object.keys(updates).length === 0) return null
  return updates
}

function handleSubmit() {
  const updates = buildUpdates()
  if (!updates) {
    message.warning('请至少填写或选择一项要批量修改的内容')
    return
  }
  emit('submit', updates)
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="`批量修改（${count} 条）`"
    class="max-w-2xl"
    :mask-closable="false"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <p class="mb-3 text-xs leading-relaxed text-zinc-500">
      仅更新下方已填写的字段，留空项保持各运单原值不变。运单号不可批量修改。
    </p>
    <NForm label-placement="top" size="small">
      <div class="grid grid-cols-1 gap-x-3 sm:grid-cols-2">
        <NFormItem label="状态">
          <NSelect
            v-model:value="statusCode"
            :options="statusOptions"
            clearable
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="客户">
          <NInput v-model:value="customer" clearable placeholder="不修改" />
        </NFormItem>
        <NFormItem label="客户订单号">
          <NInput v-model:value="customerNo" clearable placeholder="不修改" />
        </NFormItem>
        <NFormItem label="渠道">
          <NSelect
            v-model:value="channelCode"
            :options="channelOptions"
            filterable
            tag
            clearable
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="国家">
          <NSelect
            v-model:value="countryCode"
            :options="countryOptions"
            filterable
            tag
            clearable
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="承运商">
          <NSelect
            v-model:value="carrierCode"
            :options="carrierOptions"
            filterable
            tag
            clearable
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="尾程快递">
          <NSelect
            v-model:value="expressCodePick"
            :options="EXPRESS_CODE_BATCH_OPTIONS"
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="地址类型">
          <NSelect
            v-model:value="addressType"
            :options="addressTypeOptions"
            clearable
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="派送仓库/代码">
          <NInput v-model:value="addressCode" clearable placeholder="不修改" />
        </NFormItem>
        <NFormItem label="件数">
          <NInputNumber v-model:value="ctns" :min="0" clearable class="w-full" placeholder="不修改" />
        </NFormItem>
        <NFormItem label="品名">
          <NInput v-model:value="productName" clearable placeholder="不修改" />
        </NFormItem>
        <NFormItem label="供应商">
          <NInput v-model:value="supplierName" clearable placeholder="不修改" />
        </NFormItem>
      </div>

      <p class="mb-2 mt-4 text-xs font-medium text-zinc-400">海运 / 船期</p>
      <div class="grid grid-cols-1 gap-x-3 sm:grid-cols-2">
        <NFormItem label="船名航次" class="sm:col-span-2">
          <NInput
            v-model:value="vesselVoyage"
            clearable
            placeholder="不修改，如 CSCL BOHAI SEA/076E"
          />
        </NFormItem>
        <NFormItem label="ETD">
          <NDatePicker
            v-model:value="etd"
            type="date"
            clearable
            class="w-full"
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="ETA">
          <NDatePicker
            v-model:value="eta"
            type="date"
            clearable
            class="w-full"
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="ATD">
          <NDatePicker
            v-model:value="atd"
            type="date"
            clearable
            class="w-full"
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="ATA">
          <NDatePicker
            v-model:value="ata"
            type="date"
            clearable
            class="w-full"
            placeholder="不修改"
          />
        </NFormItem>
        <NFormItem label="出发港口">
          <NInput v-model:value="originPortCode" clearable placeholder="不修改" />
        </NFormItem>
        <NFormItem label="到达港口">
          <NInput v-model:value="destinationPortCode" clearable placeholder="不修改" />
        </NFormItem>
      </div>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" @click="handleSubmit">应用到所选</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
