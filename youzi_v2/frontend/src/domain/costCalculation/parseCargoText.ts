import { ceilVolume } from './decimal'
import type { ParsedCargo } from './types'

const VOLUME_REGEX = /([\d.]+)\s*(cbm|方)/i
const WEIGHT_REGEX = /([\d.]+)\s*(kg|kgs|lb|lbs|磅)/i
const QUANTITY_REGEX =
  /(\d+)\s*(X|\s*)\s*(BOX|BOXES|Boxs|CARTON|CARTONS|ctn|ctns|件|箱|pal|pallets|托)/i
const DIMENSION_REGEX =
  /(\d+(?:\.\d+)?)\s*[*xX×хХ]\s*(\d+(?:\.\d+)?)\s*[*xX×хХ]\s*(\d+(?:\.\d+)?)\s*(cm|mm|MM|m|M|米|inch|in|英寸)?/i

function toCm(value: number, unit: string): number {
  const u = unit.toLowerCase()
  if (u === 'inch' || u === 'in' || u === '英寸') return value * 2.54
  if (u === 'mm') return value / 10
  if (u === 'm' || u === '米') return value * 100
  return value
}

/** 从自然语言文本识别箱数、重量、体积（与 Legacy parseCalTabCargoInfo 一致） */
export function parseCargoText(input: string): ParsedCargo {
  const text = input.trim()
  const quantityMatch = text.match(QUANTITY_REGEX)
  const quantity = quantityMatch ? Number.parseInt(quantityMatch[1], 10) : 0

  const volumeMatch = text.match(VOLUME_REGEX)
  let volume = volumeMatch ? Number.parseFloat(volumeMatch[1]) : 0

  const weightMatch = text.match(WEIGHT_REGEX)
  let weightKg = 0
  if (weightMatch) {
    weightKg = Number.parseFloat(weightMatch[1])
    const unit = (weightMatch[2] || '').toLowerCase()
    if (unit === 'lb' || unit === 'lbs' || unit === '磅') {
      weightKg *= 0.453592
    }
  }

  const dimensionMatch = text.match(DIMENSION_REGEX)
  if (dimensionMatch) {
    const unit = dimensionMatch[4] || ''
    const length = toCm(Number.parseFloat(dimensionMatch[1]), unit)
    const width = toCm(Number.parseFloat(dimensionMatch[2]), unit)
    const height = toCm(Number.parseFloat(dimensionMatch[3]), unit)
    if (volume === 0 && quantity > 0) {
      volume = (length * width * height * quantity) / 1_000_000
    }
  }

  return {
    quantity,
    weight: weightKg > 0 ? Math.ceil(weightKg) : 0,
    volume: volume > 0 ? ceilVolume(volume) : 0,
  }
}
