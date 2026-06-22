<script setup lang="ts">
import { computed } from 'vue'
import ShipmentGroupTypeIcon from '@/components/shipments/ShipmentGroupTypeIcon.vue'
import { shipmentGroupTypeLabel } from '@/constants/shipmentGroupTypes'

const props = withDefaults(
  defineProps<{
    type?: string | null
    /** 不传则按 type 自动解析 */
    label?: string
    iconSize?: number
  }>(),
  {
    iconSize: 12,
  },
)

const text = computed(() => props.label ?? shipmentGroupTypeLabel(props.type))
</script>

<template>
  <span class="inline-flex items-center gap-1">
    <ShipmentGroupTypeIcon :type="type" :size="iconSize" />
    <span>{{ text }}</span>
  </span>
</template>
