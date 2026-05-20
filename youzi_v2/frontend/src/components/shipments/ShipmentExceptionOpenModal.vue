<script setup lang="ts">
import { NButton, NDatePicker, NForm, NFormItem, NInput, NModal, NSelect } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import type { ShipmentExceptionType } from '@/types/shipment'
import { formatTimestampForApi, nowTimestamp } from '@/utils/formatDateTime'

const props = defineProps<{
  show: boolean
  count: number
  exceptionTypes: ShipmentExceptionType[]
}>()

const emit = defineEmits<{
  close: []
  confirm: [exceptionCode: string, openedTime: string | undefined, note: string | undefined]
}>()

const exceptionCode = ref<string | null>(null)
const openedAt = ref<number | null>(null)
const note = ref('')

const options = computed(() =>
  props.exceptionTypes.map((t) => ({ label: t.nameZh, value: t.code })),
)

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      exceptionCode.value = props.exceptionTypes[0]?.code ?? null
      openedAt.value = nowTimestamp()
      note.value = ''
    }
  },
)

function submit() {
  if (!exceptionCode.value || openedAt.value == null) return
  const openedTime = formatTimestampForApi(openedAt.value)
  emit('confirm', exceptionCode.value, openedTime, note.value.trim() || undefined)
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="标记异常"
    class="max-w-md"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <p class="mb-3 text-sm text-zinc-400">将为已选 {{ count }} 条运单开启异常并记录开始时间。</p>
    <NForm label-placement="left" label-width="88">
      <NFormItem label="异常类型" required>
        <NSelect v-model:value="exceptionCode" :options="options" placeholder="选择类型" />
      </NFormItem>
      <NFormItem label="异常开始时间" required>
        <NDatePicker
          v-model:value="openedAt"
          type="datetime"
          clearable
          class="w-full"
          format="yyyy-MM-dd HH:mm:ss"
        />
      </NFormItem>
      <NFormItem label="备注">
        <NInput v-model:value="note" type="textarea" placeholder="可选" :rows="2" />
      </NFormItem>
    </NForm>
    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" :disabled="!exceptionCode || openedAt == null" @click="submit">
          确认标记
        </NButton>
      </div>
    </template>
  </NModal>
</template>
