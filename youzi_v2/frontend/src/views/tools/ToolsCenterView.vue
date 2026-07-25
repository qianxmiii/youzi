<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Database, FileSpreadsheet, Package } from 'lucide-vue-next'
import type { FunctionalComponent } from 'vue'
import type { LucideProps } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import {
  TOOL_CATEGORIES,
  toolStatusLabel,
  toolsByCategory,
  type ToolDefinition,
} from '@/constants/toolsRegistry'

const router = useRouter()

const CATEGORY_ICONS: Record<string, FunctionalComponent<LucideProps>> = {
  file: FileSpreadsheet,
  data: Database,
  warehouse: Package,
}

const sections = computed(() =>
  TOOL_CATEGORIES.map((cat) => ({
    ...cat,
    tools: toolsByCategory(cat.id),
  })).filter((s) => s.tools.length > 0 || s.id === 'data'),
)

function ioSummary(tool: ToolDefinition) {
  return `${tool.inputSummary} → ${tool.outputSummary}`
}

function statusBadge(tool: ToolDefinition): string | null {
  if (tool.badge === 'new' && (!tool.status || tool.status === 'active')) return '新功能'
  return toolStatusLabel(tool.status)
}

function canOpen(tool: ToolDefinition) {
  return !tool.status || tool.status === 'active'
}

function openTool(tool: ToolDefinition) {
  if (!canOpen(tool)) return
  void router.push(tool.route)
}
</script>

<template>
  <div class="flex h-full min-h-0 w-full flex-col gap-5 overflow-y-auto scrollbar-subtle">
    <div>
      <h1 class="page-h2">工具中心</h1>
      <p class="page-subtitle mt-1">
        独立业务辅助能力集中入口：文件处理、数据校验等，互不影响核心业务数据
      </p>
    </div>

    <section v-for="section in sections" :key="section.id" class="space-y-3">
      <div class="flex items-center gap-2">
        <span
          class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--color-btn-ghost-bg)] text-[var(--color-fg-secondary)]"
          aria-hidden="true"
        >
          <component
            :is="CATEGORY_ICONS[section.id] || Package"
            class="h-4 w-4"
            :stroke-width="ICON_STROKE"
          />
        </span>
        <div>
          <h2 class="section-h2 !text-[var(--color-fg-emphasis)]">{{ section.label }}</h2>
          <p class="text-xs text-[var(--color-muted)]">{{ section.description }}</p>
        </div>
      </div>

      <div
        v-if="section.tools.length"
        class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
      >
        <article
          v-for="tool in section.tools"
          :key="tool.id"
          class="tool-card"
          :class="{ 'tool-card--disabled': !canOpen(tool) }"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-[0.95rem] font-semibold text-[var(--color-fg-emphasis)]">
                  {{ tool.name }}
                </h3>
                <span
                  v-if="statusBadge(tool)"
                  class="rounded px-1.5 py-0.5 text-[0.68rem] font-medium"
                  :class="
                    statusBadge(tool) === '新功能'
                      ? 'bg-violet-500/15 text-violet-600 dark:text-violet-300'
                      : 'bg-[var(--color-btn-ghost-bg)] text-[var(--color-muted)]'
                  "
                >
                  {{ statusBadge(tool) }}
                </span>
              </div>
              <p class="mt-1 text-sm text-[var(--color-fg-secondary)]">
                {{ tool.description }}
              </p>
            </div>
          </div>

          <dl class="mt-3 space-y-1 text-xs text-[var(--color-muted)]">
            <div v-if="tool.audience" class="flex gap-2">
              <dt class="shrink-0 text-[var(--color-fg-secondary)]">适用</dt>
              <dd>{{ tool.audience }}</dd>
            </div>
            <div class="flex gap-2">
              <dt class="shrink-0 text-[var(--color-fg-secondary)]">输入/输出</dt>
              <dd>{{ ioSummary(tool) }}</dd>
            </div>
          </dl>

          <div class="mt-4">
            <button
              type="button"
              class="tool-card__cta"
              :disabled="!canOpen(tool)"
              @click="openTool(tool)"
            >
              <span>{{ canOpen(tool) ? '立即使用' : statusBadge(tool) || '暂不可用' }}</span>
              <ArrowRight
                v-if="canOpen(tool)"
                class="h-3.5 w-3.5"
                :stroke-width="ICON_STROKE"
                aria-hidden="true"
              />
            </button>
          </div>
        </article>
      </div>

      <div
        v-else
        class="rounded-xl border border-dashed border-[var(--color-border)] px-4 py-6 text-center text-sm text-[var(--color-muted)]"
      >
        暂无工具，后续按需求新增
      </div>
    </section>
  </div>
</template>

<style scoped>
.tool-card {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: 0.75rem;
  background: var(--color-elevated);
  padding: 1rem 1.05rem;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.tool-card:hover:not(.tool-card--disabled) {
  border-color: color-mix(in srgb, var(--color-accent) 35%, var(--color-border));
  background: color-mix(in srgb, var(--color-accent) 4%, var(--color-elevated));
}

.tool-card--disabled {
  opacity: 0.72;
}

.tool-card__cta {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  border-radius: 0.45rem;
  background: var(--color-btn-ghost-bg);
  padding: 0.4rem 0.7rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-accent-text);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.tool-card__cta:hover:not(:disabled) {
  background: var(--color-btn-ghost-hover);
}

.tool-card__cta:disabled {
  cursor: not-allowed;
  color: var(--color-muted);
}

.tool-card__cta:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .tool-card,
  .tool-card__cta {
    transition: none;
  }
}
</style>
