<script setup lang="ts">
import { NTooltip } from 'naive-ui'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavIcon from '@/components/icons/NavIcon.vue'
import { useSidebarCollapsed } from '@/composables/useSidebarCollapsed'
import { navGroups } from '@/constants/navigation'

const route = useRoute()
const { collapsed, toggle } = useSidebarCollapsed()

const flatItems = computed(() => navGroups.flatMap((g) => g.items))

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path === path || route.path.startsWith(`${path}/`)
}

function itemLabel(name: string, badge?: string) {
  return badge ? `${name}（${badge}）` : name
}
</script>

<template>
  <aside
    class="flex h-full shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-panel)] transition-[width] duration-200 ease-out"
    :class="collapsed ? 'w-14' : 'w-[240px]'"
  >
    <div
      class="flex h-14 shrink-0 items-center border-b border-[var(--color-border)]"
      :class="collapsed ? 'justify-center px-0' : 'gap-2.5 px-4'"
    >
      <img
        src="/youzi-app-icon.png"
        alt="Youzi"
        class="h-7 w-7 shrink-0 rounded-lg object-cover shadow-lg shadow-violet-500/20"
      />
      <div v-if="!collapsed" class="min-w-0">
        <div class="truncate text-sm font-semibold tracking-tight text-white">Youzi</div>
        <div class="text-[11px] text-zinc-500">v2 · 迁移中</div>
      </div>
    </div>

    <nav
      class="scrollbar-subtle flex-1 overflow-x-hidden overflow-y-auto py-3"
      :class="collapsed ? 'px-1.5' : 'px-2'"
    >
      <div
        v-for="(group, gi) in navGroups"
        :key="group.label"
        :class="[gi > 0 && collapsed ? 'mt-2 border-t border-[var(--color-border)] pt-2' : '', gi > 0 && !collapsed ? 'mt-4' : '']"
      >
        <div
          v-if="!collapsed"
          class="mb-1 px-2.5 text-[10px] font-medium uppercase tracking-wider text-zinc-600"
        >
          {{ group.label }}
        </div>
        <NTooltip
          v-for="item in group.items"
          :key="item.to"
          :disabled="!collapsed"
          placement="right"
          :show-arrow="false"
        >
          <template #trigger>
            <RouterLink
              :to="item.to"
              class="nav-item mb-0.5"
              :class="[
                { 'nav-item-active': isActive(item.to) },
                collapsed ? 'justify-center px-0 py-2.5' : '',
              ]"
              :aria-label="item.name"
            >
              <NavIcon :name="item.icon" />
              <span v-if="!collapsed" class="flex-1 truncate">{{ item.name }}</span>
              <span
                v-if="!collapsed && item.badge"
                class="rounded-md bg-zinc-800 px-1.5 py-0.5 text-[10px] font-medium text-zinc-500"
              >
                {{ item.badge }}
              </span>
            </RouterLink>
          </template>
          {{ itemLabel(item.name, item.badge) }}
        </NTooltip>
      </div>
    </nav>

    <div class="shrink-0 border-t border-[var(--color-border)] p-2">
      <NTooltip :disabled="!collapsed" placement="right" :show-arrow="false">
        <template #trigger>
          <a
            href="http://127.0.0.1:3001/"
            target="_blank"
            rel="noopener"
            class="nav-item w-full text-zinc-500 hover:text-zinc-300"
            :class="collapsed ? 'justify-center px-0 py-2.5' : ''"
            aria-label="旧版后台"
          >
            <NavIcon name="settings" />
            <span v-if="!collapsed">旧版后台</span>
          </a>
        </template>
        旧版后台
      </NTooltip>

      <button
        type="button"
        class="nav-item mt-1 w-full text-zinc-500 hover:text-zinc-300"
        :class="collapsed ? 'justify-center px-0 py-2.5' : ''"
        :aria-label="collapsed ? '展开侧栏' : '收起侧栏'"
        @click="toggle"
      >
        <svg
          class="h-4 w-4 shrink-0 transition-transform duration-200"
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
        <span v-if="!collapsed" class="text-xs">收起侧栏</span>
      </button>

      <div v-if="!collapsed" class="mt-2 px-2.5 text-[10px] leading-relaxed text-zinc-600">
        {{ flatItems.length }} 个模块 · Linear / Vercel 风格壳
      </div>
    </div>
  </aside>
</template>
