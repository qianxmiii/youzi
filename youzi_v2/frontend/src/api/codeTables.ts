import { api } from '@/api/client'
import type {
  CodeTableImportResult,
  CodeTableListResponse,
  CodeTableMeta,
  CodeTablePayload,
  CodeTableRow,
} from '@/types/codeTable'

export async function listCodeTableTypes(): Promise<{ tables: CodeTableMeta[] }> {
  return api('/api/v1/admin/code-tables')
}

export async function listCodeTableRows(
  table: string,
  params?: { search?: string; limit?: number; offset?: number },
): Promise<CodeTableListResponse> {
  return api(`/api/v1/admin/code-tables/${table}`, { query: params })
}

export async function createCodeTableRow(
  table: string,
  payload: CodeTablePayload,
): Promise<CodeTableRow> {
  return api(`/api/v1/admin/code-tables/${table}`, { method: 'POST', body: payload })
}

export async function updateCodeTableRow(
  table: string,
  code: string,
  payload: Omit<CodeTablePayload, 'code'>,
): Promise<CodeTableRow> {
  return api(`/api/v1/admin/code-tables/${table}/${encodeURIComponent(code)}`, {
    method: 'PUT',
    body: payload,
  })
}

export async function deleteCodeTableRow(table: string, code: string): Promise<void> {
  await api(`/api/v1/admin/code-tables/${table}/${encodeURIComponent(code)}`, {
    method: 'DELETE',
  })
}

export async function importCodeTableExcel(
  table: string,
  file: File,
): Promise<CodeTableImportResult> {
  const form = new FormData()
  form.append('file', file)
  return api(`/api/v1/admin/code-tables/${table}/import`, { method: 'POST', body: form })
}

export function codeTableTemplateUrl(table: string): string {
  const base = import.meta.env.VITE_API_BASE || ''
  return `${base}/api/v1/admin/code-tables/${table}/template`
}
