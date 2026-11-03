import type { DeliveryWindow } from '@/api/deliveryWindow'
import type { Shipment } from '@/types/shipment'
import { formatShipmentDetailSummaryLine } from '@/utils/shipmentCopyFormat'

export function formatShipmentDWCopyText(row: Shipment, window: string): string {
  return `${formatShipmentDetailSummaryLine(row)}\n${window}`
}

/** Bound request concurrency and preserve selection order, regardless of response order. */
export async function prepareShipmentDWCopy(
  rows: Shipment[],
  fetchWindow: (id: string) => Promise<DeliveryWindow>,
) {
  const blocks: string[] = new Array(rows.length)
  const failures: { row: Shipment; reason: string }[] = []
  let next = 0
  async function worker() {
    while (next < rows.length) {
      const index = next++
      const row = rows[index]!
      try {
        const result = await fetchWindow(row.id)
        const risks = result.warnings.filter(text => text.includes('过期') || text.includes('运输异常'))
        if (!result.copyText || risks.length) {
          failures.push({ row, reason: risks.join('；') || result.reason || '暂无有效DW，请检查渠道时效和日期' })
        } else {
          blocks[index] = formatShipmentDWCopyText(row, result.copyText)
        }
      } catch {
        failures.push({ row, reason: 'DW读取失败，请检查后端连接后重试' })
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(4, rows.length) }, () => worker()))
  // No partial clipboard result: every selected shipment must be accounted for.
  failures.sort((a, b) => rows.indexOf(a.row) - rows.indexOf(b.row))
  return { text: failures.length ? '' : blocks.join('\n\n'), failures }
}
