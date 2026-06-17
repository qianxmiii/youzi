/**
 * 成本计算单元测试（与 docs/costCalTab-analysis.md 第 5 节对齐）
 * 运行: npx tsx youzi_v2/scripts/verify_cost_calculation.ts
 */
import { calculateDdpRow, calculateDdu, parseCargoText } from '../frontend/src/domain/costCalculation'

function assertEq(actual: string, expected: string, label: string) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`)
  }
}

const c1 = parseCargoText('21ctns 8.3 kg 2.126 cbm')
if (c1.quantity !== 21 || c1.weight !== 9 || c1.volume !== 2.13) {
  throw new Error(`5.1 failed: ${JSON.stringify(c1)}`)
}

const c2 = parseCargoText('10ctns 100 lbs 1.2 cbm')
if (c2.weight !== 46 || c2.volume !== 1.2) throw new Error(`5.2 failed: ${JSON.stringify(c2)}`)

const c3 = parseCargoText('2ctns 10kg 50*40*30cm')
if (c3.quantity !== 2 || c3.weight !== 10 || c3.volume !== 0.12) {
  throw new Error(`5.3 failed: ${JSON.stringify(c3)}`)
}

const ddu1 = calculateDdu({
  quantity: 0,
  weight: 100,
  volume: 0.2,
  pricePerCbm: 1000,
  byVolumeTaxIncluded: false,
  byVolumeTaxIncludedValue: 0,
  goodsValue: 167,
  taxRate: 10,
  deliveryFeeUsd: 20,
  weightRatio: '363',
})
assertEq(ddu1.chargeVolume, '0.28', '5.4 chargeVolume')
assertEq(ddu1.volumeRatio, '500', '5.4 volumeRatio')
assertEq(ddu1.forwardingCost, '280.00', '5.4 forwarding')
assertEq(ddu1.taxAmount, '72', '5.4 tax')
assertEq(ddu1.deliveryFeeRmb, '142.00', '5.4 delivery')
assertEq(ddu1.totalCost, '494', '5.4 total')
assertEq(ddu1.unitPriceCbm, '1762', '5.4 unit cbm')
assertEq(ddu1.unitPriceKg, '4.93', '5.4 unit kg')

const ddp1 = calculateDdpRow({
  quantity: 0,
  weight: 100,
  volume: 0.2,
  pricePerKg: 4,
  deliveryFeeUsd: 10,
  deliveryFeeRmb: 20,
  weightRatio: '363',
})
assertEq(ddp1.chargeWeight, '100', '5.7 chargeWeight')
assertEq(ddp1.chargeVolume, '0.28', '5.7 chargeVolume')
assertEq(ddp1.volumeRatio, '500', '5.7 volumeRatio')
assertEq(ddp1.forwardingCost, '400.00', '5.7 forwarding')
assertEq(ddp1.deliveryFeeTotal, '88.00', '5.7 delivery')
assertEq(ddp1.totalCost, '488', '5.7 total')
assertEq(ddp1.unitPriceCbm, '1743', '5.7 unit cbm')
assertEq(ddp1.unitPriceKg, '4.88', '5.7 unit kg')

const ddp2 = calculateDdpRow({
  quantity: 0,
  weight: 10,
  volume: 1,
  pricePerKg: 4,
  deliveryFeeUsd: 0,
  deliveryFeeRmb: 0,
  weightRatio: '363',
})
assertEq(ddp2.chargeWeight, '167', '5.8 chargeWeight')
assertEq(ddp2.forwardingCost, '668.00', '5.8 forwarding')
assertEq(ddp2.totalCost, '668', '5.8 total')

console.log('cost calculation tests passed')
