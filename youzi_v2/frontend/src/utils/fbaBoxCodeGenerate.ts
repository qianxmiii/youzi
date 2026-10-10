/** FBA 箱号展开：前缀 + 命名符 + 零填充序号 */

export type FbaBoxCodeGenerateResult = {
  codes: string[]
  errors: string[]
}

/**
 * 解析「前缀 箱数」多行文本，生成 `{prefix}{namingChar}{000001…}`。
 * 箱号尾数 = 序号位数（默认 6 → U000001）。
 */
export function generateFbaBoxCodes(
  rawLines: string,
  namingChar = 'U',
  suffixDigits = 6,
): FbaBoxCodeGenerateResult {
  const marker = (namingChar || 'U').trim() || 'U'
  const width = Math.min(12, Math.max(1, Math.floor(Number(suffixDigits) || 6)))
  const codes: string[] = []
  const errors: string[] = []

  const lines = (rawLines || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)

  if (!lines.length) {
    return { codes, errors: ['请输入至少一行「前缀 箱数」'] }
  }

  lines.forEach((line, index) => {
    const parts = line.split(/\s+/).filter(Boolean)
    if (parts.length < 2) {
      errors.push(`第 ${index + 1} 行格式无效：需要「前缀 箱数」，例如 FBA19QH6N50R 3`)
      return
    }
    const countRaw = parts[parts.length - 1]!
    const prefix = parts.slice(0, -1).join('')
    const count = Number.parseInt(countRaw, 10)
    if (!prefix) {
      errors.push(`第 ${index + 1} 行缺少前缀`)
      return
    }
    if (!Number.isFinite(count) || count < 1 || count > 9999) {
      errors.push(`第 ${index + 1} 行箱数无效：${countRaw}（应为 1～9999 的整数）`)
      return
    }
    for (let i = 1; i <= count; i++) {
      codes.push(`${prefix}${marker}${String(i).padStart(width, '0')}`)
    }
  })

  return { codes, errors }
}
