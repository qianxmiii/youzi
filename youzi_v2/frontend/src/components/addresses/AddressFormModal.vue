<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NModal, NSelect, NSpace } from 'naive-ui'
import { computed, reactive, watch } from 'vue'
import type { Address, AddressPayload, AddressType } from '@/api/addresses'

const props = defineProps<{
  show: boolean
  mode: 'create' | 'edit'
  row: Address | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: AddressPayload]
}>()

const addressTypeOptions = [
  { label: 'AMZ', value: 'AMZ' },
  { label: 'WFS', value: 'WFS' },
]

const form = reactive<AddressPayload>({
  warehouseCode: '',
  addressType: '',
  company: '',
  contact: '',
  countryCode: '',
  postalCode: '',
  state: '',
  city: '',
  addressLine1: '',
  addressLine2: '',
  addressLine3: '',
  phone: '',
  note1: '',
  note2: '',
})

const title = computed(() => (props.mode === 'create' ? '新增地址' : '编辑地址'))

watch(
  () => [props.show, props.mode, props.row] as const,
  () => {
    if (!props.show) return
    if (props.mode === 'edit' && props.row) {
      form.warehouseCode = props.row.warehouseCode || ''
      form.addressType = (props.row.addressType || '') as AddressType
      form.company = props.row.company || ''
      form.contact = props.row.contact || ''
      form.countryCode = props.row.countryCode || ''
      form.postalCode = props.row.postalCode || ''
      form.state = props.row.state || ''
      form.city = props.row.city || ''
      form.addressLine1 = props.row.addressLine1 || ''
      form.addressLine2 = props.row.addressLine2 || ''
      form.addressLine3 = props.row.addressLine3 || ''
      form.phone = props.row.phone || ''
      form.note1 = props.row.note1 || ''
      form.note2 = props.row.note2 || ''
    } else {
      form.warehouseCode = ''
      form.addressType = ''
      form.company = ''
      form.contact = ''
      form.countryCode = ''
      form.postalCode = ''
      form.state = ''
      form.city = ''
      form.addressLine1 = ''
      form.addressLine2 = ''
      form.addressLine3 = ''
      form.phone = ''
      form.note1 = ''
      form.note2 = ''
    }
  },
  { immediate: true },
)

function handleSubmit() {
  if (!form.warehouseCode.trim()) return
  emit('submit', {
    warehouseCode: form.warehouseCode.trim(),
    addressType: form.addressType,
    company: form.company.trim(),
    contact: form.contact.trim(),
    countryCode: form.countryCode.trim(),
    postalCode: form.postalCode.trim(),
    state: form.state.trim(),
    city: form.city.trim(),
    addressLine1: form.addressLine1.trim(),
    addressLine2: form.addressLine2.trim(),
    addressLine3: form.addressLine3.trim(),
    phone: form.phone.trim(),
    note1: form.note1.trim(),
    note2: form.note2.trim(),
  })
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    class="max-w-2xl"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <NForm label-placement="top" size="small">
      <div class="grid grid-cols-2 gap-3">
        <NFormItem label="仓库代码" required>
          <NInput v-model:value="form.warehouseCode" placeholder="如 DFW2" />
        </NFormItem>
        <NFormItem label="地址类型">
          <NSelect
            v-model:value="form.addressType"
            :options="addressTypeOptions"
            clearable
            placeholder="AMZ / WFS"
          />
        </NFormItem>
        <NFormItem label="收件人公司名">
          <NInput v-model:value="form.company" />
        </NFormItem>
        <NFormItem label="收件人">
          <NInput v-model:value="form.contact" />
        </NFormItem>
        <NFormItem label="国家代码">
          <NInput v-model:value="form.countryCode" placeholder="如 US" />
        </NFormItem>
        <NFormItem label="邮编">
          <NInput v-model:value="form.postalCode" />
        </NFormItem>
        <NFormItem label="州/省">
          <NInput v-model:value="form.state" placeholder="如 TX" />
        </NFormItem>
        <NFormItem label="城市">
          <NInput v-model:value="form.city" />
        </NFormItem>
        <NFormItem label="电话" class="col-span-2 sm:col-span-1">
          <NInput v-model:value="form.phone" />
        </NFormItem>
      </div>
      <NFormItem label="地址一">
        <NInput v-model:value="form.addressLine1" type="textarea" :rows="2" />
      </NFormItem>
      <NFormItem label="地址二">
        <NInput v-model:value="form.addressLine2" />
      </NFormItem>
      <NFormItem label="地址三">
        <NInput v-model:value="form.addressLine3" />
      </NFormItem>
      <div class="grid grid-cols-2 gap-3">
        <NFormItem label="备注一">
          <NInput v-model:value="form.note1" type="textarea" :rows="2" />
        </NFormItem>
        <NFormItem label="备注二">
          <NInput v-model:value="form.note2" type="textarea" :rows="2" />
        </NFormItem>
      </div>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" :disabled="!form.warehouseCode.trim()" @click="handleSubmit">
          保存
        </NButton>
      </NSpace>
    </template>
  </NModal>
</template>
