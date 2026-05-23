<script setup lang="ts">
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
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path
        d="M8 2.8 9.55 6.2l3.7.55-2.68 2.6.63 3.65L8 11.1l-3.2 1.9.63-3.65-2.68-2.6 3.7-.55L8 2.8Z"
      />
    </svg>
  </span>
</template>

<style scoped>
.vip-star-badge {
  color: rgb(250 204 21);
  filter: drop-shadow(0 0 4px rgb(245 158 11 / 0.35));
}

.vip-star-badge svg {
  width: 0.875rem;
  height: 0.875rem;
}

.vip-star-badge--md svg {
  width: 1rem;
  height: 1rem;
}
</style>
