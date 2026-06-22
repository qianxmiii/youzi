<script setup lang="ts">
import { NButton, NCheckbox, NEmpty, NInput, NModal, NSpin, useMessage } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { applyShipmentGroupSuggestions, previewShipmentGroupSuggestions } from '@/api/shipmentGroups'
import type { ShipmentGroupSuggestion } from '@/types/shipmentGroup'
import ShipmentGroupTypeLabel from '@/components/shipments/ShipmentGroupTypeLabel.vue'

const props = defineProps<{
  show: boolean
  shipmentIds: string[]
}>()

const emit = defineEmits<{
  close: []
  applied: []
}>()

const message = useMessage()
const loading = ref(false)
const submitting = ref(false)
const suggestions = ref<ShipmentGroupSuggestion[]>([])
const checkedKeys = ref<string[]>([])
const nameOverrides = ref<Record<string, string>>({})

const checkedSuggestions = computed(() =>
  suggestions.value.filter((s) => checkedKeys.value.includes(s.suggestionKey)),
)

watch(
  () => props.show,
  (visible) => {
    if (visible) void loadPreview()
    else {
      suggestions.value = []
      checkedKeys.value = []
      nameOverrides.value = {}
    }
  },
)

async function loadPreview() {
  if (!props.shipmentIds.length) return
  loading.value = true
  try {
    const res = await previewShipmentGroupSuggestions(props.shipmentIds)
    suggestions.value = res.suggestions
    checkedKeys.value = res.suggestions.map((s) => s.suggestionKey)
    nameOverrides.value = Object.fromEntries(
      res.suggestions.map((s) => [s.suggestionKey, s.proposedGroupName]),
    )
  } catch (e) {
    message.error(e instanceof Error ? e.message : '加载推荐失败')
    suggestions.value = []
  } finally {
    loading.value = false
  }
}

function displayName(s: ShipmentGroupSuggestion): string {
  return nameOverrides.value[s.suggestionKey] ?? s.proposedGroupName
}

async function submit() {
  const items = checkedSuggestions.value.map((s) => ({
    ...s,
    groupName: (nameOverrides.value[s.suggestionKey] || s.proposedGroupName).trim(),
  }))
  if (!items.length) {
    message.warning('请至少选择一条推荐')
    return
  }
  submitting.value = true
  try {
    const res = await applyShipmentGroupSuggestions(items)
    let text = `已创建 ${res.groupsCreated} 个分组，加入 ${res.membersAdded} 条运单`
    if (res.errors.length) text += `，失败 ${res.errors.length} 条`
    message.success(text)
    emit('applied')
    emit('close')
  } catch (e) {
    message.error(e instanceof Error ? e.message : '应用推荐失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="推荐分组"
    class="max-w-lg"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <p class="mb-3 text-sm text-zinc-400">
      根据已选 {{ shipmentIds.length }} 条运单的业务字段生成候选分组，确认后才会写入数据库。
    </p>

    <NSpin :show="loading">
      <NEmpty
        v-if="!loading && !suggestions.length"
        description="暂无可用推荐（需至少 2 票运单命中同一规则）"
        size="small"
      />
      <ul v-else class="max-h-80 space-y-3 overflow-y-auto pr-1">
        <li
          v-for="s in suggestions"
          :key="s.suggestionKey"
          class="rounded-lg border border-[var(--color-border)] p-3"
        >
          <div class="flex items-start gap-2">
            <NCheckbox
              :checked="checkedKeys.includes(s.suggestionKey)"
              @update:checked="
                (v: boolean) => {
                  if (v) checkedKeys.push(s.suggestionKey)
                  else checkedKeys = checkedKeys.filter((k) => k !== s.suggestionKey)
                }
              "
            />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-1 text-xs text-violet-300">
                <span>{{ s.ruleLabel }}</span>
                <span aria-hidden="true">·</span>
                <ShipmentGroupTypeLabel :type="s.primaryType || s.groupType" :icon-size="12" />
                <span
                  v-if="(s.groupTypes?.length ?? 0) > 1"
                  class="text-[10px] text-[var(--color-muted)]"
                >
                  +{{ (s.groupTypes?.length ?? 1) - 1 }}
                </span>
                <span aria-hidden="true">·</span>
                <span>{{ s.memberCount }} 票</span>
              </div>
              <NInput
                size="small"
                class="mt-2"
                :value="nameOverrides[s.suggestionKey]"
                placeholder="分组名称"
                @update:value="(v: string) => (nameOverrides[s.suggestionKey] = v)"
              />
              <p class="mt-2 truncate text-xs text-zinc-500" :title="s.shipmentNos.join('、')">
                {{ s.shipmentNos.join('、') }}
              </p>
            </div>
          </div>
        </li>
      </ul>
    </NSpin>

    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton @click="emit('close')">取消</NButton>
        <NButton
          type="primary"
          :loading="submitting"
          :disabled="!checkedSuggestions.length"
          @click="submit"
        >
          确认创建
        </NButton>
      </div>
    </template>
  </NModal>
</template>
