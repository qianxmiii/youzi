<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'
import { NTooltip } from 'naive-ui'
import { ICON_STROKE } from '@/constants/icons'

const props = defineProps<{
  generatedAt?: string | null
  refreshing?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

function formatUpdated(raw?: string | null) {
  const text = (raw || '').trim()
  if (!text) return '尚未加载'
  const normalized = text.replace(' ', 'T')
  const d = new Date(normalized)
  if (!Number.isNaN(d.getTime())) {
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `${hh}:${mm}`
  }
  const m = text.match(/(\d{2}:\d{2})/)
  return m ? m[1] : text
}

function onRefresh() {
  if (props.disabled || props.refreshing) return
  emit('refresh')
}
</script>

<template>
  <header class="workbench-header">
    <div class="min-w-0">
      <h1 class="page-h2">物流工作台</h1>
      <p class="page-subtitle mt-1 workbench-header__meta">
        全量掌控在途状态、时效预警及关键节点卡点
      </p>
    </div>

    <div class="workbench-header__actions shrink-0">
      <NTooltip placement="bottom-end" :show-arrow="false">
        <template #trigger>
          <span
            class="workbench-header__time tabular-nums"
            :title="generatedAt || undefined"
          >
            数据更新于 {{ formatUpdated(generatedAt) }}
          </span>
        </template>
        <span class="text-xs">
          {{ generatedAt ? `数据时间：${generatedAt}` : '首次进入时自动加载' }}
        </span>
      </NTooltip>

      <NTooltip placement="bottom-end" :show-arrow="false">
        <template #trigger>
          <button
            type="button"
            class="workbench-refresh"
            :class="{ 'workbench-refresh--busy': refreshing }"
            :disabled="disabled || refreshing"
            aria-label="刷新工作台数据"
            @click="onRefresh"
          >
            <RefreshCw
              class="workbench-refresh__icon"
              :class="{ 'workbench-refresh__icon--spin': refreshing }"
              :stroke-width="ICON_STROKE"
            />
            <span class="workbench-refresh__label">{{ refreshing ? '更新中' : '刷新' }}</span>
          </button>
        </template>
        <span class="text-xs leading-relaxed">
          重新拉取工作台数据（明细状态、今日动态、到港等）<br />
          不整页空白，仅更新数字与列表
        </span>
      </NTooltip>
    </div>
  </header>
</template>

<style scoped>
.workbench-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem 1rem;
}

.workbench-header__meta {
  max-width: 28rem;
}

.workbench-header__actions {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.2rem 0.25rem 0.2rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-elevated);
}

.workbench-header__time {
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--color-muted);
  white-space: nowrap;
}

.workbench-refresh {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.75rem 0.35rem 0.55rem;
  border: none;
  border-radius: 999px;
  background: var(--color-btn-ghost-bg);
  color: var(--color-fg-secondary);
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease,
    box-shadow 0.15s ease;
}

.workbench-refresh:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-accent-text) 12%, var(--color-btn-ghost-bg));
  color: var(--color-fg-emphasis);
}

.workbench-refresh:focus-visible {
  outline: 2px solid var(--color-accent-text);
  outline-offset: 2px;
}

.workbench-refresh:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.workbench-refresh--busy {
  color: var(--color-accent-text);
}

.workbench-refresh__icon {
  width: 0.95rem;
  height: 0.95rem;
  flex-shrink: 0;
}

.workbench-refresh__icon--spin {
  animation: workbench-refresh-spin 0.75s linear infinite;
}

.workbench-refresh__label {
  white-space: nowrap;
}

@keyframes workbench-refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .workbench-refresh__icon--spin {
    animation: none;
  }
}
</style>
