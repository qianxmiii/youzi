<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const title = computed(() => (route.meta.title as string) || '模块')
const migration = computed(() => route.meta.migration as string | undefined)
</script>

<template>
  <div class="mx-auto flex h-full max-w-lg flex-col items-center justify-center overflow-y-auto py-20 text-center">
    <div
      class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--color-border)] bg-zinc-900/50 text-2xl"
    >
      ◌
    </div>
    <h2 class="text-xl font-semibold tracking-tight text-white">{{ title }}</h2>
    <p class="mt-2 text-sm text-zinc-500">此页面等待从旧版迁移实现。</p>
    <p v-if="migration" class="mt-4 rounded-lg border border-dashed border-zinc-700 bg-zinc-900/30 px-4 py-2 text-xs text-zinc-500">
      {{ migration }}
    </p>
    <button
      type="button"
      class="mt-8 rounded-lg bg-white px-4 py-2 text-sm font-medium text-zinc-950 transition hover:bg-zinc-200"
      @click="router.push('/')"
    >
      返回工作台
    </button>
  </div>
</template>
