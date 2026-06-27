import type { TrackingSyncResult } from '@/types/tracking'

type SyncMessage = {
  success: (content: string, options?: { duration?: number }) => void
  warning: (content: string, options?: { duration?: number }) => void
  error: (content: string, options?: { duration?: number }) => void
}

export function formatTrackingMessage(res: TrackingSyncResult, label = '轨迹') {
  const unassigned =
    res.unassigned && res.unassigned > 0 ? `，未匹配 vendor ${res.unassigned} 单` : ''
  let text =
    `${label}已更新：${res.updated}/${res.total} 单（${res.batches} 批×${res.batchSize}），新增 ${res.logCount} 条` +
    (res.skipped ? `，跳过 ${res.skipped} 单` : '') +
    (res.notFound ? `，未返回/失败 ${res.notFound} 单` : '') +
    (res.empty ? `，无轨迹 ${res.empty} 单` : '') +
    (res.excludedNotInTransit ? `，已跳过不可同步 ${res.excludedNotInTransit} 单` : '') +
    unassigned
  if (res.groupAlertsCreated && res.groupAlertsCreated > 0) {
    text += `；分组提醒 +${res.groupAlertsCreated}`
  }
  if (res.errors.length) {
    const preview = res.errors.slice(0, 3).join('；')
    const more = res.errors.length > 3 ? `…等 ${res.errors.length} 条` : ''
    text += `；错误：${preview}${more}`
  }
  return text
}

export function notifyTrackingSyncResult(
  message: SyncMessage,
  res: TrackingSyncResult,
  label: string,
) {
  const content = formatTrackingMessage(res, label)
  if (res.errors.length && res.updated === 0) {
    message.error(content, { duration: 12_000 })
  } else if (res.errors.length) {
    message.warning(content, { duration: 12_000 })
  } else {
    message.success(content, { duration: 8000 })
  }
  if (res.errors.length) {
    console.warn(`sync ${label} errors:`, res.errors)
  }
  if (res.logs?.length) {
    console.info(`sync ${label} log:\n${res.logs.join('\n')}`)
  }
}
