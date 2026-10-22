import type { Shipment } from '@/types/shipment'

export type MarkRenameFieldKey =
  | 'shipmentNo'
  | 'addressCode'
  | 'ctns'
  | 'customer'
  | 'customerNo'
  | 'refShipmentNo'
  | 'customerShipmentId'
  | 'channelNameZh'
  | 'zipcode'
  | 'originWarehouseCode'
  | 'countryCode'

export type MarkRenameCountryLang = 'en' | 'zh'

/** 国家码 → 中英文名（字典 value=中文，desc=英文） */
export type MarkRenameCountryLabelMap = Record<string, { zh: string; en: string }>

export const MARK_RENAME_FIELDS: { key: MarkRenameFieldKey; label: string }[] = [
  { key: 'shipmentNo', label: '运单号' },
  { key: 'addressCode', label: '派送仓库（空则邮编）' },
  { key: 'ctns', label: '件数' },
  { key: 'customer', label: '客户' },
  { key: 'customerNo', label: '客户单号' },
  { key: 'refShipmentNo', label: '关联单号' },
  { key: 'customerShipmentId', label: '货件号' },
  { key: 'channelNameZh', label: '渠道' },
  { key: 'zipcode', label: '邮编' },
  { key: 'originWarehouseCode', label: '收货仓' },
  { key: 'countryCode', label: '国家' },
]

export const DEFAULT_MARK_RENAME_FIELDS: MarkRenameFieldKey[] = [
  'shipmentNo',
  'addressCode',
  'ctns',
]

export const DEFAULT_MARK_RENAME_COUNTRY_LANG: MarkRenameCountryLang = 'en'

export const MARK_RENAME_SEPARATORS = [
  { label: '-（连字符）', value: '-' },
  { label: '_（下划线）', value: '_' },
  { label: '空格', value: ' ' },
] as const

export const MARK_RENAME_COUNTRY_LANG_OPTIONS = [
  { label: '英文缩写', value: 'en' },
  { label: '中文', value: 'zh' },
] as const

const FIELD_KEYS = new Set(MARK_RENAME_FIELDS.map((item) => item.key))

export type MarkRenameResolveOptions = {
  countryLang?: MarkRenameCountryLang
  countryLabels?: MarkRenameCountryLabelMap
}

function fieldText(
  row: Shipment,
  key: MarkRenameFieldKey,
  options?: MarkRenameResolveOptions,
): string {
  if (key === 'ctns') {
    if (row.ctns === null || row.ctns === undefined) return ''
    return String(row.ctns)
  }
  if (key === 'channelNameZh') {
    return row.channelNameZh?.trim() || row.channelCode?.trim() || ''
  }
  if (key === 'addressCode') {
    // 默认规则：派送仓库为空则用邮编
    const code = row.addressCode?.trim() || ''
    if (code) return code
    return row.zipcode?.trim() || ''
  }
  if (key === 'countryCode') {
    const code = row.countryCode?.trim() || ''
    if (!code) return ''
    const upper = code.toUpperCase()
    // 英文：国家码缩写（AU / US）；中文：字典中文名
    const lang = options?.countryLang ?? DEFAULT_MARK_RENAME_COUNTRY_LANG
    if (lang !== 'zh') return upper
    const entry = options?.countryLabels?.[upper]
    return entry?.zh || upper
  }
  const value = row[key]
  if (value === null || value === undefined) return ''
  return String(value).trim()
}

function sanitizePart(value: string): string {
  return value.replace(/[\\/:*?"<>|\r\n\t]+/g, '').replace(/\s+/g, '')
}

/** 与后端 mark_rename.build_mark_rename_stem 一致，供下载前预览。 */
export function previewMarkRenameFolder(
  row: Shipment,
  key: MarkRenameFieldKey | '',
  options?: MarkRenameResolveOptions,
): string {
  if (!key) return ''
  const part = sanitizePart(fieldText(row, key, options))
  return part || '未填写'
}

export function previewMarkRenameStem(
  row: Shipment,
  fields: MarkRenameFieldKey[],
  separator: string,
  options?: MarkRenameResolveOptions,
): string {
  const parts = fields
    .map((key) => sanitizePart(fieldText(row, key, options)))
    .filter(Boolean)
  const stem = parts.join(separator)
  if (stem) return stem.length > 180 ? stem.slice(0, 180).replace(/[ .\-_]+$/g, '') : stem
  return sanitizePart(row.shipmentNo || '') || '唛头'
}

export function normalizeStoredMarkRenameFields(raw: unknown): MarkRenameFieldKey[] {
  if (!Array.isArray(raw)) return [...DEFAULT_MARK_RENAME_FIELDS]
  const fields: MarkRenameFieldKey[] = []
  for (const item of raw) {
    if (typeof item !== 'string' || !FIELD_KEYS.has(item as MarkRenameFieldKey)) continue
    const key = item as MarkRenameFieldKey
    if (!fields.includes(key)) fields.push(key)
  }
  return fields.length ? fields : [...DEFAULT_MARK_RENAME_FIELDS]
}

export function normalizeStoredMarkRenameCountryLang(raw: unknown): MarkRenameCountryLang {
  if (raw === 'zh' || raw === 'en') return raw
  return DEFAULT_MARK_RENAME_COUNTRY_LANG
}
