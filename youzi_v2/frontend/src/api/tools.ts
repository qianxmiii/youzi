import { api } from '@/api/client'

export type ImageZipJobStatus = 'pending' | 'running' | 'done' | 'failed'

export type ImageZipJob = {
  jobId: string
  status: ImageZipJobStatus
  total: number
  done: number
  failed: number
  downloaded: number
  error?: string | null
  column: string
  ready: boolean
}

export type ImageLinkZipResult = {
  blob: Blob
  filename: string
  total: number
  downloaded: number
  failed: number
}

function parseFilename(disposition: string | null): string {
  if (!disposition) return '标签图片.zip'
  const star = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1])
    } catch {
      return star[1]
    }
  }
  const plain = disposition.match(/filename="?([^";]+)"?/i)
  return plain?.[1] || '标签图片.zip'
}

async function readFetchError(e: unknown): Promise<never> {
  const err = e as { data?: Blob | { detail?: string }; message?: string }
  if (err?.data instanceof Blob) {
    const text = await err.data.text().catch(() => '')
    try {
      const parsed = JSON.parse(text) as { detail?: unknown }
      if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
        throw new Error(parsed.detail)
      }
    } catch (inner) {
      if (!(inner instanceof SyntaxError)) throw inner
    }
  } else if (err?.data && typeof err.data === 'object' && 'detail' in err.data) {
    const detail = (err.data as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) throw new Error(detail)
  }
  throw e instanceof Error ? e : new Error(err?.message || '请求失败')
}

/** 创建后台下载任务 */
export async function startImageLinkZipJob(file: File, column = 'P'): Promise<ImageZipJob> {
  const form = new FormData()
  form.append('file', file)
  try {
    return await api<ImageZipJob>('/api/v1/tools/image-link-zip/jobs', {
      method: 'POST',
      body: form,
      query: { column },
      timeout: 60_000,
    })
  } catch (e) {
    return readFetchError(e)
  }
}

export async function getImageLinkZipJob(jobId: string): Promise<ImageZipJob> {
  try {
    return await api<ImageZipJob>(`/api/v1/tools/image-link-zip/jobs/${encodeURIComponent(jobId)}`)
  } catch (e) {
    return readFetchError(e)
  }
}

export async function downloadImageLinkZipJob(jobId: string): Promise<ImageLinkZipResult> {
  try {
    const response = await api.raw<Blob>(
      `/api/v1/tools/image-link-zip/jobs/${encodeURIComponent(jobId)}/download`,
      {
        responseType: 'blob',
        timeout: 120_000,
      },
    )
    const headers = response.headers
    return {
      blob: response._data as Blob,
      filename: parseFilename(headers.get('content-disposition')),
      total: Number(headers.get('x-image-zip-total') || 0),
      downloaded: Number(headers.get('x-image-zip-downloaded') || 0),
      failed: Number(headers.get('x-image-zip-failed') || 0),
    }
  } catch (e) {
    return readFetchError(e)
  }
}

/** 上传 → 轮询进度 → 下载 zip */
export async function exportImageLinkZip(
  file: File,
  column = 'P',
  onProgress?: (job: ImageZipJob) => void,
): Promise<ImageLinkZipResult> {
  let job = await startImageLinkZipJob(file, column)
  onProgress?.(job)

  const started = Date.now()
  const maxWaitMs = 30 * 60 * 1000
  while (job.status === 'pending' || job.status === 'running') {
    if (Date.now() - started > maxWaitMs) {
      throw new Error('等待超时（超过 30 分钟），请稍后重试')
    }
    await new Promise((r) => setTimeout(r, 800))
    job = await getImageLinkZipJob(job.jobId)
    onProgress?.(job)
  }

  if (job.status === 'failed') {
    throw new Error(job.error || '打包失败')
  }

  return downloadImageLinkZipJob(job.jobId)
}
