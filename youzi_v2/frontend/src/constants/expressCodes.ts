/** 运单尾程快递（express_code），优先于单号自动识别 */

export type ExpressCode = 'UPS' | 'FEDEX' | 'DPD' | 'CWE' | 'USPS' | 'DHL'

export const EXPRESS_CODE_OPTIONS: { label: string; value: ExpressCode | null }[] = [
  { label: '自动识别', value: null },
  { label: 'UPS', value: 'UPS' },
  { label: 'FedEx', value: 'FEDEX' },
  { label: 'DPD', value: 'DPD' },
  { label: 'CWE (Conwest)', value: 'CWE' },
  { label: 'USPS', value: 'USPS' },
  { label: 'DHL', value: 'DHL' },
]

/** 批量修改：不修改 / 清空 / 指定快递 */
export const EXPRESS_CODE_BATCH_OPTIONS: { label: string; value: string | null }[] = [
  { label: '不修改', value: '__UNCHANGED__' },
  { label: '自动识别（清空）', value: null },
  ...EXPRESS_CODE_OPTIONS.filter((o) => o.value !== null),
]
