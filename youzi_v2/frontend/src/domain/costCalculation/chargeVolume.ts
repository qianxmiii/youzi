import type { WeightRatio } from '@/constants/costCalculation'
import { Decimal, num } from './decimal'

/** 计费方：实际方或 max(体积, ceil2(实重/重量比)) */
export function calcChargeVolume(
  weight: number,
  volume: number,
  weightRatio: WeightRatio,
): Decimal {
  const w = num(weight)
  const v = num(volume)
  if (weightRatio === 'actual') return v
  const ratio = num(weightRatio)
  const weightVolume = w.dividedBy(ratio).toDecimalPlaces(2, Decimal.ROUND_UP)
  return Decimal.max(v, weightVolume)
}

/** 泡比 = 实重 / 体积；体积或实重为 0 时返回 0 */
export function calcVolumeRatio(weight: number, volume: number): Decimal {
  const w = num(weight)
  const v = num(volume)
  if (w.isZero() || v.isZero()) return new Decimal(0)
  return w.dividedBy(v)
}
