<script setup lang="ts">
import { NButton, NCheckbox, NForm, NFormItem, NInput, NInputNumber, NModal, NSelect } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { listShipmentGroups } from '@/api/shipmentGroups'
import {
  SHIPMENT_GROUP_RULE_OPTIONS,
  defaultRuleDraft,
  shipmentGroupRuleHasDeadlineFields,
  shipmentGroupRuleHasEtaWarningFields,
  type ShipmentGroupRuleType,
} from '@/constants/shipmentGroupRules'
import { formatGroupNoDisplay } from '@/utils/shipmentGroup'
import type {
  ShipmentGroupBatchMode,
  ShipmentGroupFilterOption,
  ShipmentGroupRuleInput,
} from '@/types/shipmentGroup'

const props = defineProps<{
  show: boolean
  mode: ShipmentGroupBatchMode
  count: number
  memberGroupOptions?: ShipmentGroupFilterOption[]
  defaultCustomer?: string | null
}>()

const emit = defineEmits<{
  close: []
  confirmCreate: [
    groupName: string,
    customer: string | undefined,
    rules: ShipmentGroupRuleInput[],
  ]
  confirmGroupId: [groupId: string]
}>()

const groupName = ref('')
const customer = ref('')
const enabledRuleTypes = ref<ShipmentGroupRuleType[]>([])
const ruleDrafts = ref<Record<string, ShipmentGroupRuleInput>>({})
const groupId = ref<string | null>(null)
const loadingGroups = ref(false)
const allGroupOptions = ref<{ label: string; value: string }[]>([])

const title = computed(() => {
  switch (props.mode) {
    case 'create':
      return '新建分组'
    case 'add':
      return '加入已有分组'
    case 'remove':
      return '移出分组'
    default:
      return '分组操作'
  }
})

const hint = computed(() => {
  switch (props.mode) {
    case 'create':
      return `将为已选 ${props.count} 条运单新建分组并加入为成员。`
    case 'add':
      return `将已选 ${props.count} 条运单加入所选分组。`
    case 'remove':
      return `将已选 ${props.count} 条运单从所选分组移出。`
    default:
      return ''
  }
})

const groupSelectOptions = computed(() => {
  if (props.mode === 'remove') {
    return (props.memberGroupOptions ?? []).map((g) => ({
      label: formatGroupOptionLabel(g),
      value: g.id,
    }))
  }
  return allGroupOptions.value
})

function formatGroupOptionLabel(g: ShipmentGroupFilterOption): string {
  const name = g.groupName?.trim()
  const no = formatGroupNoDisplay(g.groupNo)
  if (name) return `${name}（${no}）`
  return no
}

function toggleRule(ruleType: ShipmentGroupRuleType, checked: boolean) {
  if (checked) {
    if (!enabledRuleTypes.value.includes(ruleType)) {
      enabledRuleTypes.value.push(ruleType)
    }
    if (!ruleDrafts.value[ruleType]) {
      ruleDrafts.value[ruleType] = defaultRuleDraft(ruleType)
    }
  } else {
    enabledRuleTypes.value = enabledRuleTypes.value.filter((t) => t !== ruleType)
  }
}

async function loadAllGroups() {
  loadingGroups.value = true
  try {
    const res = await listShipmentGroups({ limit: 200, offset: 0 })
    allGroupOptions.value = res.items.map((g) => ({
      label: formatGroupOptionLabel({
        id: g.id,
        groupNo: g.groupNo,
        groupName: g.groupName,
      }),
      value: g.id,
    }))
  } catch {
    allGroupOptions.value = []
  } finally {
    loadingGroups.value = false
  }
}

watch(
  () => props.show,
  (visible) => {
    if (!visible) return
    groupName.value = ''
    customer.value = props.defaultCustomer?.trim() ?? ''
    enabledRuleTypes.value = []
    ruleDrafts.value = {}
    groupId.value = null
    if (props.mode === 'add') void loadAllGroups()
    else if (props.mode === 'remove') {
      const opts = props.memberGroupOptions ?? []
      groupId.value = opts.length === 1 ? opts[0].id : null
    }
  },
)

function buildRules(): ShipmentGroupRuleInput[] {
  return enabledRuleTypes.value.map((ruleType) => ({
    ...defaultRuleDraft(ruleType),
    ...ruleDrafts.value[ruleType],
    ruleType,
    enabled: true,
  }))
}

function submit() {
  if (props.mode === 'create') {
    emit('confirmCreate', groupName.value.trim(), customer.value.trim() || undefined, buildRules())
    return
  }
  if (!groupId.value) return
  emit('confirmGroupId', groupId.value)
}

const canSubmit = computed(() => {
  if (props.mode === 'create') return true
  return !!groupId.value
})
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    class="max-w-md"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <p class="mb-3 text-sm text-zinc-400">{{ hint }}</p>
    <NForm label-placement="left" label-width="88">
      <template v-if="mode === 'create'">
        <NFormItem label="分组名称">
          <NInput v-model:value="groupName" placeholder="可选，留空则仅显示组号" />
        </NFormItem>
        <NFormItem label="客户">
          <NInput v-model:value="customer" placeholder="可选" />
        </NFormItem>
        <NFormItem label="启用规则">
          <div class="w-full space-y-3">
            <div
              v-for="opt in SHIPMENT_GROUP_RULE_OPTIONS"
              :key="opt.value"
              class="rounded-lg border border-[var(--color-border)] p-3"
            >
              <NCheckbox
                :checked="enabledRuleTypes.includes(opt.value)"
                @update:checked="(v: boolean) => toggleRule(opt.value, v)"
              >
                {{ opt.label }}
              </NCheckbox>
              <p class="mt-1 text-xs text-[var(--color-muted)]">{{ opt.description }}</p>
              <div
                v-if="enabledRuleTypes.includes(opt.value) && shipmentGroupRuleHasDeadlineFields(opt.value)"
                class="mt-2 grid grid-cols-2 gap-2"
              >
                <NInputNumber
                  v-model:value="ruleDrafts[opt.value].thresholdDays"
                  :min="1"
                  :show-button="false"
                  size="small"
                  placeholder="期限天数"
                />
                <NInputNumber
                  v-model:value="ruleDrafts[opt.value].warningDays"
                  :min="0"
                  :show-button="false"
                  size="small"
                  placeholder="提前提醒"
                />
              </div>
              <div
                v-else-if="enabledRuleTypes.includes(opt.value) && shipmentGroupRuleHasEtaWarningFields(opt.value)"
                class="mt-2"
              >
                <NInputNumber
                  v-model:value="ruleDrafts[opt.value].warningDays"
                  :min="1"
                  :show-button="false"
                  size="small"
                  placeholder="到港前提醒天数"
                  class="w-full"
                />
              </div>
            </div>
          </div>
        </NFormItem>
      </template>
      <template v-else>
        <NFormItem label="选择分组" required>
          <NSelect
            v-model:value="groupId"
            :options="groupSelectOptions"
            :loading="loadingGroups"
            placeholder="选择分组"
            filterable
            clearable
          />
        </NFormItem>
      </template>
    </NForm>
    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" :disabled="!canSubmit" @click="submit">确认</NButton>
      </div>
    </template>
  </NModal>
</template>
