/** 成本计算静态数据（迁移自 Legacy data.js / data_price.js） */

export const EXCHANGE_RATE = 6.8
export const COST_EXCHANGE_RATE = 7.1

export type WeightRatio = '363' | '360' | '400' | '450' | '500' | 'actual'

export const WEIGHT_RATIO_OPTIONS: { label: string; value: WeightRatio }[] = [
  { label: '363', value: '363' },
  { label: '360', value: '360' },
  { label: '400', value: '400' },
  { label: '450', value: '450' },
  { label: '500', value: '500' },
  { label: '实际方', value: 'actual' },
]

export interface CommonProduct {
  name: string
  hscode: string
  taxrate: string
}

export const COMMON_PRODUCTS: CommonProduct[] = [
  { name: '脚轮', hscode: '3926909985', taxrate: '12.8' },
  { name: '门把手', hscode: '8302426000', taxrate: '10.9' },
  { name: '气球', hscode: '9505906000', taxrate: '0' },
  { name: '装饰板', hscode: '3926400010', taxrate: '5.3' },
  { name: '大豆蜡', hscode: '3406000000', taxrate: '7.5' },
  { name: '橡胶手套', hscode: '3926201050', taxrate: '0' },
  { name: '游戏卡牌', hscode: '9504904000', taxrate: '0' },
]

export interface DdpKgPriceOption {
  label: string
  price: number
}

export const DDP_KG_PRICE_OPTIONS: DdpKgPriceOption[] = [
  { label: '洛杉矶自提(特惠)', price: 3.48 },
  { label: '洛杉矶自提(OA)', price: 3.68 },
  { label: '洛杉矶自提(以星合德)', price: 4.8 },
  { label: '洛杉矶自提(美森)', price: 8.78 },
  { label: '纽约自提', price: 4.28 },
  { label: '奥克兰自提', price: 3.78 },
  { label: '休斯顿自提', price: 4.28 },
  { label: '芝加哥自提', price: 4.88 },
  { label: '萨瓦纳自提', price: 4.38 },
]

export const DEFAULT_GOODS_VALUE_USD = 167
