<script setup lang="ts">
import { Moon, Sun } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
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
    <Sun v-if="isDark" class="h-4 w-4" :stroke-width="ICON_STROKE" aria-hidden="true" />
    <Moon v-else class="h-4 w-4" :stroke-width="ICON_STROKE" aria-hidden="true" />
  </button>
</template>
