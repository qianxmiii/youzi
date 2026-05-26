<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'

const { isDark, toggleTheme } = useTheme()
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :aria-label="isDark ? '切换到浅色模式' : '切换到深色模式'"
    :title="isDark ? '浅色模式' : '深色模式'"
    @click="toggleTheme"
  >
    <svg
      v-if="isDark"
      class="h-4 w-4"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="3.25" stroke="currentColor" stroke-width="1.25" />
      <path
        d="M8 1.25v1.5M8 13.25v1.5M1.25 8h1.5M13.25 8h1.5M3.05 3.05l1.06 1.06M11.89 11.89l1.06 1.06M3.05 12.95l1.06-1.06M11.89 4.11l1.06-1.06"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linecap="round"
      />
    </svg>
    <svg
      v-else
      class="h-4 w-4"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M7.5 2.5a5 5 0 1 0 4.95 5.75A4.25 4.25 0 0 1 7.5 2.5Z"
        stroke="currentColor"
        stroke-width="1.25"
        stroke-linejoin="round"
      />
    </svg>
  </button>
</template>
