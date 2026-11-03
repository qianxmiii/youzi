export const QUOTE_STATUS_OPTIONS = [
  { label: '已报价', value: 'QUOTED' },
  { label: '跟进中', value: 'FOLLOWING' },
  { label: '已成单', value: 'WON' },
  { label: '已丢单', value: 'LOST' },
  { label: '已过期', value: 'EXPIRED' },
  { label: '已取消', value: 'CANCELLED' },
] as const

export const QUOTE_SCOPE_OPTIONS = [
  { label: '待办（默认）', value: 'todo' },
  { label: '今日待跟进', value: 'today' },
  { label: '逾期未跟进', value: 'overdue_followup' },
  { label: '即将过期', value: 'expiring_soon' },
  { label: '已过有效期', value: 'expired' },
  { label: '全部进行中', value: 'all_active' },
  { label: '已成单', value: 'won' },
  { label: '已丢单', value: 'lost' },
  { label: '已取消', value: 'cancelled' },
] as const

export const QUOTE_CHANGE_REASON_OPTIONS = [
  { label: '降价', value: 'PRICE_DOWN' },
  { label: '涨价', value: 'PRICE_UP' },
  { label: '修改货物', value: 'CARGO_CHANGE' },
  { label: '修改地址', value: 'ADDRESS_CHANGE' },
  { label: '修改渠道', value: 'CHANNEL_CHANGE' },
  { label: '其他', value: 'OTHER' },
] as const

export const QUOTE_FOLLOWUP_TYPE_OPTIONS = [
  { label: '电话', value: 'phone' },
  { label: '微信', value: 'wechat' },
  { label: '邮件', value: 'email' },
  { label: '其他', value: 'other' },
] as const

export const QUOTE_CURRENCY_OPTIONS = [
  { label: 'USD', value: 'USD' },
  { label: 'CNY', value: 'CNY' },
  { label: 'EUR', value: 'EUR' },
] as const

export const QUOTE_LOST_REASON_OPTIONS = [
  { label: '价格高', value: '价格高' },
  { label: '时效不合适', value: '时效不合适' },
  { label: '客户取消', value: '客户取消' },
  { label: '竞争对手成交', value: '竞争对手成交' },
  { label: '客户暂无需求', value: '客户暂无需求' },
  { label: '其他', value: '其他' },
] as const

const STATUS_LABEL: Record<string, string> = Object.fromEntries(
  QUOTE_STATUS_OPTIONS.map((o) => [o.value, o.label]),
)

const CHANGE_LABEL: Record<string, string> = {
  INITIAL: '初次报价',
  ...Object.fromEntries(QUOTE_CHANGE_REASON_OPTIONS.map((o) => [o.value, o.label])),
}

export function quoteStatusLabel(code: string | null | undefined): string {
  const key = (code || '').trim().toUpperCase()
  return STATUS_LABEL[key] || key || '—'
}

export function quoteChangeReasonLabel(code: string | null | undefined): string {
  const key = (code || '').trim().toUpperCase()
  return CHANGE_LABEL[key] || key || '—'
}

export function moneyUnitLabel(currency: string | null | undefined): string {
  const code = (currency || '').trim().toUpperCase()
  if (code === 'USD') return 'usd'
  if (code === 'CNY' || code === 'RMB') return 'rmb'
  return code.toLowerCase()
}

export function priceUnitLabel(
  currency: string | null | undefined,
  basis: string | null | undefined,
): string {
  const money = moneyUnitLabel(currency)
  const unit = (basis || '').trim().toLowerCase()
  if (money && unit) return `${money}/${unit}`
  return money || unit
}

export const DEFAULT_USD_CNY_RATE = 6.7

