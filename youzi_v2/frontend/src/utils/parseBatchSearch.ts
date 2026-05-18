/** 将逗号、换行、分号、空格等分隔的文本解析为去重后的单号列表 */
export function parseBatchSearchTokens(input: string): string[] {
  return [
    ...new Set(
      input
        .split(/[\s,，;；\n\r]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  ]
}
