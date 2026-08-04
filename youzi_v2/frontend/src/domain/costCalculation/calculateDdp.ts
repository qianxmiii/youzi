import { EXCHANGE_RATE } from '@/constants/costCalculation'
import { calcChargeVolume, calcChargeWeight, calcVolumeRatio } from './chargeVolume'
import { Decimal, ceil0, ceil2, fixed2, num } from './decimal'
import type { DdpRowInput, DdpRowOutput } from './types'

export function calculateDdpRow(input: DdpRowInput): DdpRowOutput {
  const pricePerKg = num(input.pricePerKg)
  const deliveryFeeUsd = num(input.deliveryFeeUsd)
  const deliveryFeeRmb = num(input.deliveryFeeRmb)

  const chargeWeight = calcChargeWeight(input.weight, input.volume)
  const chargeVolume = calcChargeVolume(input.weight, input.volume, input.weightRatio)
  const volumeRatio = calcVolumeRatio(input.weight, input.volume)

  const forwardingCost = pricePerKg.mul(chargeWeight)
  const deliveryFeeFromUsd = deliveryFeeUsd.mul(EXCHANGE_RATE)
  const totalDeliveryFee = num(deliveryFeeRmb.plus(deliveryFeeFromUsd).toFixed(2))
  const totalCost = forwardingCost.plus(totalDeliveryFee)

  const unitPriceCbm = chargeVolume.greaterThan(0)
    ? totalCost.dividedBy(chargeVolume)
    : new Decimal(0)
  const unitPriceKg = chargeWeight.greaterThan(0)
    ? totalCost.dividedBy(chargeWeight)
    : new Decimal(0)

  return {
    chargeWeight: chargeWeight.toFixed(0),
    chargeVolume: ceil2(chargeVolume),
    volumeRatio: volumeRatio.isZero() ? '0' : volumeRatio.toFixed(0),
    forwardingCost: ceil2(forwardingCost),
    deliveryFeeTotal: fixed2(totalDeliveryFee),
    totalCost: ceil0(totalCost),
    unitPriceCbm: ceil0(unitPriceCbm),
    unitPriceKg: fixed2(unitPriceKg),
  }
}
