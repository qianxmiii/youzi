<script setup lang="ts">
import { NButton, NTooltip, useMessage } from 'naive-ui'
import { computed } from 'vue'
import LastMileBadge from '@/components/common/LastMileBadge.vue'
import type { Shipment } from '@/types/shipment'
import { resolveLastMileTracking } from '@/utils/lastMileTracking'

const props = defineProps<{
  shipment: Shipment
}>()

const message = useMessage()

const lastMile = computed(() => resolveLastMileTracking(props.shipment))

async function copyNumber() {
  const n = lastMile.value?.number
  if (!n) return
  try {
    await navigator.clipboard.writeText(n)
    message.success('已复制转单号')
  } catch {
    message.error('复制失败')
  }
}

function openTrackUrl() {
  const url = lastMile.value?.url
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}
</script>

<template>
  <div
    v-if="lastMile"
    class="last-mile-header mb-3 space-y-1.5 rounded-md border px-3 py-2.5"
  >
    <div class="flex flex-wrap items-center gap-1.5">
      <LastMileBadge size="md" />
      <span class="last-mile-label text-[11px] font-medium">转单号</span>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <code class="last-mile-code max-w-full truncate font-mono text-xs">{{ lastMile.number }}</code>
      <div class="flex shrink-0 items-center gap-1">
        <NButton size="tiny" quaternary @click="copyNumber">复制</NButton>
        <NTooltip v-if="!lastMile.url" trigger="hover">
          <template #trigger>
            <NButton size="tiny" quaternary disabled>官网查询</NButton>
          </template>
          暂未识别承运商官网，请手动查询
        </NTooltip>
        <NButton
          v-else
          size="tiny"
          type="primary"
          secondary
          @click="openTrackUrl"
        >
          {{ lastMile.carrierLabel }} 查询（{{ lastMile.trackLang === 'en' ? '英文' : '中文' }}）
        </NButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.last-mile-header {
  border-color: var(--last-mile-border);
  background: var(--last-mile-bg);
}

.last-mile-label {
  color: var(--last-mile-label);
}

.last-mile-code {
  color: var(--last-mile-code);
}
</style>
