<script setup lang="ts">
import { NButton, NCheckbox, NDrawer, NDrawerContent, NSpace } from 'naive-ui'
import { computed } from 'vue'
import {
  DEFAULT_SHIPMENT_VISIBLE_COLUMNS,
  SHIPMENT_COLUMN_LABELS,
  SHIPMENT_COLUMN_STORAGE_KEY,
  SHIPMENT_LIST_COLUMN_GROUPS,
} from '@/constants/shipmentListFilterMeta'

const show = defineModel<boolean>('show', { default: false })
const visibleKeys = defineModel<string[]>('visibleKeys', { required: true })

const grouped = computed(() =>
  SHIPMENT_LIST_COLUMN_GROUPS.map((g) => ({
    group: g.group,
    items: g.keys.map((key) => ({
      key,
      label: SHIPMENT_COLUMN_LABELS[key] || key,
    })),
  })),
)

function toggle(key: string, checked: boolean) {
  const set = new Set(visibleKeys.value)
  if (checked) set.add(key)
  else set.delete(key)
  visibleKeys.value = [...set]
}

function restoreDefault() {
  visibleKeys.value = [...DEFAULT_SHIPMENT_VISIBLE_COLUMNS]
  localStorage.setItem(SHIPMENT_COLUMN_STORAGE_KEY, JSON.stringify(visibleKeys.value))
}

function saveAndClose() {
  localStorage.setItem(SHIPMENT_COLUMN_STORAGE_KEY, JSON.stringify(visibleKeys.value))
  show.value = false
}
</script>

<template>
  <NDrawer v-model:show="show" :width="360" placement="right">
    <NDrawerContent title="列设置" closable>
      <div class="space-y-4">
        <section v-for="section in grouped" :key="section.group">
          <p class="mb-2 text-xs font-medium text-[var(--color-muted)]">{{ section.group }}</p>
          <NSpace vertical :size="8">
            <NCheckbox
              v-for="item in section.items"
              :key="item.key"
              :checked="visibleKeys.includes(item.key)"
              @update:checked="(v) => toggle(item.key, v)"
            >
              {{ item.label }}
            </NCheckbox>
          </NSpace>
        </section>
      </div>
      <template #footer>
        <NSpace justify="end">
          <NButton size="small" quaternary @click="restoreDefault">恢复默认</NButton>
          <NButton size="small" type="primary" @click="saveAndClose">保存</NButton>
        </NSpace>
      </template>
    </NDrawerContent>
  </NDrawer>
</template>
