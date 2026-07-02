export type TrackingTimeReviewAction =
  | 'use_expected_delivery'
  | 'use_signed_track'
  | 'manual'
  | 'reject'
  | 'approve'

export interface TrackingTimeCandidate {
  id: string
  shipmentId: string
  fieldName: string
  /** 推荐写入正式字段的时间（冲突时为预计送仓） */
  candidateValue: string
  /** 对照时间（冲突时为签收节点事件时间） */
  compareValue: string
  recommendedSource: string
  compareSource: string
  sourceTrackId: string
  sourceTrackTime: string
  sourceTrackDesc: string
  compareSourceTrackId: string
  compareSourceTrackTime: string
  compareSourceTrackDesc: string
  confidence: string
  reviewStatus: 'auto_confirmed' | 'pending_review' | 'manual_approved' | 'manual_rejected'
  reviewReason: string
  applied: boolean
  createdTime: string
  updatedTime: string
  shipmentNo?: string
  carrierCode?: string | null
  carrierNameZh?: string | null
  expectedDeliveryTime?: string | null
  deliveredTime?: string | null
}

export interface TrackingTimeRecalculateResult {
  found: boolean
  shipmentId?: string
  shipmentNo?: string
  applied: string[]
  pendingReview: string[]
}

export function formatSignedTimeReviewQuestion(candidateValue: string): string {
  const date = (candidateValue || '').trim().slice(0, 10)
  return date
    ? `是否采用预计送仓时间 ${date} 作为签收时间？`
    : '是否采用预计送仓时间作为签收时间？'
}
