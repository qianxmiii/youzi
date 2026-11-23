type CheckRow = { shipmentNo: string; kind?: string; message: string }

export function collectCtnsMismatchNos(rows: readonly CheckRow[]): string[] {
  // 即时结果和历史任务均以「没有产品」区分空产品列表与查询失败。
  const numbers = rows
    .filter(row => row.kind === 'mismatch' || (row.kind === 'error' && row.message.trim() === '没有产品'))
    .map(row => row.shipmentNo.trim())
    .filter(no => no && no !== '—')
  return [...new Set(numbers)]
}
