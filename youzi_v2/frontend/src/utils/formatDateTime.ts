/** 将时间戳格式化为 API 使用的 YYYY-MM-DD HH:mm:ss */
export function formatTimestampForApi(ts: number): string {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

export function nowTimestamp(): number {
  return Date.now()
}
