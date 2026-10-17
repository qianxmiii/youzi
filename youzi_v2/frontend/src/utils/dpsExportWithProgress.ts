import { api } from '@/api/client'
import { parseDownloadFilename, readBlobApiError } from '@/api/shipments'

export type DpsExportJobType =
  | 'cargo'
  | 'mark'
  | 'markSplit'
  | 'packinglist'
  | 'warehouseform'
  | 'warehouseEntry'
  | 'warehouseEntryPdf'

export interface DpsExportJobStatus {
  id: string
  status: string
  progress: number
  message: string
  filename?: string | null
  done: boolean
  failed: boolean
  error?: string | null
}

const POLL_MS = 450

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function runDpsExportJob(
  exportType: DpsExportJobType,
  shipmentIds: string[],
  options: {
    splitSpec?: string
    onProgress: (status: DpsExportJobStatus) => void
  },
): Promise<{ blob: Blob; filename: string }> {
  const { jobId } = await api<{ jobId: string }>('/api/v1/shipments/dps-export-jobs', {
    method: 'POST',
    body: {
      exportType,
      ids: shipmentIds,
      ...(options.splitSpec?.trim() ? { splitSpec: options.splitSpec.trim() } : {}),
    },
  })

  for (;;) {
    const status = await api<DpsExportJobStatus>(
      `/api/v1/shipments/dps-export-jobs/${encodeURIComponent(jobId)}`,
    )
    options.onProgress(status)
    if (status.failed) {
      throw new Error(status.error?.trim() || status.message || '导出失败')
    }
    if (status.done) {
      try {
        const response = await api.raw<Blob, 'blob'>(
          `/api/v1/shipments/dps-export-jobs/${encodeURIComponent(jobId)}/download`,
          {
            method: 'GET',
            responseType: 'blob',
            timeout: 600_000,
          },
        )
        const blob = response._data as Blob
        const filename =
          parseDownloadFilename(response.headers.get('content-disposition')) ||
          status.filename ||
          'download.bin'
        options.onProgress({ ...status, progress: 100, message: '下载完成' })
        return { blob, filename }
      } catch (e) {
        return readBlobApiError(e, '下载导出文件失败')
      }
    }
    await sleep(POLL_MS)
  }
}

export const DPS_EXPORT_TITLES: Record<DpsExportJobType, string> = {
  cargo: '货箱数据',
  mark: '唛头',
  markSplit: '唛头（拆分）',
  packinglist: '箱单发票',
  warehouseform: '排仓单',
  warehouseEntry: '进仓单',
  warehouseEntryPdf: '进仓单（PDF）',
}
