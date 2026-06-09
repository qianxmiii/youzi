<script setup lang="ts">
import { Bell } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'

withDefaults(
  defineProps<{
    size?: number
    /** 已订阅：铃铛实心填充 */
    filled?: boolean
  }>(),
  { size: 18, filled: false },
)
</script>

<template>
  <Bell
    class="bell-icon"
    :size="size"
    :stroke-width="ICON_STROKE"
    :fill="filled ? 'currentColor' : 'none'"
    aria-hidden="true"
  />
</template>
