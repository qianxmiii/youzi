/** 解析 FastAPI / ofetch 错误体中的 detail 文案。 */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object') {
    const data = (error as { data?: unknown }).data
    if (data && typeof data === 'object') {
      const detail = (data as { detail?: unknown }).detail
      if (typeof detail === 'string' && detail.trim()) {
        return detail
      }
      if (Array.isArray(detail) && detail.length) {
        const first = detail[0] as { msg?: string; loc?: unknown[] }
        if (first?.msg) {
          const loc = Array.isArray(first.loc) ? first.loc.join('.') : ''
          return loc ? `${loc}: ${first.msg}` : first.msg
        }
      }
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return fallback
}
