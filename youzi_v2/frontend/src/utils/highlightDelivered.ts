export interface TextHighlightPart {
  text: string
  highlight: boolean
}

const DELIVERED_RE = /delivered/gi

/** 将文案按 delivered（不区分大小写）拆成普通/高亮片段，用于首页轨迹通知等。 */
export function splitDeliveredHighlight(text: string | null | undefined): TextHighlightPart[] {
  const raw = (text ?? '').trim()
  if (!raw) return [{ text: '—', highlight: false }]

  const parts: TextHighlightPart[] = []
  let last = 0
  for (const match of raw.matchAll(DELIVERED_RE)) {
    const start = match.index ?? 0
    if (start > last) {
      parts.push({ text: raw.slice(last, start), highlight: false })
    }
    parts.push({ text: match[0], highlight: true })
    last = start + match[0].length
  }
  if (last < raw.length) {
    parts.push({ text: raw.slice(last), highlight: false })
  }
  if (!parts.length) {
    parts.push({ text: raw, highlight: false })
  }
  return parts
}

export function hasDeliveredKeyword(text: string | null | undefined): boolean {
  if (!text) return false
  return DELIVERED_RE.test(text)
}
