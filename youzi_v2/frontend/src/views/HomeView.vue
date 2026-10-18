<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { getWorkbenchOverview, type WorkbenchOverview } from '@/api/workbench'
import WorkbenchHeader from '@/components/home/WorkbenchHeader.vue'
import WorkbenchFocusMetrics from '@/components/home/WorkbenchFocusMetrics.vue'
import WorkbenchArrivalTimeline from '@/components/home/WorkbenchArrivalTimeline.vue'
import WorkbenchRouteStatusFunnel from '@/components/home/WorkbenchRouteStatusFunnel.vue'

const message = useMessage()
const loading = ref(false)
const refreshing = ref(false)
const data = ref<WorkbenchOverview | null>(null)
const loadError = ref('')

async function load(opts: { silent?: boolean } = {}) {
  if (opts.silent) {
    if (refreshing.value) return
    refreshing.value = true
  } else {
    loading.value = true
  }
  loadError.value = ''
  try {
    const next = await getWorkbenchOverview({ todoLimit: 1, arrivalLimit: 8 })
    data.value = next
  } catch (e) {
    const msg = e instanceof Error ? e.message : '加载失败'
    loadError.value = msg
    if (!data.value) {
      message.error(msg)
    } else if (opts.silent) {
      message.error(msg, { duration: 4000 })
    }
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="scrollbar-subtle flex h-full min-h-0 w-full flex-col gap-4 overflow-y-auto">
    <WorkbenchHeader
      :generated-at="data?.generatedAt"
      :refreshing="refreshing"
      :disabled="loading && !data"
      @refresh="load({ silent: true })"
    />

    <WorkbenchRouteStatusFunnel
      :module="data?.routeStatus ?? null"
      :loading="loading"
      :error="data?.routeStatus?.available === false ? data?.routeStatus?.error : null"
      :exception-stuck="data?.focus?.pendingExceptions ?? 0"
      @retry="load()"
    />

    <WorkbenchFocusMetrics
      :focus="data?.focus ?? null"
      :loading="loading"
      :error="data?.focus?.available === false ? data?.focus?.error : loadError || null"
      @retry="load()"
    />

    <WorkbenchArrivalTimeline
      :items="data?.arrivals?.items ?? []"
      :loading="loading"
      :available="data?.arrivals?.available"
      :error="data?.arrivals?.error"
      @retry="load()"
    />
  </div>
</template>
