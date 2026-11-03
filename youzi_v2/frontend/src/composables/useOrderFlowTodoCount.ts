import { ref } from 'vue'
import { getOrderFlowSummary } from '@/api/orderFlow'

const orderFlowTodoCount = ref(0)
let inflight: Promise<void> | null = null

export function useOrderFlowTodoCount() {
  async function refreshOrderFlowTodoCount() {
    if (inflight) return inflight
    inflight = (async () => {
      try {
        const summary = await getOrderFlowSummary()
        orderFlowTodoCount.value = summary.mineCount ?? 0
      } catch {
        /* 保留上次计数 */
      } finally {
        inflight = null
      }
    })()
    return inflight
  }

  return { orderFlowTodoCount, refreshOrderFlowTodoCount }
}
