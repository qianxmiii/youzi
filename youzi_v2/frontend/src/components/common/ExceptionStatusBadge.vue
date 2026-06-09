<script setup lang="ts">
import { TriangleAlert } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NTooltip } from 'naive-ui'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    code: string
    label?: string
    durationLabel?: string | null
    /** 表格「异常」列显示简短中文名 */
    showLabel?: boolean
    size?: 'sm' | 'md'
  }>(),
  { size: 'sm', showLabel: false },
)

/** 异常码表：查验(INSPECTION) 用深红，其余用浅红 */
const isInspection = computed(() => {
  const code = props.code.trim().toUpperCase()
  if (code === 'INSPECTION') return true
  const name = (props.label || '').trim()
  return name.includes('查验')
})

const toneClass = computed(() =>
  isInspection.value ? 'exception-badge--inspection' : 'exception-badge--soft',
)

const tip = computed(() => {
  const name = props.label || props.code
  const dur = props.durationLabel?.trim()
  return dur ? `${name} · 已持续 ${dur}` : name
})

const shortLabel = computed(() => {
  const name = (props.label || props.code).trim()
  if (name.length <= 4) return name
  return name.slice(0, 4)
})
</script>

<template>
  <NTooltip trigger="hover" :show-arrow="false">
    <template #trigger>
      <span
        class="exception-badge inline-flex shrink-0 items-center gap-0.5 rounded-full border tabular-nums"
        :class="[
          toneClass,
          showLabel ? 'exception-badge--pill px-1.5 py-0.5' : 'exception-badge--icon',
          size === 'md' ? 'exception-badge--md' : '',
        ]"
        :aria-label="`异常：${tip}`"
      >
        <TriangleAlert class="exception-badge__icon" :stroke-width="ICON_STROKE" aria-hidden="true" />
        <span v-if="showLabel" class="exception-badge__text">{{ shortLabel }}</span>
      </span>
    </template>
    {{ tip }}
  </NTooltip>
</template>

<style scoped>
.exception-badge--icon {
  width: 1.125rem;
  height: 1.125rem;
  justify-content: center;
}

.exception-badge--md.exception-badge--icon {
  width: 1.25rem;
  height: 1.25rem;
}

.exception-badge--inspection {
  color: var(--badge-exception-inspection-fg);
  border-color: var(--badge-exception-inspection-border);
  background: var(--badge-exception-inspection-bg);
  box-shadow: none;
}

.exception-badge--soft {
  color: var(--badge-exception-soft-fg);
  border-color: var(--badge-exception-soft-border);
  background: var(--badge-exception-soft-bg);
}

.exception-badge__icon {
  width: 0.625rem;
  height: 0.625rem;
}

.exception-badge--md .exception-badge__icon {
  width: 0.6875rem;
  height: 0.6875rem;
}

.exception-badge__text {
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: -0.01em;
}
</style>
