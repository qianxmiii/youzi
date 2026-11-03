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
const estimatedDaysMin = ref<number | null>(null)
const estimatedDaysMax = ref<number | null>(null)
const postArrivalDaysMin = ref<number | null>(7)
const postArrivalDaysMax = ref<number | null>(15)
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
    estimatedDaysMin.value = defaultRule?.estimatedDaysMin ?? defaultRule?.estimatedDays ?? null
    estimatedDaysMax.value = defaultRule?.estimatedDaysMax ?? defaultRule?.estimatedDays ?? null
    postArrivalDaysMin.value = defaultRule?.postArrivalDaysMin ?? 7
    postArrivalDaysMax.value = defaultRule?.postArrivalDaysMax ?? 15
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
  if (estimatedDaysMin.value == null || estimatedDaysMax.value == null || estimatedDaysMin.value < 1 || estimatedDaysMax.value < estimatedDaysMin.value) {
    message.warning('请填写有效时效区间：最短天数不能大于最长天数')
    return
  }
  if (postArrivalDaysMin.value == null || postArrivalDaysMax.value == null || postArrivalDaysMin.value < 0 || postArrivalDaysMax.value < postArrivalDaysMin.value) {
    message.warning('请填写有效的到港后送仓区间'); return
  }
  saving.value = true
  try {
    await upsertChannelSlaRule(props.channel.code, {
      estimatedDaysMin: estimatedDaysMin.value,
      estimatedDaysMax: estimatedDaysMax.value,
      postArrivalDaysMin: postArrivalDaysMin.value,
      postArrivalDaysMax: postArrivalDaysMax.value,
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
    <NForm label-placement="left" label-width="120" :disabled="loading || saving">
      <NFormItem label="起算节点">
        <NInput value="ATD（实际离港）" disabled />
      </NFormItem>
      <NFormItem label="离港至送仓(天)" required>
        <div class="grid w-full grid-cols-1 items-center gap-2 sm:grid-cols-[1fr_auto_1fr]">
          <NInputNumber v-model:value="estimatedDaysMin" :min="1" :precision="0" class="w-full" placeholder="最短，如25" aria-label="最短时效天数" />
          <span class="text-center">至</span>
          <NInputNumber v-model:value="estimatedDaysMax" :min="estimatedDaysMin ?? 1" :precision="0" class="w-full" placeholder="最长，如35" aria-label="最长时效天数" />
        </div>
      </NFormItem>
      <NFormItem label="到港后送仓(天)" required>
        <div class="grid w-full grid-cols-1 items-center gap-2 sm:grid-cols-[1fr_auto_1fr]">
          <NInputNumber v-model:value="postArrivalDaysMin" :min="0" :precision="0" class="w-full" placeholder="默认7" aria-label="到港后最短送仓天数" />
          <span class="text-center">至</span>
          <NInputNumber v-model:value="postArrivalDaysMax" :min="postArrivalDaysMin ?? 0" :precision="0" class="w-full" placeholder="默认15" aria-label="到港后最长送仓天数" />
        </div>
      </NFormItem>
      <p class="mb-4 text-xs text-[var(--color-fg-secondary)]">DW参考离港全程与到港后送仓两种估算，取较晚范围；实际到港优先于ETA。Amazon仍只取最晚预计送仓日所在的一周。异常预警只使用全程时效上限。</p>
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
