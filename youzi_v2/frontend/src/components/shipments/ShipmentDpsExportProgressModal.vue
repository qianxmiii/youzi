<script setup lang="ts">
import { NModal, NProgress } from 'naive-ui'
import { computed } from 'vue'

const props = defineProps<{
  show: boolean
  title: string
  message: string
  progress: number
  failed?: boolean
}>()

const emit = defineEmits<{ 'update:show': [value: boolean] }>()

const clampedProgress = computed(() => Math.max(0, Math.min(100, props.progress)))
const statusType = computed(() => (props.failed ? 'error' : clampedProgress.value >= 100 ? 'success' : 'default'))
</script>

<template>
  <NModal
    :show="show"
    :mask-closable="false"
    :close-on-esc="false"
    :auto-focus="false"
    transform-origin="center"
    @update:show="$emit('update:show', $event)"
  >
    <div
      class="w-[min(420px,calc(100vw-2rem))] rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-5 shadow-xl"
    >
      <h3 class="text-base font-semibold text-[var(--color-text)]">{{ title }}</h3>
      <p class="mt-2 min-h-[2.5rem] text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {{ message }}
      </p>
      <NProgress
        class="mt-4"
        type="line"
        :percentage="clampedProgress"
        :status="statusType"
        :show-indicator="true"
        :height="10"
        :border-radius="4"
      />
      <p v-if="!failed" class="mt-3 text-xs text-[var(--color-muted)]">
        请勿关闭页面，完成后将自动保存文件。
      </p>
      <button
        v-else
        type="button"
        class="mt-4 w-full rounded-lg border border-[var(--color-border)] py-2 text-sm hover:bg-[var(--color-bg-muted)]"
        @click="emit('update:show', false)"
      >
        关闭
      </button>
    </div>
  </NModal>
</template>
