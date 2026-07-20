<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'
import { NButton } from 'naive-ui'
import { ICON_STROKE } from '@/constants/icons'

defineProps<{
  generatedAt?: string | null
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

function formatUpdated(raw?: string | null) {
  const text = (raw || '').trim()
  if (!text) return '—'
  // 展示 HH:mm，完整时间放 title
  const m = text.match(/(\d{2}:\d{2})/)
  return m ? m[1] : text
}
</script>

<template>
  <header class="workbench-header">
    <div>
      <h1 class="page-h2">物流工作台</h1>
      <p class="page-subtitle mt-1">
        最后更新
        <span :title="generatedAt || undefined">{{ formatUpdated(generatedAt) }}</span>
      </p>
    </div>
    <NButton
      quaternary
      circle
      size="small"
      :loading="loading"
      aria-label="刷新工作台"
      @click="emit('refresh')"
    >
      <template #icon>
        <RefreshCw class="h-4 w-4" :stroke-width="ICON_STROKE" />
      </template>
    </NButton>
  </header>
</template>

<style scoped>
.workbench-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}
</style>
