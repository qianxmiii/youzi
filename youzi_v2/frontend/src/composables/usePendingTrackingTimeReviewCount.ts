import { ref } from 'vue'
import { getTrackingFreshnessStats } from '@/api/shipments'

const pendingTrackingTimeReviewCount = ref(0)
let inflight: Promise<void> | null = null

export function usePendingTrackingTimeReviewCount() {
  async function refreshPendingTrackingTimeReviewCount() {
    if (inflight) return inflight
    inflight = (async () => {
      try {
        const stats = await getTrackingFreshnessStats()
        pendingTrackingTimeReviewCount.value = stats.pendingTrackingTimeReview ?? 0
      } catch {
        /* 保留上次计数 */
      } finally {
        inflight = null
      }
    })()
    return inflight
  }

  return {
    pendingTrackingTimeReviewCount,
    refreshPendingTrackingTimeReviewCount,
  }
}
