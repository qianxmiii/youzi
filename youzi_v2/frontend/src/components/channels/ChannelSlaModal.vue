<script setup lang="ts">
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSwitch,
  useMessage,
} from 'naive-ui'
import { ref, watch } from 'vue'
import {
  listChannelSlaRules,
  upsertChannelSlaRule,
  type ChannelSlaRule,
} from '@/api/shipmentSla'
import type { Channel as ChannelRow } from '@/api/channels'

const props = defineProps<{
  show: boolean
  channel: ChannelRow | null
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: []
}>()

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const rule = ref<ChannelSlaRule | null>(null)
const estimatedDays = ref<number | null>(null)
const warningDays = ref(3)
const severeOverdueDays = ref(7)
const enabled = ref(true)
const note = ref('')

async function loadRule() {
  if (!props.channel) return
  loading.value = true
  try {
    const res = await listChannelSlaRules(props.channel.code)
    const defaultRule =
      res.items.find((r) => !r.carrierCode && r.startField === 'ATD') || res.items[0] || null
    rule.value = defaultRule
    estimatedDays.value = defaultRule?.estimatedDays ?? null
    warningDays.value = defaultRule?.warningDays ?? 3
    severeOverdueDays.value = defaultRule?.severeOverdueDays ?? 7
    enabled.value = defaultRule?.enabled ?? true
    note.value = defaultRule?.note ?? ''
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.show,
  (open) => {
    if (open) void loadRule()
  },
)

async function save() {
  if (!props.channel) return
  if (estimatedDays.value == null || estimatedDays.value <= 0) {
    message.warning('请填写预估天数')
    return
  }
  saving.value = true
  try {
    await upsertChannelSlaRule(props.channel.code, {
      estimatedDays: estimatedDays.value,
      warningDays: warningDays.value,
      severeOverdueDays: severeOverdueDays.value,
      enabled: enabled.value,
      note: note.value,
      startField: 'ATD',
      carrierCode: '',
    })
    message.success('运输时效规则已保存')
    emit('saved')
    emit('update:show', false)
  } catch (e) {
    message.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="channel ? `运输时效 · ${channel.nameZh || channel.code}` : '运输时效'"
    class="max-w-lg"
    @update:show="emit('update:show', $event)"
  >
    <NForm label-placement="left" label-width="120" :disabled="loading">
      <NFormItem label="起算节点">
        <NInput value="ATD（实际离港）" disabled />
      </NFormItem>
      <NFormItem label="预估天数" required>
        <NInputNumber v-model:value="estimatedDays" :min="1" class="w-full" placeholder="如 35" />
      </NFormItem>
      <NFormItem label="提前提醒(天)">
        <NInputNumber v-model:value="warningDays" :min="0" class="w-full" />
      </NFormItem>
      <NFormItem label="严重超时(天)">
        <NInputNumber v-model:value="severeOverdueDays" :min="0" class="w-full" />
      </NFormItem>
      <NFormItem label="启用">
        <NSwitch v-model:value="enabled" />
      </NFormItem>
      <NFormItem label="备注">
        <NInput v-model:value="note" type="textarea" :rows="2" placeholder="如：美西卡派常规时效" />
      </NFormItem>
    </NForm>
    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" :loading="saving" @click="save">保存</NButton>
      </div>
    </template>
  </NModal>
</template>