export function quoteSellingTotal(
  lines: Array<{ quotedAmount?: number | null; quotedCurrency?: string }>,
): { amount: number; currency: string } | null {
  const buckets = new Map<string, { amount: number; count: number }>()
  for (const line of lines) {
    if (line.quotedAmount == null || Number.isNaN(Number(line.quotedAmount))) continue
    const currency = (line.quotedCurrency || '').trim().toUpperCase() === 'RMB'
      ? 'CNY'
      : (line.quotedCurrency || '').trim().toUpperCase()
    const bucket = buckets.get(currency) || { amount: 0, count: 0 }
    bucket.amount += Number(line.quotedAmount)
    bucket.count += 1
    buckets.set(currency, bucket)
  }
  if (!buckets.size) return null
  const [currency, bucket] = [...buckets.entries()].sort(
    (left, right) => right[1].count - left[1].count || Math.abs(right[1].amount) - Math.abs(left[1].amount),
  )[0]
  return { amount: bucket.amount, currency }
}

export function quoteProfitMoney(
  rate: number | null | undefined,
  profitUnit: string | null | undefined,
  lines: Array<{ chargeWeightKg: number | null; priceBasis?: string }>,
  sellingCurrency: string | null | undefined,
  exchangeRate: number | null | undefined,
): { amount: number; currency: string } | null {
  const total = quoteProfitTotal(rate, profitUnit, lines)
  if (total == null) return null
  const currency = (sellingCurrency || '').trim().toUpperCase() === 'RMB'
    ? 'CNY'
    : (sellingCurrency || '').trim().toUpperCase()
  if (currency === 'USD') {
    const rateValue = exchangeRate != null && exchangeRate > 0 ? exchangeRate : DEFAULT_USD_CNY_RATE
    return { amount: total / rateValue, currency: 'USD' }
  }
  return { amount: total, currency: 'CNY' }
}

export function quoteProfitRate(
  profitAmount: number | null | undefined,
  profitCurrency: string | null | undefined,
  sellingAmount: number | null | undefined,
  sellingCurrency: string | null | undefined,
): number | null {
  if (profitAmount == null || sellingAmount == null || sellingAmount === 0) return null
  const profitCode = (profitCurrency || '').trim().toUpperCase() === 'RMB' ? 'CNY' : (profitCurrency || '').trim().toUpperCase()
  const sellingCode = (sellingCurrency || '').trim().toUpperCase() === 'RMB' ? 'CNY' : (sellingCurrency || '').trim().toUpperCase()
  if (!profitCode || profitCode !== sellingCode) return null
  return Math.round((profitAmount / sellingAmount) * 10000) / 100
}

export function quoteProfitTotal(
  rate: number | null | undefined,
  profitUnit: string | null | undefined,
  lines: Array<{ chargeWeightKg: number | null; priceBasis?: string }>,
): number | null {
  if (rate == null || Number.isNaN(Number(rate))) return null
  const unit = (profitUnit || '').trim().toUpperCase()
  if (unit !== 'RMB/KG' && unit !== 'RMB/CBM') return null
  const want = unit.endsWith('CBM') ? 'cbm' : 'kg'
  const matched: number[] = []
  const every: number[] = []
  for (const line of lines) {
    if (line.chargeWeightKg == null || Number.isNaN(Number(line.chargeWeightKg))) continue
    const qty = Number(line.chargeWeightKg)
    every.push(qty)
    const basis = (line.priceBasis || '').trim().toLowerCase()
    if (!basis || basis === want) matched.push(qty)
  }
  const chosen = matched.length ? matched : every
  if (!chosen.length) return null
  return Number(rate) * chosen.reduce((sum, qty) => sum + qty, 0)
}

export function formatMoney(
  amount: number | null | undefined,
  currency: string | null | undefined,
): string {
  if (amount == null || Number.isNaN(Number(amount))) return '—'
  const cur = (currency || '').trim().toUpperCase()
  const n = Number(amount)
  const text = Number.isInteger(n) ? String(n) : n.toFixed(2)
  return cur ? `${text} ${cur}` : text
}

export function formatProfitRate(rate: number | null | undefined): string {
  if (rate == null || Number.isNaN(Number(rate))) return '—'
  return `${Number(rate)}%`
}
