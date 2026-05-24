<script setup lang="ts">
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
        <svg
          class="exception-badge__icon"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M8 2.2 13.6 12.4H2.4L8 2.2Z"
            stroke="currentColor"
            stroke-width="1.35"
            stroke-linejoin="round"
          />
          <path
            d="M8 6.2v3.2M8 11.1h.01"
            stroke="currentColor"
            stroke-width="1.35"
            stroke-linecap="round"
          />
        </svg>
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

/* 查验：深红 */
.exception-badge--inspection {
  color: rgb(248 113 113);
  border-color: rgb(185 28 28 / 0.55);
  background: rgb(127 29 29 / 0.45);
  box-shadow: 0 0 0 1px rgb(69 10 10 / 0.25);
}

/* 其他异常：浅红 */
.exception-badge--soft {
  color: rgb(252 165 165);
  border-color: rgb(248 113 113 / 0.28);
  background: rgb(239 68 68 / 0.1);
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
