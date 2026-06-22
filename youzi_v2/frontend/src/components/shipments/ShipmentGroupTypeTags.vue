<script setup lang="ts">
import { computed } from 'vue'
import ShipmentGroupTypeIcon from '@/components/shipments/ShipmentGroupTypeIcon.vue'
import { shipmentGroupTypeLabel, type ShipmentGroupType } from '@/constants/shipmentGroupTypes'

const props = withDefaults(
  defineProps<{
    types?: string[] | null
    primaryType?: string | null
    size?: 'tiny' | 'small'
    showIcons?: boolean
  }>(),
  {
    size: 'small',
    showIcons: true,
  },
)

const items = computed(() => {
  const list = (props.types ?? []).filter(Boolean)
  const primary = (props.primaryType || list[0] || 'MANUAL').trim().toUpperCase()
  const ordered = [primary, ...list.filter((t) => t.toUpperCase() !== primary)]
  return [...new Set(ordered.map((t) => t.toUpperCase()))]
})

const tagClass =
  props.size === 'tiny'
    ? 'text-[10px] px-1.5 py-0.5'
    : 'text-xs px-2 py-0.5'
</script>

<template>
  <span v-if="items.length" class="inline-flex flex-wrap items-center gap-1">
    <span
      v-for="t in items"
      :key="t"
      class="inline-flex items-center gap-1 rounded-md bg-[var(--color-btn-ghost-bg)] text-[var(--color-fg-secondary)]"
      :class="[
        tagClass,
        t === (props.primaryType || items[0] || '').toString().toUpperCase()
          ? 'ring-1 ring-[var(--color-nav-active-ring)] text-[var(--color-fg-emphasis)]'
          : '',
      ]"
      :title="shipmentGroupTypeLabel(t)"
    >
      <ShipmentGroupTypeIcon
        v-if="showIcons"
        :type="t as ShipmentGroupType"
        :size="size === 'tiny' ? 10 : 12"
      />
      <span>{{ shipmentGroupTypeLabel(t) }}</span>
    </span>
  </span>
  <span v-else class="text-[var(--color-muted)]">—</span>
</template>
