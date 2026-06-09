import { onMounted, onUnmounted, ref } from 'vue'
import { getWorldClocksSettings, type WorldClocksSettings } from '@/api/worldClocks'
import { DEFAULT_WORLD_CLOCK_ZONES } from '@/constants/worldClockPresets'

export const DEFAULT_WORLD_CLOCKS_SETTINGS: WorldClocksSettings = {
  enabled: true,
  use24h: true,
  zones: DEFAULT_WORLD_CLOCK_ZONES.map((z) => ({ ...z })),
}

const settings = ref<WorldClocksSettings | null>(null)
const tick = ref(0)
let subscribers = 0
let loadPromise: Promise<void> | null = null
let tickTimer: ReturnType<typeof setInterval> | null = null

async function loadSettings(force = false) {
  if (!force && settings.value) return
  if (loadPromise && !force) {
    await loadPromise
    return
  }
  loadPromise = (async () => {
    try {
      settings.value = await getWorldClocksSettings()
    } catch {
      settings.value = { ...DEFAULT_WORLD_CLOCKS_SETTINGS, zones: [...DEFAULT_WORLD_CLOCKS_SETTINGS.zones] }
    } finally {
      loadPromise = null
    }
  })()
  await loadPromise
}

function startTick() {
  if (tickTimer) return
  tickTimer = setInterval(() => {
    tick.value = Date.now()
  }, 1000)
}

function stopTick() {
  if (tickTimer) {
    clearInterval(tickTimer)
    tickTimer = null
  }
}

export type WorldClockDayPhase = 'day' | 'night'

/** 该时区当地小时（0–23） */
export function getLocalHourInTimeZone(tz: string, at = Date.now()): number | null {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      hour: 'numeric',
      hour12: false,
    }).formatToParts(new Date(at))
    const hour = parts.find((p) => p.type === 'hour')?.value
    if (hour == null) return null
    const n = Number.parseInt(hour, 10)
    return Number.isNaN(n) ? null : n
  } catch {
    return null
  }
}

/** 06:00–18:00 视为白天，其余为夜间 */
export function getWorldClockDayPhase(tz: string, at = Date.now()): WorldClockDayPhase {
  const hour = getLocalHourInTimeZone(tz, at)
  if (hour == null) return 'day'
  return hour >= 6 && hour < 18 ? 'day' : 'night'
}

export function formatWorldClockTime(tz: string, use24h: boolean, at = Date.now()): string {
  try {
    return new Intl.DateTimeFormat('zh-CN', {
      timeZone: tz,
      hour: '2-digit',
      minute: '2-digit',
      hour12: !use24h,
    }).format(new Date(at))
  } catch {
    return '—'
  }
}

/** 顶栏等多处共享：拉配置 + 定时刷新显示 */
export function useWorldClocks() {
  onMounted(() => {
    subscribers += 1
    void loadSettings()
    startTick()
  })

  onUnmounted(() => {
    subscribers = Math.max(0, subscribers - 1)
    if (subscribers === 0) stopTick()
  })

  return {
    settings,
    tick,
    reload: () => loadSettings(true),
  }
}

export function setWorldClocksCache(next: WorldClocksSettings) {
  settings.value = next
}
