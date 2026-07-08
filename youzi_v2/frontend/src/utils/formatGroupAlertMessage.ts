/** 分组提醒文案：收款状态中文 + 值字段拆分（用于灰底展示） */

export interface GroupAlertMessagePart {
  text: string
  highlight: boolean
}

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  UNPAID: '未付',
  PARTIAL: '部分',
  PAID: '已付',
}

export function paymentStatusLabel(code: string | null | undefined): string {
  const key = (code || '').trim().toUpperCase()
  return PAYMENT_STATUS_LABELS[key] ?? (code || '').trim()
}

/** 将消息中的英文收款状态替换为中文（兼容历史提醒） */
export function normalizeGroupAlertMessage(message: string): string {
  return message
    .replace(/\bUNPAID\b/gi, '未付')
    .replace(/\bPARTIAL\b/gi, '部分')
    .replace(/\bPAID\b/gi, '已付')
}

/** 日期、组号、运单号、数字、收款状态等「值」片段 */
const VALUE_PATTERN =
  /\d{4}-\d{2}-\d{2}|G\d[\dA-Z]*|[A-Za-z]{2,}\d[A-Za-z0-9]*|（[^）]+）|未付|部分|已付|\d+/g

export function splitGroupAlertMessage(message: string): GroupAlertMessagePart[] {
  const text = normalizeGroupAlertMessage(message.trim())
  if (!text) return [{ text: '—', highlight: false }]

  const parts: GroupAlertMessagePart[] = []
  let last = 0
  for (const match of text.matchAll(VALUE_PATTERN)) {
    const start = match.index ?? 0
    if (start > last) {
      parts.push({ text: text.slice(last, start), highlight: false })
    }
    parts.push({ text: match[0], highlight: true })
    last = start + match[0].length
  }
  if (last < text.length) {
    parts.push({ text: text.slice(last), highlight: false })
  }
  return parts.length ? parts : [{ text, highlight: false }]
}
