<script setup lang="ts">
import { NButton, NTag } from 'naive-ui'
import type { ShipmentFilterTag } from '@/utils/shipmentListFilterQuery'

defineProps<{
  tags: ShipmentFilterTag[]
}>()

const emit = defineEmits<{
  remove: [key: string]
  clear: []
}>()
</script>

<template>
  <div
    v-if="tags.length"
    class="flex min-w-0 flex-wrap items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-soft)] px-3 py-2"
  >
    <span class="shrink-0 text-xs text-[var(--color-muted)]">已筛选</span>
    <NTag
      v-for="tag in tags"
      :key="tag.key"
      closable
      size="small"
      @close="emit('remove', tag.key)"
    >
      {{ tag.label }}
    </NTag>
    <NButton size="tiny" quaternary class="ml-auto" @click="emit('clear')">清空</NButton>
  </div>
</template>
