import Decimal from 'decimal.js'

export { Decimal }

export function num(value: unknown): Decimal {
  if (value === null || value === undefined || value === '') return new Decimal(0)
  const n = typeof value === 'number' ? value : Number.parseFloat(String(value))
  return Number.isFinite(n) ? new Decimal(n) : new Decimal(0)
}

export function ceil0(value: Decimal): string {
  return value.toDecimalPlaces(0, Decimal.ROUND_UP).toFixed(0)
}

export function ceil2(value: Decimal): string {
  return value.toDecimalPlaces(2, Decimal.ROUND_UP).toFixed(2)
}

export function fixed2(value: Decimal): string {
  return value.toFixed(2)
}

export function ceilVolume(value: number): number {
  return Number(new Decimal(value).toDecimalPlaces(2, Decimal.ROUND_UP).toFixed(2))
}
