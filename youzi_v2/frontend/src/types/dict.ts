export interface DictItem {
  dictType: string
  code: string
  value: string
  desc: string
  createdTime?: string
  updatedTime?: string
}

export interface DictListResponse {
  dictType: string
  items: DictItem[]
}
