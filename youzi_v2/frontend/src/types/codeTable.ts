export interface CodeTableMeta {
  table: string
  label: string
  hasPortType: boolean
}

export interface CodeTableRow {
  code: string
  nameZh: string
  nameEn: string
  sortOrder: number
  isActive: boolean
  portType?: string
  createdTime: string
  updatedTime: string
}

export interface CodeTableListResponse {
  table: string
  label: string
  items: CodeTableRow[]
  total: number
  limit: number
  offset: number
}

export interface CodeTablePayload {
  code: string
  nameZh: string
  nameEn: string
  sortOrder: number
  isActive: boolean
  portType?: string
}

export interface CodeTableImportResult {
  table: string
  created: number
  updated: number
  failed: number
  errors: { row: number; message: string }[]
}
