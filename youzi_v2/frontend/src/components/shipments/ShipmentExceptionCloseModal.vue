<script setup lang="ts">
import { NButton, NDatePicker, NForm, NFormItem, NInput, NModal } from 'naive-ui'
import { ref, watch } from 'vue'
import { formatTimestampForApi, nowTimestamp } from '@/utils/formatDateTime'

const props = defineProps<{
  show: boolean
  count: number
}>()

const emit = defineEmits<{
  close: []
  confirm: [closedTime: string | undefined, note: string | undefined]
}>()

const closedAt = ref<number | null>(null)
const note = ref('')

watch(
  () => props.show,
  (visible) => {
    if (visible) {
      closedAt.value = nowTimestamp()
      note.value = ''
    }
  },
)

function submit() {
  const closedTime =
    closedAt.value != null ? formatTimestampForApi(closedAt.value) : undefined
  emit('confirm', closedTime, note.value.trim() || undefined)
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="解除异常"
    class="max-w-md"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <p class="mb-3 text-sm text-zinc-400">将为已选 {{ count }} 条运单结束当前异常并记录结束时间。</p>
    <NForm label-placement="left" label-width="88">
      <NFormItem label="异常结束时间" required>
        <NDatePicker
          v-model:value="closedAt"
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
        <NButton type="primary" :disabled="closedAt == null" @click="submit">确认解除</NButton>
      </div>
    </template>
  </NModal>
</template>
