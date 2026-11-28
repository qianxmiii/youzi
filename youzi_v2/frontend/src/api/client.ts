import { FetchError, ofetch, type $Fetch, type FetchOptions, type FetchRequest, type ResponseType } from 'ofetch'

function userFacingRequestMessage(error: FetchError): string {
  const status = error.status
  const detail = (error.data as { detail?: unknown } | undefined)?.detail
  if (!status) {
    if (error.cause instanceof Error && error.cause.name === 'TimeoutError') return '请求超时，请稍后重试'
    if (error.cause instanceof Error && error.cause.name === 'AbortError') return '请求已取消'
    return '无法连接服务，请检查网络或服务是否已启动'
  }
  if (status >= 500) return '服务暂时无法完成请求，请稍后重试'
  if (status === 401) return '登录已失效，请重新登录'
  if (status === 403) return '没有权限执行此操作'
  if (status === 429) return '操作过于频繁，请稍后重试'
  if (typeof detail === 'string' && detail.trim()) return detail.trim()
  if (status === 404) return '找不到所请求的记录或功能'
  if (status === 409) return '操作发生冲突，请刷新后检查是否已有相同记录'
  if (status === 400 || status === 422) return '提交的信息有误，请检查后再试'
  return '请求未完成，请稍后重试'
}

function withReadableErrors(fetcher: $Fetch): $Fetch {
  const raw = async <T, R extends ResponseType = 'json'>(request: FetchRequest, options?: FetchOptions<R>) => {
    try {
      return await fetcher.raw<T, R>(request, options)
    } catch (error) {
      if (error instanceof FetchError) error.message = userFacingRequestMessage(error)
      throw error
    }
  }
  const request = async <T, R extends ResponseType = 'json'>(input: FetchRequest, options?: FetchOptions<R>) =>
    (await raw<T, R>(input, options))._data!

  return Object.assign(request, {
    raw,
    native: fetcher.native,
    create: (...args: Parameters<$Fetch['create']>) => withReadableErrors(fetcher.create(...args)),
  })
}

export const api = withReadableErrors(ofetch.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
}))

export interface HealthResponse {
  ok: boolean
  service?: string
  version?: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  return api<HealthResponse>('/api/v1/health')
}

export async function fetchLegacyHealth(): Promise<HealthResponse> {
  return api<HealthResponse>('/api/health')
}
