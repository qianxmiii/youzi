import type { ShipmentCarrierFilterOption } from '@/api/shipments'
import type { CodeTableRow } from '@/types/codeTable'

export function buildCarrierSelectOptions(
  carriers: ShipmentCarrierFilterOption[] | undefined,
  legacyCodes?: string[],
  opts?: { includeEmpty?: boolean; emptyValue?: string },
): { label: string; value: string }[] {
  const items =
    carriers?.length ?
      carriers.map((c) => ({
        label: (c.nameZh || c.code).trim() || c.code,
        value: c.code,
      }))
    : (legacyCodes ?? []).map((v) => ({ label: v, value: v }))
  if (opts?.includeEmpty) {
    return [{ label: '（未填写）', value: opts.emptyValue ?? '__EMPTY__' }, ...items]
  }
  return items
}

/** 运单编辑：下拉显示中文名，值为 carrier_codes.carrier_id（无 id 时回退 code） */
export function buildCarrierFormSelectOptions(
  rows: CodeTableRow[] | undefined,
): { label: string; value: string }[] {
  const items: { label: string; value: string }[] = []
  const seen = new Set<string>()
  for (const row of rows ?? []) {
    if (!row.isActive) continue
    const id = (row.carrierId || '').trim()
    const value = id || row.code.trim()
    if (!value || seen.has(value)) continue
    seen.add(value)
    const label = (row.nameZh || row.nameEn || row.code).trim() || row.code
    items.push({ label, value })
  }
  return items.sort((a, b) => a.label.localeCompare(b.label, 'zh'))
}

/** 将运单已存的 carrier_code（code 或 carrier_id）解析为表单下拉的 value */
export function resolveCarrierFormSelectValue(
  carrierCode: string | null | undefined,
  rows: CodeTableRow[] | undefined,
): string | null {
  const raw = (carrierCode || '').trim()
  if (!raw) return null
  for (const row of rows ?? []) {
    const id = (row.carrierId || '').trim()
    if (id && id === raw) return id
    if (row.code.trim() === raw) return id || raw
  }
  return raw
}

export function buildCarrierFormSelectOptionsWithCurrent(
  rows: CodeTableRow[] | undefined,
  current: string | null | undefined,
  currentNameZh?: string | null,
): { label: string; value: string }[] {
  const opts = buildCarrierFormSelectOptions(rows)
  const cur = (current || '').trim()
  if (cur && !opts.some((o) => o.value === cur)) {
    opts.unshift({
      label: (currentNameZh || cur).trim() || cur,
      value: cur,
    })
  }
  return opts
}
