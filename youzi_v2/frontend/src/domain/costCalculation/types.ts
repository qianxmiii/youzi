import type { WeightRatio } from '@/constants/costCalculation'

export interface ParsedCargo {
  quantity: number
  weight: number
  volume: number
}

export interface DduInput {
  quantity: number
  weight: number
  volume: number
  pricePerCbm: number
  byVolumeTaxIncluded: boolean
  byVolumeTaxIncludedValue: number
  goodsValue: number
  taxRate: number
  deliveryFeeUsd: number
  weightRatio: WeightRatio
}

export interface DduOutput {
  chargeVolume: string
  /** 计费重 kg：max(实重, 材积重) 向上取整；单价/kg 用此值 */
  chargeWeight: string
  volumeRatio: string
  forwardingCost: string
  deliveryFeeRmb: string
  taxAmount: string
  totalCost: string
  unitPriceCbm: string
  unitPriceKg: string
}

export interface DdpRowInput {
  quantity: number
  weight: number
  volume: number
  pricePerKg: number
  deliveryFeeUsd: number
  deliveryFeeRmb: number
  weightRatio: WeightRatio
}

export interface DdpRowOutput {
  chargeWeight: string
  chargeVolume: string
  volumeRatio: string
  forwardingCost: string
  deliveryFeeTotal: string
  totalCost: string
  unitPriceCbm: string
  unitPriceKg: string
}
