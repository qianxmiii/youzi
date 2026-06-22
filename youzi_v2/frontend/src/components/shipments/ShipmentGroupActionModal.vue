<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NModal, NSelect } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import { listShipmentGroups } from '@/api/shipmentGroups'
import type { ShipmentGroupBatchMode, ShipmentGroupFilterOption } from '@/types/shipmentGroup'
import {
  shipmentGroupTypeSelectOptions,
  type ShipmentGroupType,
} from '@/constants/shipmentGroupTypes'
import {
  renderShipmentGroupTypeSelectLabel,
} from '@/utils/shipmentGroupTypeSelectRender'

const props = defineProps<{
  show: boolean
  mode: ShipmentGroupBatchMode
  count: number
  /** 移出/标记末批时可选的分组（来自已选运单） */
  memberGroupOptions?: ShipmentGroupFilterOption[]
  /** 新建分组时预填客户 */
  defaultCustomer?: string | null
}>()

const emit = defineEmits<{
  close: []
  confirmCreate: [
    groupName: string,
    customer: string | undefined,
    types: { primaryType: ShipmentGroupType; groupTypes: ShipmentGroupType[] },
  ]
  confirmGroupId: [groupId: string, batchNo?: string]
}>()

const groupName = ref('')
const customer = ref('')
const groupTypes = ref<ShipmentGroupType[]>(['MANUAL'])
const primaryType = ref<ShipmentGroupType>('MANUAL')
const groupTypeOptions = shipmentGroupTypeSelectOptions()
const groupId = ref<string | null>(null)
const batchNo = ref('')
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
    case 'lastBatch':
      return '标记最后一批'
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
    case 'lastBatch':
      return `将已选 ${props.count} 条运单在所选分组中标记为最后一批（LAST_BATCH）。`
    default:
      return ''
  }
})

const groupSelectOptions = computed(() => {
  if (props.mode === 'remove' || props.mode === 'lastBatch') {
    return (props.memberGroupOptions ?? []).map((g) => ({
      label: formatGroupOptionLabel(g),
      value: g.id,
    }))
  }
  return allGroupOptions.value
})

function formatGroupOptionLabel(g: ShipmentGroupFilterOption): string {
  const name = g.groupName?.trim()
  if (name) return `${name}（${g.groupNo}）`
  return g.groupNo
}

const primaryTypeOptions = computed(() =>
  groupTypeOptions.filter((o) => groupTypes.value.includes(o.value as ShipmentGroupType)),
)

watch(groupTypes, (types) => {
  if (!types.length) {
    groupTypes.value = ['MANUAL']
    primaryType.value = 'MANUAL'
    return
  }
  if (!types.includes(primaryType.value)) {
    primaryType.value = types[0]
  }
})

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
    groupTypes.value = ['MANUAL']
    primaryType.value = 'MANUAL'
    groupId.value = null
    batchNo.value = ''
    if (props.mode === 'add') void loadAllGroups()
    else if (props.mode === 'remove' || props.mode === 'lastBatch') {
      const opts = props.memberGroupOptions ?? []
      groupId.value = opts.length === 1 ? opts[0].id : null
    }
  },
)

function submit() {
  if (props.mode === 'create') {
    emit('confirmCreate', groupName.value.trim(), customer.value.trim() || undefined, {
      primaryType: primaryType.value,
      groupTypes: [...groupTypes.value],
    })
    return
  }
  if (!groupId.value) return
  if (props.mode === 'lastBatch') {
    emit('confirmGroupId', groupId.value, batchNo.value.trim() || undefined)
  } else {
    emit('confirmGroupId', groupId.value)
  }
}

const canSubmit = computed(() => {
  if (props.mode === 'create') return groupTypes.value.length > 0 && !!primaryType.value
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
        <NFormItem label="业务类型" required>
          <NSelect
            v-model:value="groupTypes"
            :options="groupTypeOptions"
            :render-label="renderShipmentGroupTypeSelectLabel"
            consistent-menu-width
            class="w-full"
            multiple
            placeholder="至少选择一项"
          />
        </NFormItem>
        <NFormItem label="主类型" required>
          <NSelect
            v-model:value="primaryType"
            :options="primaryTypeOptions"
            :render-label="renderShipmentGroupTypeSelectLabel"
            consistent-menu-width
            class="w-full"
            placeholder="用于列表图标与默认展示"
          />
        </NFormItem>
        <NFormItem label="分组名称">
          <NInput v-model:value="groupName" placeholder="可选，留空则仅显示组号" />
        </NFormItem>
        <NFormItem label="客户">
          <NInput v-model:value="customer" placeholder="可选" />
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
        <NFormItem v-if="mode === 'lastBatch'" label="批次号">
          <NInput v-model:value="batchNo" placeholder="可选" />
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
