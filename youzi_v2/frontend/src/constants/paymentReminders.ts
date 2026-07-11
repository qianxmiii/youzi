export const SETTLEMENT_METHOD_OPTIONS = [
  { label: '发货前结', value: 'BEFORE_SHIPMENT' },
  { label: '到港前结', value: 'BEFORE_ARRIVAL' },
  { label: '到港后结', value: 'AFTER_ARRIVAL' },
  { label: '月结', value: 'MONTHLY' },
  { label: '签收结', value: 'AFTER_DELIVERY' },
] as const

export const SETTLEMENT_METHOD_FILTER_OPTIONS = [
  ...SETTLEMENT_METHOD_OPTIONS,
  { label: '未设置', value: 'UNSET' },
]

export const PAYMENT_REMINDER_SCOPE_OPTIONS = [
  { label: '待催（默认）', value: 'todo' },
  { label: '全部未付款', value: 'all_unpaid' },
  { label: '提前7天', value: 'upcoming_7_days' },
  { label: '当天提醒', value: 'today' },
  { label: '已逾期', value: 'overdue' },
  { label: '未设置结算方式', value: 'missing_rule' },
  { label: '缺少时间字段', value: 'missing_date' },
] as const

export const PAYMENT_REMINDER_TYPE_OPTIONS = [
  { label: '提前7天', value: 'upcoming_7_days' },
  { label: '当天', value: 'today' },
  { label: '已逾期', value: 'overdue' },
  { label: '月结', value: 'monthly' },
  { label: '未设置结算方式', value: 'missing_rule' },
  { label: '缺少时间字段', value: 'missing_date' },
] as const

const SETTLEMENT_LABEL: Record<string, string> = Object.fromEntries(
  SETTLEMENT_METHOD_OPTIONS.map((o) => [o.value, o.label]),
)

export function settlementMethodLabel(code: string | null | undefined): string {
  const key = (code || '').trim().toUpperCase()
  if (!key) return '未设置'
  return SETTLEMENT_LABEL[key] || key
}

const REMINDER_TYPE_LABEL: Record<string, string> = Object.fromEntries(
  PAYMENT_REMINDER_TYPE_OPTIONS.map((o) => [o.value, o.label]),
)

export function paymentReminderTypeLabel(code: string | null | undefined): string {
  const key = (code || '').trim()
  if (!key) return '—'
  return REMINDER_TYPE_LABEL[key] || key
}

export function paymentReminderDueHint(item: {
  overdueDays?: number
  daysUntilDue?: number
  reminderType?: string
}): string {
  const rt = (item.reminderType || '').trim()
  const overdue = item.overdueDays ?? 0
  if (rt === 'overdue') {
    if (overdue > 0) return `逾期 ${overdue} 天`
    return '已逾期'
  }
  const left = item.daysUntilDue ?? 0
  if (left > 0) return `剩余 ${left} 天`
  if (rt === 'today' || rt === 'monthly') return '今天'
  return '—'
}
