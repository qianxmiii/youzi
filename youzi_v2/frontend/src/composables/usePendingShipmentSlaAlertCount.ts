import { ref } from 'vue'
import { getShipmentSlaSummary } from '@/api/shipmentSla'

const pendingShipmentSlaAlertCount = ref(0)
let inflight: Promise<void> | null = null

export function usePendingShipmentSlaAlertCount() {
  async function refreshPendingShipmentSlaAlertCount() {
    if (inflight) return inflight
    inflight = (async () => {
      try {
        const summary = await getShipmentSlaSummary()
        pendingShipmentSlaAlertCount.value = summary.pendingOpen ?? 0
      } catch {
        /* 保留上次计数 */
      } finally {
        inflight = null
      }
    })()
    return inflight
  }

  return {
    pendingShipmentSlaAlertCount,
    refreshPendingShipmentSlaAlertCount,
  }
}
