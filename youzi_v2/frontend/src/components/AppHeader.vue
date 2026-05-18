<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { fetchHealth, fetchLegacyHealth } from '@/api/client'
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
  <header class="glass-header flex h-14 shrink-0 items-center justify-between px-6">
    <div class="flex min-w-0 items-center gap-3">
      <button
        type="button"
        class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--color-border)] bg-white/[0.04] text-zinc-400 transition hover:bg-white/[0.08] hover:text-white"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        :title="collapsed ? '展开侧栏' : '收起侧栏'"
        @click="toggle"
      >
        <svg
          class="h-4 w-4 transition-transform duration-200"
          :class="collapsed ? 'rotate-180' : ''"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M10 3 5 8l5 5"
            stroke="currentColor"
            stroke-width="1.25"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
      <div class="min-w-0">
        <h1 class="text-sm font-semibold tracking-tight text-white">{{ title }}</h1>
        <p v-if="migration" class="mt-0.5 text-xs text-zinc-500">迁移来源：{{ migration }}</p>
      </div>
    </div>

    <div class="flex items-center gap-3">
      <span
        class="inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-zinc-900/80 px-2.5 py-1 text-xs text-zinc-400"
      >
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
      <a
        href="http://127.0.0.1:3001/"
        target="_blank"
        rel="noopener"
        class="rounded-lg border border-[var(--color-border)] bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:bg-white/[0.08] hover:text-white"
      >
        Legacy
      </a>
    </div>
  </header>
</template>
