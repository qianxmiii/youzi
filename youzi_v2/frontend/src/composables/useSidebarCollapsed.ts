import { ref } from 'vue'

const STORAGE_KEY = 'youzi.sidebarCollapsed'

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function writeStored(value: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, value ? '1' : '0')
  } catch {
    /* ignore */
  }
}

const collapsed = ref(readStored())

export function useSidebarCollapsed() {
  function toggle() {
    collapsed.value = !collapsed.value
    writeStored(collapsed.value)
  }

  function setCollapsed(value: boolean) {
    collapsed.value = value
    writeStored(value)
  }

  return { collapsed, toggle, setCollapsed }
}
