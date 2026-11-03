import { Decimal } from '@/domain/costCalculation/decimal'
import { calcChargeVolume, calcChargeWeight, calcVolumeRatio } from '@/domain/costCalculation/chargeVolume'

export interface QuickQuoteInput {
  channel: string
  country: string
  origin: string
  customer: string
  product: string
  address: string
  postcode: string
  quantity: number
  weight: number
  volume: number
  cost: number
  profit: number
  extraFee: number
}

export const emptyQuote = (): QuickQuoteInput => ({
  channel: 'Sea truck', country: '美国', origin: '', customer: '', product: '', address: '',
  postcode: '', quantity: 0, weight: 0, volume: 0, cost: 0, profit: 0, extraFee: 0,
})

export const DEFAULT_EXCHANGE_RATE = 6.7

export function calculateQuickQuote(input: QuickQuoteInput, exchangeRate = DEFAULT_EXCHANGE_RATE) {
  if (!Number.isFinite(exchangeRate) || exchangeRate <= 0) throw new Error('汇率须为大于0的数字（1 USD = 多少 RMB）')
  const invalid = Object.entries(input).filter(([, value]) => typeof value === 'number' && (!Number.isFinite(value) || value < 0))
  if (invalid.length || !Number.isInteger(input.quantity)) throw new Error('箱数须为非负整数，重量、体积和金额须为非负数字')
  let chargeWeight = calcChargeWeight(input.weight, input.volume)
  // Same basic express minimum as the original page; no unseen surcharges or split-volume rules.
  if (input.channel.toLowerCase().includes('express')) {
    const perBox = input.channel === 'Air express' ? 10 : 12
    chargeWeight = Decimal.max(chargeWeight, new Decimal(input.quantity).mul(perBox))
  }
  const unitMargin = new Decimal(input.profit).add(input.extraFee)
  const unitPrice = new Decimal(input.cost).add(unitMargin)
  const total = unitPrice.mul(chargeWeight)
  return {
    chargeWeight: chargeWeight.toFixed(0),
    chargeVolume: calcChargeVolume(input.weight, input.volume, '363').toFixed(2),
    volumeRatio: calcVolumeRatio(input.weight, input.volume).toFixed(0),
    margin: unitPrice.isZero() ? '0%' : unitMargin.div(unitPrice).mul(100).ceil().toFixed(0) + '%',
    unitPrice: unitPrice.toFixed(2),
    totalUnitPrice: unitPrice.toFixed(2),
    total: total.toFixed(2),
    unitPriceUsd: unitPrice.div(exchangeRate).toFixed(2),
  }
}

export const quoteFields = [
  { key: 'channel', label: '运输方式', type: 'channel' },
  { key: 'country', label: '国家', type: 'text' },
  { key: 'origin', label: '发货地', type: 'text' },
  { key: 'customer', label: '客户', type: 'text' },
  { key: 'product', label: '品名', type: 'text' },
  { key: 'address', label: '地址／仓码', type: 'text' },
  { key: 'postcode', label: '邮编', type: 'text' },
  { key: 'quantity', label: '箱数', type: 'number' },
  { key: 'weight', label: '总实重 kg', type: 'number' },
  { key: 'volume', label: '总体积 cbm', type: 'number' },
  { key: 'chargeWeight', label: '计费重 kg', type: 'result' },
  { key: 'chargeVolume', label: '计费方 cbm', type: 'result' },
  { key: 'volumeRatio', label: '泡比 kg/cbm', type: 'result' },
  { key: 'cost', label: '成本 RMB/kg', type: 'number', private: true },
  { key: 'profit', label: '利润 RMB/kg', type: 'number', private: true },
  { key: 'extraFee', label: '附加费 RMB/kg', type: 'number' },
  { key: 'margin', label: '毛利率', type: 'result', private: true },
  { key: 'unitPrice', label: '单价 RMB/kg', type: 'result' },
  { key: 'unitPriceUsd', label: '单价 USD/kg', type: 'result' },
  { key: 'totalUnitPrice', label: '综合单价 RMB/kg', type: 'result' },
  { key: 'total', label: '总报价 RMB', type: 'result' },
] as const
export type QuoteFieldKey = typeof quoteFields[number]['key']
export const defaultVisibleFields: QuoteFieldKey[] = ['channel', 'country', 'address', 'quantity', 'weight', 'volume', 'chargeWeight', 'chargeVolume', 'volumeRatio', 'cost', 'profit', 'unitPrice', 'totalUnitPrice', 'unitPriceUsd']

export function restoreVisibleFields(saved: readonly string[], layoutVersion = 0): QuoteFieldKey[] {
  const keys = new Set(saved)
  // Show the newly requested USD card once for existing RMB-price users. Later hides persist.
  if (layoutVersion < 1 && keys.has('unitPrice')) keys.add('unitPriceUsd')
  return quoteFields.filter(field => keys.has(field.key)).map(field => field.key)
}

export function publicQuoteText(input: QuickQuoteInput, exchangeRate = DEFAULT_EXCHANGE_RATE) {
  const result = calculateQuickQuote(input, exchangeRate)
  const cargo = [
    input.quantity > 0 ? `${input.quantity}ctns` : '',
    input.weight > 0 ? `${new Decimal(input.weight).toFixed()}kg` : '',
    input.volume > 0 ? `${new Decimal(input.volume).toFixed()}cbm` : '',
  ].filter(Boolean).join(' ')
  const address = input.address.trim().replace(/\s+/g, ' ')
  const summary = [address ? `To ${address}` : '', cargo].filter(Boolean).join(address && cargo ? ',' : '')
  const channel = input.channel.trim().replace(/^DDP\s+/i, '').replace(/\s+/g, ' ')
  let quote = `${['DDP', channel].filter(Boolean).join(' ')}: ${result.unitPriceUsd} usd/kg`
  if (new Decimal(result.chargeWeight).greaterThan(0)) {
    // Match the quoted two-decimal USD unit price so the copied equation balances.
    const totalUsd = new Decimal(result.unitPriceUsd).mul(result.chargeWeight).toFixed(2)
    quote += ` * ${result.chargeWeight}kg = ${totalUsd}usd`
  }
  return [summary, quote].filter(Boolean).join('\n')
}

export function singleResultCopyText(key: QuoteFieldKey, result: ReturnType<typeof calculateQuickQuote>): string | null {
  if (key === 'margin') return result.margin
  if (key === 'unitPrice') return `${new Decimal(result.unitPrice).toFixed()}RMB/kg`
  if (key === 'unitPriceUsd') return `${result.unitPriceUsd}usd/kg`
  return null
}
