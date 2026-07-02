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
  NSwitch,
} from 'naive-ui'
import { computed, reactive, watch } from 'vue'
import type { CodeTablePayload, CodeTableRow } from '@/types/codeTable'

const props = defineProps<{
  show: boolean
  mode: 'create' | 'edit'
  hasPortType: boolean
  hasChannelFields?: boolean
  hasCarrierFields?: boolean
  initial: CodeTableRow | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: CodeTablePayload]
}>()

const portTypeOptions = [
  { label: '出发/到达', value: 'both' },
  { label: '出发港', value: 'origin' },
  { label: '到达港', value: 'destination' },
]

const categoryOptions = ['快船', '普船', '卡航', '铁路', '空运'].map((c) => ({
  label: c,
  value: c,
}))

const form = reactive<CodeTablePayload>({
  code: '',
  nameZh: '',
  nameEn: '',
  sortOrder: 0,
  isActive: true,
  portType: 'both',
  country: '',
  category: '',
  note: '',
  carrierId: '',
})

const title = computed(() => (props.mode === 'create' ? '新增码表项' : '修改码表项'))

watch(
  () => [props.show, props.mode, props.initial] as const,
  () => {
    if (!props.show) return
    if (props.mode === 'edit' && props.initial) {
      form.code = props.initial.code
      form.nameZh = props.initial.nameZh
      form.nameEn = props.initial.nameEn
      form.sortOrder = props.initial.sortOrder
      form.isActive = props.initial.isActive
      form.portType = props.initial.portType || 'both'
      form.country = props.initial.country || ''
      form.category = props.initial.category || ''
      form.note = props.initial.note || ''
      form.carrierId = props.initial.carrierId || ''
    } else {
      form.code = ''
      form.nameZh = ''
      form.nameEn = ''
      form.sortOrder = 0
      form.isActive = true
      form.portType = 'both'
      form.country = ''
      form.category = ''
      form.note = ''
      form.carrierId = ''
    }
  },
  { immediate: true },
)

function handleSubmit() {
  emit('submit', { ...form })
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    class="w-full max-w-md"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <NForm label-placement="left" label-width="88" size="small">
      <NFormItem label="编码" required>
        <NInput v-model:value="form.code" :disabled="mode === 'edit'" placeholder="唯一编码" />
      </NFormItem>
      <NFormItem label="中文名">
        <NInput v-model:value="form.nameZh" />
      </NFormItem>
      <NFormItem label="英文名">
        <NInput v-model:value="form.nameEn" />
      </NFormItem>
      <NFormItem v-if="hasPortType" label="港口类型">
        <NSelect v-model:value="form.portType" :options="portTypeOptions" />
      </NFormItem>
      <NFormItem v-if="hasChannelFields" label="国家/地区">
        <NInput v-model:value="form.country" placeholder="如 美国" />
      </NFormItem>
      <NFormItem v-if="hasChannelFields" label="大类">
        <NSelect
          v-model:value="form.category"
          :options="categoryOptions"
          clearable
          placeholder="快船 / 普船 / …"
        />
      </NFormItem>
      <NFormItem v-if="hasChannelFields" label="备注">
        <NInput v-model:value="form.note" type="textarea" :rows="2" />
      </NFormItem>
      <NFormItem v-if="hasCarrierFields" label="承运商ID">
        <NInput
          v-model:value="form.carrierId"
          placeholder="DPS carrierId，用于反查编码（写入运单 carrier_code）"
        />
      </NFormItem>
      <NFormItem label="排序">
        <NInputNumber v-model:value="form.sortOrder" :min="0" class="w-full" />
      </NFormItem>
      <NFormItem label="启用">
        <NSwitch v-model:value="form.isActive" />
      </NFormItem>
    </NForm>
    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" @click="handleSubmit">保存</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
