<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: 'sm' | 'md'
    title?: string
    /** 可点击跳转官网时显示手型与悬停高亮 */
    interactive?: boolean
  }>(),
  {
    size: 'sm',
    title: '',
    interactive: false,
  },
)
</script>

<template>
  <span
    class="last-mile-badge inline-flex shrink-0 items-center justify-center font-semibold"
    :class="[
      size === 'md' ? 'last-mile-badge--md' : '',
      interactive ? 'last-mile-badge--interactive' : '',
    ]"
    :title="title || undefined"
    aria-label="转单"
  >
    转
  </span>
</template>

<style scoped>
.last-mile-badge {
  min-width: 1.125rem;
  height: 1.125rem;
  padding: 0 0.2rem;
  border-radius: 0.25rem;
  font-size: 0.625rem;
  line-height: 1;
  letter-spacing: 0.02em;
  color: rgb(103 232 249);
  background: rgb(8 145 178 / 0.2);
  border: 1px solid rgb(34 211 238 / 0.35);
  box-shadow: 0 0 6px rgb(34 211 238 / 0.12);
}

.last-mile-badge--md {
  min-width: 1.25rem;
  height: 1.25rem;
  font-size: 0.6875rem;
}

.last-mile-badge--interactive {
  cursor: pointer;
}

.last-mile-badge--interactive:hover {
  color: rgb(165 243 252);
  border-color: rgb(34 211 238 / 0.55);
  background: rgb(8 145 178 / 0.32);
  box-shadow: 0 0 8px rgb(34 211 238 / 0.2);
}
</style>
