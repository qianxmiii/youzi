<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: string
    /** 已订阅：铃铛实心填充 */
    filled?: boolean
  }>(),
  { size: '1.125rem', filled: false },
)
</script>

<template>
  <svg
    viewBox="0 0 20 20"
    fill="none"
    class="bell-icon"
    :style="{ width: size, height: size }"
    aria-hidden="true"
  >
    <path
      d="M10 2.75c-2.76 0-5 2.24-5 5v2.35l-1.15 2.3h12.3l-1.15-2.3V7.75c0-2.76-2.24-5-5-5Z"
      :fill="filled ? 'currentColor' : 'none'"
      stroke="currentColor"
      stroke-width="1.35"
      stroke-linejoin="round"
    />
    <path
      d="M7.75 14.75a2.25 2.25 0 0 0 4.5 0"
      fill="none"
      stroke="currentColor"
      stroke-width="1.35"
      stroke-linecap="round"
    />
  </svg>
</template>
