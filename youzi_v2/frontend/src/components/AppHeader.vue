<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchHealth, fetchLegacyHealth } from '@/api/client'
import AppMessageBell from '@/components/AppMessageBell.vue'
import AppTodoBell from '@/components/AppTodoBell.vue'
import WorldClockBar from '@/components/header/WorldClockBar.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { ChevronLeft } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { useSidebarCollapsed } from '@/composables/useSidebarCollapsed'

const route = useRoute()
const { collapsed, toggle } = useSidebarCollapsed()
const apiOk = ref<boolean | null>(null)

const title = computed(() => (route.meta.title as string) || '工作台')
const migration = computed(() => route.meta.migration as string | undefined)

onMounted(async () => {
  try {
    await fetchHealth()
    apiOk.value = true
  } catch {
    try {
      await fetchLegacyHealth()
      apiOk.value = true
    } catch {
      apiOk.value = false
    }
  }
})
</script>

<template>
  <header class="glass-header grid h-14 shrink-0 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 px-6">
    <div class="flex min-w-0 items-center gap-3 justify-self-start">
      <button
        type="button"
        class="header-ghost-btn"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        :title="collapsed ? '展开侧栏' : '收起侧栏'"
        @click="toggle"
      >
        <ChevronLeft
          class="h-4 w-4 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
          :stroke-width="ICON_STROKE"
          aria-hidden="true"
        />
      </button>
      <div class="min-w-0">
        <h1 class="text-sm font-semibold tracking-tight text-[var(--color-fg-emphasis)]">
          {{ title }}
        </h1>
        <p v-if="migration" class="mt-0.5 text-xs text-[var(--color-muted)]">
          迁移来源：{{ migration }}
        </p>
      </div>
    </div>

    <WorldClockBar class="justify-self-center" />

    <div class="relative z-20 flex shrink-0 items-center gap-2 justify-self-end">
      <AppTodoBell />
      <AppMessageBell />
      <span class="status-pill">
        <span
          class="h-1.5 w-1.5 rounded-full"
          :class="
            apiOk === null
              ? 'animate-pulse bg-zinc-500'
              : apiOk
                ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]'
                : 'bg-red-500'
          "
        />
        API {{ apiOk === null ? '检测中' : apiOk ? '已连接' : '未启动' }}
      </span>
      <ThemeToggle />
      <a
        href="http://127.0.0.1:3001/"
        target="_blank"
        rel="noopener"
        class="header-link-btn"
      >
        Legacy
      </a>
    </div>
  </header>
</template>
