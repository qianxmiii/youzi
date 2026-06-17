import { COST_EXCHANGE_RATE } from '@/constants/costCalculation'
import { calcChargeVolume, calcVolumeRatio } from './chargeVolume'
import { Decimal, ceil0, ceil2, fixed2, num } from './decimal'
import type { DduInput, DduOutput } from './types'

export function calculateDdu(input: DduInput): DduOutput {
  const weight = num(input.weight)
  const volume = num(input.volume)
  const pricePerCbm = num(input.pricePerCbm)
  const goodsValue = num(input.goodsValue)
  const taxRate = num(input.taxRate)
  const deliveryFeeUsd = num(input.deliveryFeeUsd)

  const chargeVolume = calcChargeVolume(input.weight, input.volume, input.weightRatio)
  const volumeRatio = calcVolumeRatio(input.weight, input.volume)

  let actualPricePerCbm = pricePerCbm
  if (input.byVolumeTaxIncluded) {
    actualPricePerCbm = pricePerCbm.plus(num(input.byVolumeTaxIncludedValue))
  }

  const forwardingCost = actualPricePerCbm.mul(chargeVolume)
  const taxAmount = goodsValue
    .mul(taxRate.plus(20).dividedBy(100))
    .mul(volume)
    .mul(COST_EXCHANGE_RATE)
  const deliveryFeeRmb = deliveryFeeUsd.mul(COST_EXCHANGE_RATE)
  const totalCost = forwardingCost.plus(taxAmount).plus(deliveryFeeRmb)

  const unitPriceCbm = chargeVolume.greaterThan(0)
    ? totalCost.dividedBy(chargeVolume)
    : new Decimal(0)
  const unitPriceKg = weight.greaterThan(0)
    ? totalCost.dividedBy(weight)
    : new Decimal(0)

  return {
    chargeVolume: chargeVolume.toFixed(2),
    volumeRatio: volumeRatio.isZero() ? '0' : volumeRatio.toFixed(0),
    forwardingCost: ceil2(forwardingCost),
    deliveryFeeRmb: fixed2(deliveryFeeRmb),
    taxAmount: ceil0(taxAmount),
    totalCost: ceil0(totalCost),
    unitPriceCbm: ceil0(unitPriceCbm),
    unitPriceKg: fixed2(unitPriceKg),
  }
}
