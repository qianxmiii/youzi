<script setup lang="ts">
import { Moon, Settings, Sun } from 'lucide-vue-next'
import { ICON_STROKE } from '@/constants/icons'
import { NTooltip } from 'naive-ui'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  DEFAULT_WORLD_CLOCKS_SETTINGS,
  formatWorldClockTime,
  getWorldClockDayPhase,
  useWorldClocks,
} from '@/composables/useWorldClocks'

const { settings, tick } = useWorldClocks()

const config = computed(() => settings.value ?? DEFAULT_WORLD_CLOCKS_SETTINGS)

const visible = computed(() => config.value.enabled && (config.value.zones?.length ?? 0) > 0)

const chips = computed(() => {
  const at = tick.value
  const cfg = config.value
  return cfg.zones.map((z) => {
    const phase = getWorldClockDayPhase(z.tz, at)
    return {
      ...z,
      time: formatWorldClockTime(z.tz, cfg.use24h, at),
      phase,
      phaseLabel: phase === 'day' ? '白天' : '夜间',
    }
  })
})
</script>

<template>
  <div
    v-if="visible"
    class="world-clock-bar hidden min-w-0 items-center justify-center gap-1.5 md:flex"
  >
    <NTooltip trigger="hover">
      <template #trigger>
        <RouterLink to="/display-settings" class="world-clock-bar__gear" aria-label="世界时间设置">
          <Settings class="h-3.5 w-3.5" :stroke-width="ICON_STROKE" aria-hidden="true" />
        </RouterLink>
      </template>
      显示设置
    </NTooltip>

    <span
      v-for="c in chips"
      :key="c.tz"
      class="world-clock-chip"
      :class="`world-clock-chip--${c.phase}`"
      :title="`${c.label} · ${c.tz} · ${c.phaseLabel}`"
    >
      <span class="world-clock-chip__dot" aria-hidden="true" />
      <span class="world-clock-chip__label">{{ c.label }}</span>
      <span class="world-clock-chip__time">{{ c.time }}</span>
      <span class="world-clock-chip__icon" aria-hidden="true">
        <Sun
          v-if="c.phase === 'day'"
          class="world-clock-chip__icon-svg"
          :stroke-width="ICON_STROKE"
          fill="none"
        />
        <Moon v-else class="world-clock-chip__icon-svg" :stroke-width="ICON_STROKE" fill="none" />
      </span>
    </span>
  </div>
</template>

<style scoped>
.world-clock-bar {
  flex: 1;
  max-width: min(40rem, 55vw);
  overflow: hidden;
  padding: 0 0.25rem;
}

.world-clock-bar__gear {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.375rem;
  color: var(--color-muted);
  transition:
    color 0.15s,
    background-color 0.15s;
}

.world-clock-bar__gear:hover {
  color: var(--color-fg);
  background: var(--color-btn-ghost-bg);
}

.world-clock-chip {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.375rem;
  border-radius: 0.5rem;
  border: 1px solid var(--color-border);
  background: var(--color-panel);
  padding: 0.25rem 0.5rem 0.25rem 0.375rem;
  font-size: 0.6875rem;
  line-height: 1.35;
  white-space: nowrap;
}

.world-clock-chip__dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 9999px;
  flex-shrink: 0;
}

.world-clock-chip--day .world-clock-chip__dot {
  background: rgb(34 197 94);
  box-shadow: 0 0 0 2px rgb(34 197 94 / 0.2);
}

.world-clock-chip--night .world-clock-chip__dot {
  background: rgb(248 113 113);
  box-shadow: 0 0 0 2px rgb(248 113 113 / 0.2);
}

.world-clock-chip__label {
  color: var(--color-fg-secondary);
  font-weight: 500;
}

.world-clock-chip__time {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-fg-emphasis);
}

.world-clock-chip__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 0.125rem;
}

.world-clock-chip__icon-svg {
  width: 0.875rem;
  height: 0.875rem;
}

.world-clock-chip--day .world-clock-chip__icon {
  color: rgb(234 179 8);
}

.world-clock-chip--night .world-clock-chip__icon {
  color: rgb(217 119 6);
}

[data-theme='dark'] .world-clock-chip--day .world-clock-chip__icon {
  color: rgb(250 204 21);
}

[data-theme='dark'] .world-clock-chip--night .world-clock-chip__icon {
  color: rgb(251 191 36);
}
</style>
