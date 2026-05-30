import { api } from './client'

export type AddressType = 'AMZ' | 'WFS' | ''

export interface Address {
  id: string
  warehouseCode: string
  addressType: AddressType | string
  company: string
  contact: string
  countryCode: string
  postalCode: string
  state: string
  city: string
  addressLine1: string
  addressLine2: string
  addressLine3: string
  phone: string
  note1: string
  note2: string
  created_at?: string
  updated_at?: string
}

export interface AddressPayload {
  warehouseCode: string
  addressType: AddressType | string
  company: string
  contact: string
  countryCode: string
  postalCode: string
  state: string
  city: string
  addressLine1: string
  addressLine2: string
  addressLine3: string
  phone: string
  note1: string
  note2: string
}

export interface AddressListResponse {
  items: Address[]
  total: number
}

export interface AddressFilterOptions {
  countries: string[]
}

const API_BASE = '/api/addresses-warehouse'

export async function listAddresses(params?: {
  search?: string
  addressType?: string
  countryCode?: string
  limit?: number
  offset?: number
}): Promise<AddressListResponse> {
  const q: Record<string, string | number> = {}
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.addressType?.trim()) q.addressType = params.addressType.trim()
  if (params?.countryCode?.trim()) q.countryCode = params.countryCode.trim()
  if (params?.limit != null) q.limit = params.limit
  if (params?.offset != null) q.offset = params.offset
  return api<AddressListResponse>(API_BASE, { query: q })
}

export async function listAddressFilterOptions(): Promise<AddressFilterOptions> {
  return api<AddressFilterOptions>(`${API_BASE}/filter-options`)
}

export async function createAddress(payload: AddressPayload): Promise<Address> {
  return api<Address>(API_BASE, { method: 'POST', body: payload })
}

export async function updateAddress(id: string, payload: AddressPayload): Promise<Address> {
  return api<Address>(`${API_BASE}/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: payload,
  })
}

export async function deleteAddress(id: string): Promise<void> {
  await api(`${API_BASE}/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export interface AddressImportResult {
  created: number
  updated: number
  failed: number
  errors: Array<{ row: number; message: string }>
}

export async function importAddressesExcel(file: File): Promise<AddressImportResult> {
  const form = new FormData()
  form.append('file', file)
  return api<AddressImportResult>(`${API_BASE}/import`, { method: 'POST', body: form })
}

export function addressTemplateUrl(): string {
  const base = import.meta.env.VITE_API_BASE || ''
  return `${base}${API_BASE}/template`
}

const ADDRESS_EXPORT_MAX = 10_000

export async function exportAddressesExcel(params?: {
  search?: string
  addressType?: string
  countryCode?: string
}): Promise<Blob> {
  const q: Record<string, string | number> = {
    limit: ADDRESS_EXPORT_MAX,
    offset: 0,
  }
  if (params?.search?.trim()) q.search = params.search.trim()
  if (params?.addressType?.trim()) q.addressType = params.addressType.trim()
  if (params?.countryCode?.trim()) q.countryCode = params.countryCode.trim()
  return api<Blob>(`${API_BASE}/export`, { query: q, responseType: 'blob' })
}
