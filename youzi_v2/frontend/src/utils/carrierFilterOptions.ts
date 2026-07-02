import type { ShipmentCarrierFilterOption } from '@/api/shipments'

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
