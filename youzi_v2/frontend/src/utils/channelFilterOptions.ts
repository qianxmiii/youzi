import type { ShipmentChannelFilterOption } from '@/api/shipments'

export function buildChannelSelectOptions(
  channels: ShipmentChannelFilterOption[] | undefined,
  legacyCodes?: string[],
): { label: string; value: string }[] {
  const byCode = new Map<string, { label: string; value: string }>()

  if (channels?.length) {
    for (const c of channels) {
      const value = (c.code || '').trim()
      if (!value || byCode.has(value)) continue
      byCode.set(value, {
        label: (c.nameZh || value).trim() || value,
        value,
      })
    }
  } else {
    for (const raw of legacyCodes ?? []) {
      const value = raw.trim()
      if (!value || byCode.has(value)) continue
      byCode.set(value, { label: value, value })
    }
  }

  const options = [...byCode.values()]
  const labelCounts = new Map<string, number>()
  for (const o of options) {
    labelCounts.set(o.label, (labelCounts.get(o.label) ?? 0) + 1)
  }
  return options.map((o) => ({
    label: (labelCounts.get(o.label) ?? 0) > 1 ? `${o.label} (${o.value})` : o.label,
    value: o.value,
  }))
}

export function channelFilterLabel(
  channels: ShipmentChannelFilterOption[] | undefined,
  code: string | null | undefined,
): string {
  const c = (code || '').trim()
  if (!c) return ''
  const hit = channels?.find((x) => x.code === c)
  return (hit?.nameZh || c).trim() || c
}
