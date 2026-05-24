/** 将时间戳格式化为 API 使用的 YYYY-MM-DD HH:mm:ss */
export function formatTimestampForApi(ts: number): string {
  return formatAbsoluteDateTime(new Date(ts))
}

/** 解析 API/库内时间为本地「日」0 点毫秒，供 NDatePicker type="date" */
export function dateOnlyToTimestamp(value: string | null | undefined): number | null {
  const raw = (value ?? '').trim()
  if (!raw) return null
  const head = raw.slice(0, 10)
  if (/^\d{4}-\d{2}-\d{2}$/.test(head)) {
    const [y, m, d] = head.split('-').map(Number)
    return new Date(y, m - 1, d).getTime()
  }
  const parsed = parseDateTimeInput(raw)
  if (!parsed) return null
  return new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate()).getTime()
}

/** 日期控件 → API：YYYY-MM-DD 00:00:00 */
export function formatDateOnlyForApi(ts: number): string {
  const d = new Date(ts)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} 00:00:00`
}

export function nowTimestamp(): number {
  return Date.now()
}

const pad2 = (n: number) => String(n).padStart(2, '0')

/** 解析 API / SQLite 常见时间字符串 */
export function parseDateTimeInput(value: string | null | undefined): Date | null {
  const raw = (value ?? '').trim()
  if (!raw) return null
  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T')
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return null
  return d
}

function toDate(value: string | number | Date | null | undefined): Date | null {
  if (value == null || value === '') return null
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value
  }
  if (typeof value === 'number') {
    const d = new Date(value)
    return Number.isNaN(d.getTime()) ? null : d
  }
  return parseDateTimeInput(value)
}

/** 精确到秒的绝对时间（用于 Tooltip） */
export function formatAbsoluteDateTime(value: string | number | Date | null | undefined): string {
  const d = toDate(value)
  if (!d) return ''
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
}

export interface RelativeTimeFormatted {
  /** 如「3分钟前」 */
  relative: string
  /** 如「2026-05-23 01:52:53」 */
  absolute: string
}

/**
 * 将时间转为中文相对时间；同时返回绝对时间供 Tooltip 使用。
 */
export function formatRelativeTime(
  value: string | number | Date | null | undefined,
  now: Date = new Date(),
): RelativeTimeFormatted | null {
  const d = toDate(value)
  if (!d) return null

  const absolute = formatAbsoluteDateTime(d)
  const diffMs = now.getTime() - d.getTime()

  if (diffMs < 0) return { relative: '刚刚', absolute }

  const sec = Math.floor(diffMs / 1000)
  if (sec < 60) return { relative: '刚刚', absolute }

  const min = Math.floor(sec / 60)
  if (min < 60) return { relative: `${min}分钟前`, absolute }

  const hour = Math.floor(min / 60)
  if (hour < 24) return { relative: `${hour}小时前`, absolute }

  const day = Math.floor(hour / 24)
  return { relative: `${day}天前`, absolute }
}
