<script setup lang="ts">
import type { DistributionItem } from '@/api/statistics'

defineProps<{
  items: DistributionItem[]
  total?: number
  emptyText?: string
}>()

function pct(ratio: number) {
  return `${(ratio * 100).toFixed(1)}%`
}
</script>

<template>
  <div v-if="!items.length" class="text-xs text-[var(--color-muted)]">{{ emptyText || '暂无数据' }}</div>
  <ul v-else class="space-y-2.5">
    <li v-for="item in items" :key="item.key" class="min-w-0">
      <div class="mb-1 flex items-baseline justify-between gap-2 text-xs">
        <span class="truncate text-[var(--color-fg)]" :title="item.label">{{ item.label }}</span>
        <span class="shrink-0 tabular-nums text-[var(--color-muted)]">
          {{ item.count }}
          <span class="text-[var(--color-fg-secondary)]">· {{ pct(item.ratio) }}</span>
        </span>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-[var(--color-border-subtle)]">
        <div
          class="h-full rounded-full bg-violet-500/80 transition-all duration-300"
          :style="{ width: `${Math.max(item.ratio * 100, item.count > 0 ? 2 : 0)}%` }"
        />
      </div>
    </li>
  </ul>
</template>
