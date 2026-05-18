/** 与后端 internal_tracking.INTERNAL_WAREHOUSE_PLACEHOLDER 一致 */
export const INTERNAL_WAREHOUSE_PLACEHOLDER = 'Your goods are in the warehouse'

export function isInternalNoTrackingDesc(desc?: string | null): boolean {
  return (desc ?? '').trim() === INTERNAL_WAREHOUSE_PLACEHOLDER
}

export function hasEffectiveInternalTracking(row: {
  latestTrackingTime?: string | null
  latestTrackingDesc?: string | null
}): boolean {
  if (isInternalNoTrackingDesc(row.latestTrackingDesc)) return false
  return Boolean(row.latestTrackingTime?.trim() || row.latestTrackingDesc?.trim())
}
