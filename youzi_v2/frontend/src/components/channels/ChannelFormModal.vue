<script setup lang="ts">
import { NButton, NForm, NFormItem, NInput, NInputNumber, NModal, NSelect, NSwitch } from 'naive-ui'
import { computed, ref, watch } from 'vue'
import type { Channel, ChannelPayload } from '@/api/channels'

const props = defineProps<{
  show: boolean
  mode: 'create' | 'edit' | 'copy'
  row: Channel | null
  categories: string[]
  countries: string[]
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: ChannelPayload]
}>()

const code = ref('')
const nameZh = ref('')
const nameEn = ref('')
const country = ref<string | null>(null)
const category = ref<string | null>(null)
const note = ref('')
const sortOrder = ref(0)
const isActive = ref(true)

const countryOptions = computed(() =>
  props.countries.map((c) => ({ label: c, value: c })),
)
const categoryOptions = computed(() =>
  props.categories.map((c) => ({ label: c, value: c })),
)

watch(
  () => [props.show, props.mode, props.row] as const,
  ([visible]) => {
    if (!visible) return
    if (props.mode === 'edit' && props.row) {
      code.value = props.row.code
      nameZh.value = props.row.nameZh
      nameEn.value = props.row.nameEn || props.row.code
      country.value = props.row.country || null
      category.value = props.row.category || null
      note.value = props.row.note || ''
      sortOrder.value = props.row.sortOrder
      isActive.value = props.row.isActive
    } else if (props.mode === 'copy' && props.row) {
      code.value = ''
      nameZh.value = props.row.nameZh
      nameEn.value = props.row.nameEn || ''
      country.value = props.row.country || null
      category.value = props.row.category || null
      note.value = props.row.note || ''
      sortOrder.value = props.row.sortOrder
      isActive.value = props.row.isActive
    } else {
      code.value = ''
      nameZh.value = ''
      nameEn.value = ''
      country.value = null
      category.value = null
      note.value = ''
      sortOrder.value = 0
      isActive.value = true
    }
  },
  { immediate: true },
)

function handleSubmit() {
  const c = code.value.trim()
  if (!c) return
  emit('submit', {
    code: c,
    nameZh: nameZh.value.trim(),
    nameEn: (nameEn.value.trim() || c),
    country: country.value?.trim() || '',
    category: category.value?.trim() || '',
    note: note.value.trim(),
    sortOrder: sortOrder.value,
    isActive: isActive.value,
  })
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    :title="mode === 'edit' ? '编辑渠道' : mode === 'copy' ? '复制渠道' : '新增渠道'"
    class="max-w-lg"
    @update:show="(v: boolean) => !v && emit('close')"
  >
    <NForm label-placement="top" size="small">
      <NFormItem label="渠道编码" required>
        <NInput
          v-model:value="code"
          placeholder="与运单 channel_code、DPS channelCode 一致，如 AEE、AU sea truck"
        />
      </NFormItem>
      <NFormItem label="中文名称" required>
        <NInput v-model:value="nameZh" placeholder="如 美国普船" />
      </NFormItem>
      <NFormItem label="英文名称">
        <NInput v-model:value="nameEn" placeholder="默认同渠道编码" />
      </NFormItem>
      <div class="grid grid-cols-2 gap-3">
        <NFormItem label="国家/地区">
          <NSelect
            v-model:value="country"
            :options="countryOptions"
            filterable
            tag
            clearable
            placeholder="选择或输入"
          />
        </NFormItem>
        <NFormItem label="大类">
          <NSelect
            v-model:value="category"
            :options="categoryOptions"
            clearable
            placeholder="快船 / 普船 / …"
          />
        </NFormItem>
      </div>
      <NFormItem label="备注">
        <NInput v-model:value="note" type="textarea" :rows="2" placeholder="可选" />
      </NFormItem>
      <div class="grid grid-cols-2 gap-3">
        <NFormItem label="排序">
          <NInputNumber v-model:value="sortOrder" class="w-full" :min="0" />
        </NFormItem>
        <NFormItem label="启用">
          <NSwitch v-model:value="isActive" />
        </NFormItem>
      </div>
    </NForm>
    <template #footer>
      <div class="flex justify-end gap-2">
        <NButton quaternary @click="emit('close')">取消</NButton>
        <NButton type="primary" :disabled="!code.trim() || !nameZh.trim()" @click="handleSubmit">
          保存
        </NButton>
      </div>
    </template>
  </NModal>
</template>
