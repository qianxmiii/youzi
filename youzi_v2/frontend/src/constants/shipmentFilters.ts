/** 运单列表筛选：承运商「未填写」占位值（与后端 CARRIER_CODE_FILTER_EMPTY 一致） */
export const CARRIER_FILTER_EMPTY = '__EMPTY__'

/** 运单列表筛选：付款状态「未设置」占位值（与后端 PAYMENT_STATUS_FILTER_EMPTY 一致） */
export const PAYMENT_FILTER_EMPTY = '__EMPTY__'

export const PAYMENT_STATUS_FILTER_OPTIONS = [
  { label: '已付款', value: 'PAID' },
  { label: '未付款', value: 'UNPAID' },
  { label: '未设置', value: PAYMENT_FILTER_EMPTY },
] as const

/** 运单编辑 / 批量修改：仅已付款、未付款 */
export const PAYMENT_STATUS_EDIT_OPTIONS = [
  { label: '已付款', value: 'PAID' },
  { label: '未付款', value: 'UNPAID' },
] as const
