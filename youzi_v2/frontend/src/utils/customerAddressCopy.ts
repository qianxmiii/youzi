export interface CustomerAddressCopyInput {
  company?: string
  consigneeName?: string
  phone?: string
  address?: string
  email?: string
}

/** 公司名、收货人名、电话、地址、邮箱，空行省掉。 */
export function formatCustomerAddressCopy(row: CustomerAddressCopyInput): string {
  return [row.company, row.consigneeName, row.phone, row.address, row.email]
    .map((part) => (part || '').trim())
    .filter(Boolean)
    .join('\n')
}

export function formatCustomerAddressCopyBatch(rows: CustomerAddressCopyInput[]): string {
  return rows
    .map((row) => formatCustomerAddressCopy(row))
    .filter(Boolean)
    .join('\n\n')
}
