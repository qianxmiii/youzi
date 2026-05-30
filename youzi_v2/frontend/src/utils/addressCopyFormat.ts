export interface AddressCopyInput {
  warehouseCode?: string
  addressLine1?: string
  addressLine2?: string
  addressLine3?: string
  city?: string
  state?: string
  postalCode?: string
  countryCode?: string
}

/** 复制格式：PHX3 - 6835 West Buckeye Road, Phoenix AZ 85043 US */
export function formatAddressCopyText(row: AddressCopyInput): string {
  const warehouseCode = (row.warehouseCode || '').trim()
  const addressLines = [row.addressLine1, row.addressLine2, row.addressLine3]
    .map((part) => (part || '').trim())
    .filter(Boolean)
    .join(' ')
  const location = [row.city, row.state, row.postalCode, row.countryCode]
    .map((part) => (part || '').trim())
    .filter(Boolean)
    .join(' ')

  if (!warehouseCode && !addressLines && !location) return ''

  let text = warehouseCode
  if (addressLines) {
    text = text ? `${text} - ${addressLines}` : addressLines
  }
  if (location) {
    if (addressLines) {
      text = `${text}, ${location}`
    } else if (text) {
      text = `${text} - ${location}`
    } else {
      text = location
    }
  }
  return text
}
