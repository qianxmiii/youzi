/** 挂靠港展示：优先用码表解析结果，否则显示船公司原始名 */

export interface PortCallLike {
  portName: string
  portCode?: string | null
  portCnname?: string | null
  portNameEn?: string | null
}

export function formatPortDisplay(pc: PortCallLike): string {
  const raw = (pc.portName || '').trim()
  const cn = (pc.portCnname || '').trim()
  const en = (pc.portNameEn || '').trim()
  const code = (pc.portCode || '').trim()
  const parts: string[] = []
  if (cn) parts.push(cn)
  if (en) parts.push(en)
  else if (raw && raw !== cn) parts.push(raw)
  if (code) parts.push(code)
  if (parts.length) return parts.join(' · ')
  return raw || '—'
}
