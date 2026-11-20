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
        // 菜单角标与“主要关注”Tab 使用同一份按运单合并后的计数。
        pendingShipmentSlaAlertCount.value = summary.severeOverdue ?? 0
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
