import { ref } from 'vue'
import type { RouteLocationNormalizedLoaded, Router } from 'vue-router'

export interface PageTab {
  key: string
  path: string
  fullPath: string
  title: string
}

const STORAGE_KEY = 'youzi.pageTabs'
const MAX_TABS = 20

function defaultTabs(): PageTab[] {
  return [
    {
      key: '/',
      path: '/',
      fullPath: '/',
      title: '工作台',
    },
  ]
}

function readStored(): { tabs: PageTab[]; activeKey: string } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      const tabs = defaultTabs()
      return { tabs, activeKey: tabs[0].key }
    }
    const parsed = JSON.parse(raw) as { tabs?: PageTab[]; activeKey?: string }
    const tabs = (parsed.tabs ?? [])
      .filter(
        (t) =>
          t &&
          typeof t.key === 'string' &&
          typeof t.fullPath === 'string' &&
          typeof t.title === 'string',
      )
      .slice(0, MAX_TABS)
    if (!tabs.length) {
      const fallback = defaultTabs()
      return { tabs: fallback, activeKey: fallback[0].key }
    }
    const activeKey =
      parsed.activeKey && tabs.some((t) => t.key === parsed.activeKey)
        ? parsed.activeKey
        : tabs[0].key
    return { tabs, activeKey }
  } catch {
    const tabs = defaultTabs()
    return { tabs, activeKey: tabs[0].key }
  }
}

function writeStored(tabs: PageTab[], activeKey: string) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        tabs: tabs.slice(0, MAX_TABS),
        activeKey,
      }),
    )
  } catch {
    /* ignore */
  }
}

const stored = readStored()
const tabs = ref<PageTab[]>(stored.tabs)
const activeKey = ref(stored.activeKey)

function tabTitle(route: RouteLocationNormalizedLoaded): string {
  return (route.meta.title as string | undefined)?.trim() || route.path || '页面'
}

function openFromRoute(route: RouteLocationNormalizedLoaded) {
  const key = route.fullPath
  const title = tabTitle(route)
  const existing = tabs.value.find((t) => t.key === key)
  if (!existing) {
    tabs.value = [
      ...tabs.value,
      {
        key,
        path: route.path,
        fullPath: route.fullPath,
        title,
      },
    ].slice(-MAX_TABS)
  } else if (existing.title !== title) {
    existing.title = title
  }
  activeKey.value = key
  writeStored(tabs.value, activeKey.value)
}

function activateTab(key: string, router: Router) {
  const tab = tabs.value.find((t) => t.key === key)
  if (!tab) return
  activeKey.value = key
  writeStored(tabs.value, activeKey.value)
  if (router.currentRoute.value.fullPath !== tab.fullPath) {
    void router.push(tab.fullPath)
  }
}

function closeTab(key: string, router: Router) {
  const idx = tabs.value.findIndex((t) => t.key === key)
  if (idx < 0) return

  const wasActive = activeKey.value === key
  const nextTabs = tabs.value.filter((t) => t.key !== key)

  if (!nextTabs.length) {
    const home = defaultTabs()[0]
    tabs.value = [home]
    activeKey.value = home.key
    writeStored(tabs.value, activeKey.value)
    if (router.currentRoute.value.fullPath !== home.fullPath) {
      void router.push(home.fullPath)
    }
    return
  }

  tabs.value = nextTabs
  if (wasActive) {
    const next = nextTabs[Math.min(idx, nextTabs.length - 1)]
    activeKey.value = next.key
    writeStored(tabs.value, activeKey.value)
    if (router.currentRoute.value.fullPath !== next.fullPath) {
      void router.push(next.fullPath)
    }
  } else {
    writeStored(tabs.value, activeKey.value)
  }
}

function closeOthers(key: string, router: Router) {
  const tab = tabs.value.find((t) => t.key === key)
  if (!tab) return
  tabs.value = [tab]
  activeKey.value = key
  writeStored(tabs.value, activeKey.value)
  if (router.currentRoute.value.fullPath !== tab.fullPath) {
    void router.push(tab.fullPath)
  }
}

function closeAll(router: Router) {
  const home = defaultTabs()[0]
  tabs.value = [home]
  activeKey.value = home.key
  writeStored(tabs.value, activeKey.value)
  if (router.currentRoute.value.fullPath !== home.fullPath) {
    void router.push(home.fullPath)
  }
}

export function usePageTabs() {
  return {
    tabs,
    activeKey,
    openFromRoute,
    activateTab,
    closeTab,
    closeOthers,
    closeAll,
  }
}
