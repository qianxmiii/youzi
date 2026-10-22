export interface CodeTableMeta {
  table: string
  label: string
  hasPortType: boolean
  hasChannelFields?: boolean
  hasCarrierFields?: boolean
  hasRouteStatusFields?: boolean
  hasExceptionPhaseFields?: boolean
  hasAmzPortRuleFields?: boolean
}

export interface CodeTableRow {
  code: string
  nameZh: string
  nameEn: string
  sortOrder: number
  isActive: boolean
  portType?: string
  country?: string
  category?: string
  note?: string
  dpsChannelName?: string
  carrierId?: string
  dpsStatus?: string
  phaseCategory?: string
  transportMode?: string
  countryCode?: string
  leg?: string
  portCode?: string
  ruleKind?: string
  matchText?: string
  isDefault?: boolean
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
  country?: string
  category?: string
  note?: string
  dpsChannelName?: string
  carrierId?: string
  dpsStatus?: string
  phaseCategory?: string
  transportMode?: string
  countryCode?: string
  leg?: string
  portCode?: string
  ruleKind?: string
  matchText?: string
  isDefault?: boolean
}

export interface CodeTableImportResult {
  table: string
  created: number
  updated: number
  failed: number
  errors: { row: number; message: string }[]
}
