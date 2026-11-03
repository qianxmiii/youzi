<script setup lang="ts">
import { NButton, NCheckbox, NForm, NFormItem, NInput, NModal, NSelect, NSpace } from 'naive-ui'
import { computed, reactive, watch } from 'vue'
import type { CustomerAddress, CustomerAddressPayload } from '@/api/customerAddresses'

const props = defineProps<{
  show: boolean
  saving: boolean
  row: CustomerAddress | null
  customerOptions: Array<{ label: string; value: string }>
  presetCustomer?: string
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  submit: [payload: CustomerAddressPayload]
}>()

const kindOptions = [
  { label: '海外仓', value: 'WAREHOUSE' },
  { label: '商业', value: 'COMMERCIAL' },
  { label: '住宅', value: 'RESIDENTIAL' },
]

const form = reactive({
  customerName: '',
  label: '',
  consigneeName: '',
  company: '',
  phone: '',
  email: '',
  country: '',
  address: '',
  postcode: '',
  addressKind: 'COMMERCIAL',
  isRemote: false,
  note: '',
})

const title = computed(() => (props.row ? '修改地址' : '新增地址'))

watch(
  () => [props.show, props.row] as const,
  ([show]) => {
    if (!show) return
    const row = props.row
    form.customerName = row?.customerName || props.presetCustomer || ''
    form.label = row?.label || ''
    form.consigneeName = row?.consigneeName || ''
    form.company = row?.company || ''
    form.phone = row?.phone || ''
    form.email = row?.email || ''
    form.country = row?.country || ''
    form.address = row?.address || ''
    form.postcode = row?.postcode || ''
    form.addressKind = row?.addressKind || 'COMMERCIAL'
    form.isRemote = row?.isRemote ?? false
    form.note = row?.note || ''
  },
)

function close() {
  emit('update:show', false)
}

function submit() {
  emit('submit', {
    customerName: form.customerName.trim(),
    label: form.label.trim(),
    consigneeName: form.consigneeName.trim(),
    company: form.company.trim(),
    phone: form.phone.trim(),
    email: form.email.trim(),
    country: form.country.trim(),
    address: form.address.trim(),
    postcode: form.postcode.trim(),
    addressKind: form.addressKind,
    isRemote: form.isRemote,
    note: form.note.trim(),
  })
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    style="width: 640px"
    @update:show="emit('update:show', $event)"
  >
    <NForm label-placement="left" label-width="108">
      <NFormItem label="客户名" required>
        <NSelect
          v-model:value="form.customerName"
          filterable
          :options="customerOptions"
          placeholder="从客户管理中选择"
        />
      </NFormItem>
      <NFormItem label="地址简称">
        <NInput v-model:value="form.label" placeholder="可空，例如洛杉矶私人仓" />
      </NFormItem>
      <NFormItem label="收货人名">
        <NInput v-model:value="form.consigneeName" />
      </NFormItem>
      <NFormItem label="收货人公司名">
        <NInput v-model:value="form.company" />
      </NFormItem>
      <NFormItem label="收货人电话">
        <NInput v-model:value="form.phone" />
      </NFormItem>
      <NFormItem label="收货人邮箱">
        <NInput v-model:value="form.email" />
      </NFormItem>
      <NFormItem label="国家" required>
        <NInput v-model:value="form.country" placeholder="如 US" />
      </NFormItem>
      <NFormItem label="收件人地址" required>
        <NInput v-model:value="form.address" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
      </NFormItem>
      <NFormItem label="收件人邮编">
        <NInput v-model:value="form.postcode" />
      </NFormItem>
      <NFormItem label="地址类型" required>
        <NSelect v-model:value="form.addressKind" :options="kindOptions" />
      </NFormItem>
      <NFormItem label="偏远">
        <NCheckbox v-model:checked="form.isRemote">偏远</NCheckbox>
      </NFormItem>
      <NFormItem label="备注">
        <NInput v-model:value="form.note" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="close">取消</NButton>
        <NButton type="primary" :loading="saving" @click="submit">保存</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
