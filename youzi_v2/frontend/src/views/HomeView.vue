<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import MaritimeAlertsPanel from '@/components/home/MaritimeAlertsPanel.vue'
import { fetchHealth } from '@/api/client'
import { navGroups } from '@/constants/navigation'

const router = useRouter()
const version = ref('—')
const pendingCount = ref(0)

onMounted(async () => {
  pendingCount.value = navGroups.flatMap((g) => g.items).filter((i) => i.badge).length
  try {
    const h = await fetchHealth()
    version.value = h.version || h.service || 'ok'
  } catch {
    version.value = 'legacy'
  }
})

const quickLinks = [
  { label: '船期监控', desc: '航次挂靠与海运预警', to: '/vessel-schedules' },
  { label: '运单管理', desc: '轨迹同步与异常', to: '/shipments' },
  { label: '箱规计算', desc: '录入尺寸、材积、计费重', to: '/box' },
]
</script>

<template>
  <div class="mx-auto h-full max-w-5xl space-y-8 overflow-y-auto">
    <section class="space-y-2">
      <p class="text-xs font-medium uppercase tracking-widest text-violet-400/90">Youzi v2</p>
      <h2 class="text-3xl font-semibold tracking-tight text-gradient">物流工作台</h2>
      <p class="max-w-xl text-sm text-zinc-500">
        Linear × Vercel 风格新壳。功能从旧版
        <code class="rounded bg-zinc-800/80 px-1.5 py-0.5 text-zinc-400">index.html</code>
        逐步迁入，API 沿用现有 FastAPI。
      </p>
    </section>

    <MaritimeAlertsPanel />

    <section class="grid gap-4 sm:grid-cols-3">
      <article class="panel p-4">
        <p class="text-xs text-zinc-500">待迁移模块</p>
        <p class="mt-1 text-2xl font-semibold tabular-nums text-white">{{ pendingCount }}</p>
      </article>
      <article class="panel p-4">
        <p class="text-xs text-zinc-500">API</p>
        <p class="mt-1 text-2xl font-semibold text-white">{{ version }}</p>
      </article>
      <article class="panel p-4">
        <p class="text-xs text-zinc-500">前端</p>
        <p class="mt-1 text-2xl font-semibold text-white">Vue 3</p>
      </article>
    </section>

    <section class="space-y-3">
      <h3 class="text-xs font-medium uppercase tracking-wider text-zinc-600">快捷入口</h3>
      <div class="grid gap-3 sm:grid-cols-3">
        <button
          v-for="link in quickLinks"
          :key="link.to"
          type="button"
          class="panel group p-4 text-left transition hover:border-zinc-600 hover:bg-zinc-800/40"
          @click="router.push(link.to)"
        >
          <p class="text-sm font-medium text-white group-hover:text-violet-300">{{ link.label }}</p>
          <p class="mt-1 text-xs text-zinc-500">{{ link.desc }}</p>
        </button>
      </div>
    </section>

    <section class="panel border-dashed p-4">
      <h3 class="text-sm font-medium text-zinc-300">迁移顺序建议</h3>
      <ol class="mt-3 list-decimal space-y-1.5 pl-5 text-sm text-zinc-500">
        <li>箱规计算 → <code class="text-zinc-400">/box</code></li>
        <li>单地址报价 + 历史 → <code class="text-zinc-400">/quote</code></li>
        <li>地址簿 CRUD → <code class="text-zinc-400">/addresses</code></li>
        <li>批量报价、成本、运单监控</li>
      </ol>
    </section>
  </div>
</template>
