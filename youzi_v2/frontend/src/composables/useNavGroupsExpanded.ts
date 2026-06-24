import { ref } from 'vue'

import { navGroups } from '@/constants/navigation'

const STORAGE_KEY = 'youzi.navGroupsExpanded'

const validLabels = new Set(navGroups.map((g) => g.label))

function readStored(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return {}
    const out: Record<string, boolean> = {}
    for (const [key, value] of Object.entries(parsed)) {
      if (validLabels.has(key) && typeof value === 'boolean') {
        out[key] = value
      }
    }
    return out
  } catch {
    return {}
  }
}

function writeStored(value: Record<string, boolean>) {
  try {
    const payload: Record<string, boolean> = {}
    for (const group of navGroups) {
      if (group.label in value) {
        payload[group.label] = value[group.label]!
      }
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch {
    /* ignore */
  }
}

const expandedGroups = ref<Record<string, boolean>>(readStored())

export function useNavGroupsExpanded() {
  function isGroupExpanded(label: string, hasActiveItem: boolean) {
    if (hasActiveItem) return true
    return expandedGroups.value[label] ?? false
  }

  function toggleGroup(label: string, hasActiveItem: boolean) {
    if (hasActiveItem) return
    const next = !(expandedGroups.value[label] ?? false)
    expandedGroups.value = { ...expandedGroups.value, [label]: next }
    writeStored(expandedGroups.value)
  }

  function setGroupExpanded(label: string, expanded: boolean) {
    if (!validLabels.has(label)) return
    expandedGroups.value = { ...expandedGroups.value, [label]: expanded }
    writeStored(expandedGroups.value)
  }

  return {
    expandedGroups,
    isGroupExpanded,
    toggleGroup,
    setGroupExpanded,
  }
}
