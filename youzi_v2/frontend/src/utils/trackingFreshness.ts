/** 轨迹新鲜度（自然日：今日 / 三日内含今日 / 更早 / 无） */

import { hasEffectiveInternalTracking } from '@/utils/internalTracking'

export type TrackingFreshnessBucket = 'today' | 'within3d' | 'older' | 'none'

export type TrackingFreshnessLevel = TrackingFreshnessBucket

export interface TrackingFreshnessCounts {
  today: number
  within3d: number
  older: number
  none: number
}

export interface TrackingFreshnessStats {
  internal: TrackingFreshnessCounts
  carrier: TrackingFreshnessCounts
  carrierAheadOfInternal: number
}

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

export function parseTrackingDateTime(time: string | null | undefined): number | null {
  const raw = (time ?? '').trim()
  if (!raw) return null
  const t = new Date(raw.replace(' ', 'T'))
  if (Number.isNaN(t.getTime())) return null
  return t.getTime()
}

function parseTrackingDate(time: string | null | undefined): Date | null {
  const ms = parseTrackingDateTime(time)
  if (ms == null) return null
  return startOfLocalDay(new Date(ms))
}

/** 承新于内：双方均有有效内部轨迹时，承运须晚于内部至少该毫秒数 */
export const CARRIER_AHEAD_MIN_MS = 60_000

/** 承运商最新节点时间晚于内部（或内部无有效轨迹但承运有） */
export function isCarrierTrackingNewerThanInternal(row: {
  latestTrackingTime?: string | null
  latestTrackingDesc?: string | null
  latestCarrierTime?: string | null
}): boolean {
  const carrierMs = parseTrackingDateTime(row.latestCarrierTime)
  if (carrierMs == null) return false
  if (!hasEffectiveInternalTracking(row)) return true
  const internalMs = parseTrackingDateTime(row.latestTrackingTime)
  if (internalMs == null) return true
  return carrierMs - internalMs > CARRIER_AHEAD_MIN_MS
}

/** 按最新节点时间计算档位（与后端 date('now','localtime') 对齐，用浏览器本地日） */
export function trackingFreshnessLevel(
  time: string | null | undefined,
  effective: boolean,
): TrackingFreshnessLevel {
  if (!effective) return 'none'
  const nodeDay = parseTrackingDate(time)
  if (!nodeDay) return 'none'
  const today = startOfLocalDay(new Date())
  const threeDayStart = new Date(today)
  threeDayStart.setDate(threeDayStart.getDate() - 2)
  if (nodeDay.getTime() === today.getTime()) return 'today'
  if (nodeDay.getTime() >= threeDayStart.getTime()) return 'within3d'
  return 'older'
}

export const FRESHNESS_DOT_CLASS: Record<TrackingFreshnessLevel, string> = {
  today: 'bg-emerald-400',
  within3d: 'bg-amber-400/90',
  older: 'bg-zinc-600',
  none: 'bg-zinc-700/80',
}

export const FRESHNESS_LABEL: Record<TrackingFreshnessBucket, string> = {
  today: '今日',
  within3d: '三日内',
  older: '超过3天',
  none: '无轨迹',
}

/**
 * 内部轨迹距今天数（本地自然日：今日=0；节点日晚于今日时按 0 计）。
 * 与 trackingFreshnessLevel / 后端 date('now','localtime') 口径一致。
 */
export function daysSinceLocalCalendar(time: string | null | undefined): number | null {
  const nodeDay = parseTrackingDate(time)
  if (!nodeDay) return null
  const today = startOfLocalDay(new Date())
  const days = Math.floor((today.getTime() - nodeDay.getTime()) / 86_400_000)
  return Math.max(0, days)
}
