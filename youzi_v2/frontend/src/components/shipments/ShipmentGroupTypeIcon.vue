<script setup lang="ts">
import {
  Anchor,
  Banknote,
  Hand,
  Package,
  Ship,
  Users,
  type LucideIcon,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { ICON_STROKE } from '@/constants/icons'
import type { ShipmentGroupType } from '@/constants/shipmentGroupTypes'

const props = withDefaults(
  defineProps<{
    type?: string | null
    size?: number
  }>(),
  {
    type: 'MANUAL',
    size: 14,
  },
)

const ICON_MAP: Record<ShipmentGroupType, LucideIcon> = {
  MANUAL: Hand,
  CUSTOMER_BATCH: Users,
  ORDER_BATCH: Package,
  VESSEL_BATCH: Ship,
  PORT_BATCH: Anchor,
  PAYMENT_BATCH: Banknote,
}

const Icon = computed(() => {
  const key = (props.type || 'MANUAL').trim().toUpperCase() as ShipmentGroupType
  return ICON_MAP[key] ?? Hand
})
</script>

<template>
  <component
    :is="Icon"
    :size="size"
    :stroke-width="ICON_STROKE"
    class="shrink-0 text-current"
    aria-hidden="true"
    v-bind="$attrs"
  />
</template>
