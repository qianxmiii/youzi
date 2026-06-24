<script setup lang="ts">
import { CalendarClock, CircleDollarSign, Ship, TriangleAlert } from 'lucide-vue-next'
import type { Component } from 'vue'
import { computed } from 'vue'
import { ICON_STROKE } from '@/constants/icons'
import {
  shipmentGroupAlertRuleKind,
  shipmentGroupRuleLabel,
  type ShipmentGroupAlertRuleKind,
} from '@/constants/shipmentGroupRules'

const props = withDefaults(
  defineProps<{
    ruleType: string
    size?: number
  }>(),
  {
    size: 14,
  },
)

const ICON_MAP: Record<ShipmentGroupAlertRuleKind, Component> = {
  delivery: CalendarClock,
  payment: CircleDollarSign,
  arrival: Ship,
  default: TriangleAlert,
}

const kind = computed(() => shipmentGroupAlertRuleKind(props.ruleType))
const iconComponent = computed(() => ICON_MAP[kind.value])
const label = computed(() => shipmentGroupRuleLabel(props.ruleType))
</script>

<template>
  <span
    class="shipment-group-rule-icon"
    :class="`shipment-group-rule-icon--${kind}`"
    :title="label"
    aria-hidden="true"
  >
    <component
      :is="iconComponent"
      class="shipment-group-rule-icon__svg"
      :size="size"
      :stroke-width="ICON_STROKE"
    />
  </span>
</template>
