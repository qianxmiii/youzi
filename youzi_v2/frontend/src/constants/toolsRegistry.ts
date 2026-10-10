/** 工具中心注册表（展示与导航，不含各工具业务规则） */

export type ToolCategoryId = 'file' | 'warehouse' | 'data'

export type ToolStatus = 'active' | 'coming-soon' | 'maintenance'

export type ToolDefinition = {
  id: string
  name: string
  description: string
  category: ToolCategoryId
  route: string
  /** NavIcon / Lucide 键名 */
  icon: string
  inputSummary: string
  outputSummary: string
  status?: ToolStatus
  permission?: string
  /** 卡片角标：新功能 */
  badge?: 'new'
  /** 适用对象，一句话 */
  audience?: string
}

export type ToolCategoryMeta = {
  id: ToolCategoryId
  label: string
  description: string
}

export const TOOL_CATEGORIES: ToolCategoryMeta[] = [
  {
    id: 'file',
    label: 'Excel 与文件',
    description: '上传、解析、转换、打包文件',
  },
  {
    id: 'data',
    label: '数据辅助',
    description: '校验、查询、整理业务数据',
  },
  {
    id: 'warehouse',
    label: '仓储辅助',
    description: '仓储相关辅助处理（后续扩展）',
  },
]

export const TOOL_REGISTRY: ToolDefinition[] = [
  {
    id: 'image-link-zip',
    name: '标签图片打包',
    description: '从 Excel 指定列读取图片链接，批量下载并打成 ZIP',
    category: 'file',
    route: '/tools/image-link-zip',
    icon: 'download',
    inputSummary: 'Excel（.xls / .xlsx）',
    outputSummary: '图片 ZIP',
    status: 'active',
    badge: 'new',
    audience: '运营 / 客服',
  },
  {
    id: 'shipment-file-rename',
    name: '运单文件重命名',
    description: '按 Excel 运单号/国家/仓库代码/件数，批量重命名本地文件夹中的文件',
    category: 'file',
    route: '/tools/shipment-file-rename',
    icon: 'download',
    inputSummary: 'Excel + 本地文件夹',
    outputSummary: '运单号-国家-仓库代码-件数',
    status: 'active',
    badge: 'new',
    audience: '运营 / 仓配',
  },
  {
    id: 'product-import',
    name: '箱单转产品导入',
    description: '上传客户箱单发票，按产品导入模板生成可导入的 .xls',
    category: 'file',
    route: '/tools/product-import',
    icon: 'download',
    inputSummary: '箱单（.xls / .xlsx）',
    outputSummary: '产品导入模版.xls',
    status: 'active',
    badge: 'new',
    audience: '运营 / 报关',
  },
  {
    id: 'fba-box-code-expand',
    name: 'FBA 箱号展开',
    description: '按前缀与箱数批量生成「前缀+命名符+序号」箱号（如 FBA…U000001）',
    category: 'warehouse',
    route: '/tools/fba-box-code-expand',
    icon: 'box',
    inputSummary: '前缀与箱数 / 命名符 / 尾数位数',
    outputSummary: '展开后的箱号列表',
    status: 'active',
    badge: 'new',
    audience: '运营 / 仓配',
  },
]

export function toolsByCategory(
  category: ToolCategoryId,
  tools: ToolDefinition[] = TOOL_REGISTRY,
): ToolDefinition[] {
  return tools.filter((t) => t.category === category)
}

export function toolStatusLabel(status: ToolStatus | undefined): string | null {
  if (status === 'coming-soon') return '即将推出'
  if (status === 'maintenance') return '维护中'
  return null
}
