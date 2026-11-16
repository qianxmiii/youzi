export type LinkRule = {id:string; name:string; host:string; port:number; paths:string[]}
export const defaultLinkRules: LinkRule[] = [{id:'pickup-photo', name:'提货照片', host:'pickupphoto.nextsls.com', port:30233, paths:['/photo/image','/photo/image/pack']}]
export type LinkRow = { shipmentNo: string; url: string }
export function parseLinkText(text: string): LinkRow[] {
  return text.replace(/\\:/g, ':').split(/\r?\n|\\(?=\s*(?:\r?\n|$))/).map(x => x.trim()).filter(Boolean).map(line => {
    const match = /^(\S+?)(?:\s*[=＝]\s*|\s+)(.+)$/.exec(line)
    return match ? {shipmentNo:match[1] || '', url:(match[2] || '').trim()} : {shipmentNo:line,url:''}
  })
}
export function checkLinkRow(row: LinkRow, rows: LinkRow[], rules: LinkRule[] = defaultLinkRules) {
  if (!row.shipmentNo.trim() && !row.url.trim()) return '请填写运单号和链接'
  const no = row.shipmentNo.trim()
  if (!/^[a-z0-9][a-z0-9_-]{0,79}$/i.test(no) || /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i.test(no)) return '运单号格式不正确'
  if (rows.filter(x => x.shipmentNo.trim().toLowerCase() === no.toLowerCase()).length > 1) return '运单号重复，请合并或删除'
  try {
    const url = new URL(row.url.trim().replace(/\\:/g, ':'))
    if (!['http:','https:'].includes(url.protocol) || !rules.some(rule => url.hostname === rule.host && url.port === String(rule.port) && rule.paths.includes(url.pathname)) || !url.searchParams.get('id')?.trim() || url.username || url.password || url.hash) return '暂不支持此链接'
  } catch { return '请填写有效的提货照片链接' }
  return ''
}
