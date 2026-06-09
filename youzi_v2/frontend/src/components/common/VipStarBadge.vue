<script setup lang="ts">
import { Star } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'

withDefaults(
  defineProps<{
    size?: 'sm' | 'md'
  }>(),
  { size: 'sm' },
)
</script>

<template>
  <span
    class="vip-star-badge inline-flex shrink-0 items-center justify-center"
    :class="size === 'md' ? 'vip-star-badge--md' : ''"
    aria-label="VIP"
  >
    <Star class="vip-star-badge__icon" :stroke-width="ICON_STROKE" fill="currentColor" aria-hidden="true" />
  </span>
</template>

<style scoped>
.vip-star-badge {
  color: rgb(250 204 21);
  filter: drop-shadow(0 0 4px rgb(245 158 11 / 0.35));
}

.vip-star-badge__icon {
  width: 0.875rem;
  height: 0.875rem;
}

.vip-star-badge--md .vip-star-badge__icon {
  width: 1rem;
  height: 1rem;
}
</style>
