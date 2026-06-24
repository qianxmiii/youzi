/** 自动编号旧格式 G20YYMMDDnnn → 展示为 GYYMMDDnnn */
export function formatGroupNoDisplay(groupNo: string | null | undefined): string {
  const s = (groupNo ?? '').trim()
  if (!s) return ''
  const m = /^G20(\d{9})$/.exec(s)
  return m ? `G${m[1]}` : s
}
