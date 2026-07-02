<script setup lang="ts">
import { CalendarClock, CircleDollarSign, ShieldAlert, Ship, TriangleAlert } from 'lucide-vue-next'
import { computed, h } from 'vue'
import { NTooltip } from 'naive-ui'
import { ICON_STROKE } from '@/constants/icons'
import { shipmentGroupAlertRuleKind } from '@/constants/shipmentGroupRules'
import { formatRelativeTime } from '@/utils/formatDateTime'
import { splitGroupAlertMessage } from '@/utils/formatGroupAlertMessage'

const props = withDefaults(
  defineProps<{
    title: string
    message: string
    subtitle?: string
    customerName?: string
    ruleType?: string
    triggeredAt?: string | null
    severity?: string
    read?: boolean
    resolved?: boolean
    compact?: boolean
    clickable?: boolean
  }>(),
  {
    subtitle: '',
    customerName: '',
    ruleType: '',
    triggeredAt: null,
    severity: 'warning',
    read: false,
    resolved: false,
    compact: false,
    clickable: false,
  },
)

const emit = defineEmits<{
  click: []
}>()

const ruleKind = computed(() => shipmentGroupAlertRuleKind(props.ruleType))

const iconComponent = computed(() => {
  if (ruleKind.value === 'exception') return ShieldAlert
  if (ruleKind.value === 'delivery') return CalendarClock
  if (ruleKind.value === 'payment') return CircleDollarSign
  if (ruleKind.value === 'arrival') return Ship
  return TriangleAlert
})

const cardClass = computed(() => {
  const sev = (props.severity || 'warning').toLowerCase()
  let tone = sev === 'urgent' ? 'urgent' : sev === 'info' ? 'info' : 'warning'
  if (ruleKind.value === 'exception') {
    tone = 'exception'
  } else if (ruleKind.value === 'payment' && tone === 'warning') {
    tone = 'payment'
  } else if (ruleKind.value === 'arrival' && (tone === 'warning' || tone === 'info')) {
    tone = 'arrival'
  }
  const state = props.resolved ? 'resolved' : props.read ? 'read' : 'active'
  return [
    'group-alert-card',
    `group-alert-card--${tone}`,
    `group-alert-card--${state}`,
    ruleKind.value !== 'default' ? `group-alert-card--kind-${ruleKind.value}` : '',
    props.compact ? 'group-alert-card--compact' : '',
    props.clickable ? 'group-alert-card--clickable' : '',
  ]
})

const timeNode = computed(() => {
  const formatted = formatRelativeTime(props.triggeredAt)
  if (!formatted) return null
  return h(
    NTooltip,
    { trigger: 'hover' },
    {
      trigger: () =>
        h(
          'span',
          { class: 'group-alert-card__time cursor-default tabular-nums' },
          formatted.relative,
        ),
      default: () => formatted.absolute,
    },
  )
})

const messageParts = computed(() => splitGroupAlertMessage(props.message))
</script>

<template>
  <article :class="cardClass">
    <div class="group-alert-card__icon" aria-hidden="true">
      <component :is="iconComponent" class="group-alert-card__icon-svg" :stroke-width="ICON_STROKE" />
    </div>
    <div
      class="group-alert-card__body"
      :role="clickable ? 'button' : undefined"
      :tabindex="clickable ? 0 : undefined"
      @click="clickable ? emit('click') : undefined"
      @keydown.enter.prevent="clickable ? emit('click') : undefined"
      @keydown.space.prevent="clickable ? emit('click') : undefined"
    >
      <div class="group-alert-card__head">
        <div class="group-alert-card__head-main">
          <h4 class="group-alert-card__title">{{ title }}</h4>
          <span v-if="customerName" class="group-alert-card__customer-badge">{{ customerName }}</span>
        </div>
        <component :is="timeNode" v-if="timeNode" />
      </div>
      <p v-if="subtitle" class="group-alert-card__subtitle">{{ subtitle }}</p>
      <p class="group-alert-card__message">
        <template v-for="(part, idx) in messageParts" :key="idx">
          <span v-if="part.highlight" class="group-alert-card__value">{{ part.text }}</span>
          <span v-else>{{ part.text }}</span>
        </template>
      </p>
      <div v-if="$slots.default" class="group-alert-card__actions">
        <slot />
      </div>
    </div>
    <div v-if="$slots.aside" class="group-alert-card__aside">
      <slot name="aside" />
    </div>
  </article>
</template>
