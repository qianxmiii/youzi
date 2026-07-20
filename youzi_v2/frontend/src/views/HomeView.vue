<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useMessage } from 'naive-ui'
import { getWorkbenchOverview, type WorkbenchOverview } from '@/api/workbench'
import WorkbenchHeader from '@/components/home/WorkbenchHeader.vue'
import WorkbenchFocusMetrics from '@/components/home/WorkbenchFocusMetrics.vue'
import WorkbenchTodoList from '@/components/home/WorkbenchTodoList.vue'
import WorkbenchArrivalTimeline from '@/components/home/WorkbenchArrivalTimeline.vue'
import WorkbenchTransportOverview from '@/components/home/WorkbenchTransportOverview.vue'

const message = useMessage()
const loading = ref(false)
const data = ref<WorkbenchOverview | null>(null)
const loadError = ref('')

async function load(opts: { silent?: boolean } = {}) {
  if (!opts.silent) loading.value = true
  loadError.value = ''
  try {
    const next = await getWorkbenchOverview({ todoLimit: 8, arrivalLimit: 6 })
    data.value = next
  } catch (e) {
    const msg = e instanceof Error ? e.message : '加载失败'
    loadError.value = msg
    if (!data.value) {
      message.error(msg)
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="scrollbar-subtle flex h-full min-h-0 w-full flex-col overflow-y-auto">
    <div class="workbench-home">
      <WorkbenchHeader
        :generated-at="data?.generatedAt"
        :loading="loading"
        @refresh="load({ silent: true })"
      />

      <WorkbenchFocusMetrics
        :focus="data?.focus ?? null"
        :loading="loading"
        :error="data?.focus?.available === false ? data?.focus?.error : loadError || null"
        @retry="load()"
      />

      <div class="workbench-home__main">
        <WorkbenchTodoList
          class="workbench-home__todos"
          :items="data?.todos?.items ?? []"
          :loading="loading"
          :available="data?.todos?.available"
          :error="data?.todos?.error"
          @retry="load()"
        />
        <WorkbenchArrivalTimeline
          class="workbench-home__arrivals"
          :items="data?.arrivals?.items ?? []"
          :loading="loading"
          :available="data?.arrivals?.available"
          :error="data?.arrivals?.error"
          @retry="load()"
        />
      </div>

      <WorkbenchTransportOverview
        :overview="data?.overview ?? null"
        :loading="loading"
        :error="data?.overview?.available === false ? data?.overview?.error : null"
        @retry="load()"
      />
    </div>
  </div>
</template>

<style scoped>
.workbench-home {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
  padding: 0;
  width: 100%;
}

.workbench-home__main {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

@media (min-width: 960px) {
  .workbench-home__main {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
    gap: 0.85rem;
    align-items: start;
  }
}
</style>
