import { ref } from 'vue'
import { getPaymentReminderSummary } from '@/api/paymentReminders'

const pendingPaymentReminderCount = ref(0)
let inflight: Promise<void> | null = null

export function usePendingPaymentReminderCount() {
  async function refreshPendingPaymentReminderCount() {
    if (inflight) return inflight
    inflight = (async () => {
      try {
        const summary = await getPaymentReminderSummary()
        pendingPaymentReminderCount.value = summary.todoCount ?? 0
      } catch {
        /* 保留上次计数 */
      } finally {
        inflight = null
      }
    })()
    return inflight
  }

  return {
    pendingPaymentReminderCount,
    refreshPendingPaymentReminderCount,
  }
}
