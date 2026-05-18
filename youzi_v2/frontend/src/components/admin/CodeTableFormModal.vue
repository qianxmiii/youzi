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

const form = reactive<CodeTablePayload>({
  code: '',
  nameZh: '',
  nameEn: '',
  sortOrder: 0,
  isActive: true,
  portType: 'both',
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
    } else {
      form.code = ''
      form.nameZh = ''
      form.nameEn = ''
      form.sortOrder = 0
      form.isActive = true
      form.portType = 'both'
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
