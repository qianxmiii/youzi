/** 尾程/转单号识别与承运商官网查询链接 */

export type LastMileCarrier = 'fedex' | 'ups' | 'usps' | 'dhl' | 'conwest' | 'dpd' | 'unknown'
export type TrackQueryLang = 'zh' | 'en'

const EXPRESS_CODE_TO_CARRIER: Record<string, LastMileCarrier> = {
  UPS: 'ups',
  FEDEX: 'fedex',
  FDX: 'fedex',
  DPD: 'dpd',
  DPDUK: 'dpd',
  CWE: 'conwest',
  CONWEST: 'conwest',
  USPS: 'usps',
  DHL: 'dhl',
}

/** 运单 express_code（UPS/FEDEX/DPD/CWE 等）→ 尾程承运商；空则走自动识别 */
export function expressCodeToCarrier(expressCode: string | null | undefined): LastMileCarrier | null {
  const key = (expressCode || '').trim().toUpperCase().replace(/\s+/g, '')
  if (!key || key === 'AUTO') return null
  return EXPRESS_CODE_TO_CARRIER[key] ?? null
}

export interface LastMileTrackingInfo {
  number: string
  carrier: LastMileCarrier
  carrierLabel: string
  url: string | null
  carrierId: string | null
  trackLang: TrackQueryLang
  /** Conwest 按件数展开后的子单号（最多 40，与 17TRACK 单次上限一致） */
  conwestNumbers?: string[]
}

const CARRIER_LABELS: Record<LastMileCarrier, string> = {
  fedex: 'FedEx',
  ups: 'UPS',
  usps: 'USPS',
  dhl: 'DHL',
  conwest: 'Conwest',
  dpd: 'DPD UK',
  unknown: '尾程',
}

/** Conwest：CWE C03IK469759415360001 或 C03xx… */
const CONWEST_TRACKING_RE = /^C03[A-Z]{2}\d{12,}$/i
const CONWEST_SUFFIX_LEN = 5
const CONWEST_17TRACK_MAX = 40
const CONWEST_17TRACK_FC = '100467'

const PREFIX_WITH_SEP =
  /^(UPS|FED\s*EX|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)\s*[-#:：]?\s*(.+)$/i
const PREFIX_COMPACT = /^(UPS|FEDEX|FDX|USPS|DHL|CWE|DPDUK|DPD)(.+)$/i

/** DPD UK 单号：查询仅用 parcel 号，不拼接邮编 */
export function normalizeDpdUkParcelRef(raw: string | null | undefined): string {
  const text = (raw || '').trim()
  if (!text) return ''
  const normalized = text.replace(/\s*\*\s*/g, '*').replace(/\s+/g, '')
  const star = normalized.indexOf('*')
  return star >= 0 ? normalized.slice(0, star) : normalized
}

/** 组装 DPD UK 查询用 parcel 号（不含邮编） */
export function buildDpdUkParcelRef(trackingNumber: string): string | null {
  const base = normalizeDpdUkParcelRef(normalizeLastMileTrackingNumber(trackingNumber))
  return base || null
}

/** http://www.dpd.co.uk/service/tracking?parcel=15505543519268 */
export function buildDpdUkTrackUrl(trackingNumber: string): string | null {
  const ref = buildDpdUkParcelRef(trackingNumber)
  if (!ref) return null
  return `http://www.dpd.co.uk/service/tracking?parcel=${encodeURIComponent(ref)}`
}

/** 剥离「UPS 1Z…」类前缀，返回纯单号（展示/提交与库内一致） */
export function normalizeLastMileTrackingNumber(raw: string | null | undefined): string {
  const text = (raw || '').trim()
  if (!text) return ''
  const sep = PREFIX_WITH_SEP.exec(text)
  if (sep?.[2]) return sep[2].trim()
  const compact = PREFIX_COMPACT.exec(text.replace(/\s+/g, ''))
  if (compact?.[2] && compact[2].trim().length >= 8) return compact[2].trim()
  return text
}

export function hasLastMileTracking(trackingNumber: string | null | undefined): boolean {
  return Boolean(normalizeLastMileTrackingNumber(trackingNumber))
}

/** 转单号前缀 → 尾程承运商（业务规则：8=FedEx，1Z=UPS，15=DPD，C=CWE，0=DHL） */
export function detectCarrierByTrackingPrefix(
  trackingNumber: string,
): LastMileCarrier | null {
  const tn = trackingNumber.trim().toUpperCase().replace(/\s+/g, '')
  if (!tn) return null
  if (/^1Z/.test(tn)) return 'ups'
  if (/^15/.test(tn)) return 'dpd'
  if (/^C/.test(tn)) return 'conwest'
  if (/^0/.test(tn)) return 'dhl'
  if (/^8/.test(tn)) return 'fedex'
  return null
}

export function detectLastMileCarrier(
  trackingNumber: string,
  carrierCode?: string | null,
  hintText?: string | null,
  rawTrackingNumber?: string | null,
  expressCode?: string | null,
): LastMileCarrier {
  const fromExpress = expressCodeToCarrier(expressCode)
  if (fromExpress) return fromExpress

  const tn = trackingNumber.trim().toUpperCase().replace(/\s+/g, '')
  const raw = (rawTrackingNumber || trackingNumber).trim().toUpperCase().replace(/\s+/g, '')
  const blob = `${carrierCode || ''} ${hintText || ''}`.toUpperCase()

  const fromPrefix = detectCarrierByTrackingPrefix(tn)
  if (fromPrefix) return fromPrefix

  const code = (carrierCode || '').trim().toUpperCase()
  if (
    /^DPD(UK)?/.test(raw) ||
    code === 'DPD' ||
    code === 'DPDUK' ||
    /\bDPDUK\b/.test(blob)
  ) {
    return 'dpd'
  }

  if (blob.includes('FEDEX') || blob.includes('FDX')) {
    return 'fedex'
  }
  if (blob.includes('USPS')) {
    return 'usps'
  }
  if (blob.includes('DHL')) {
    return 'dhl'
  }
  if (blob.includes('UPS')) {
    return 'ups'
  }
  if (
    blob.includes('CWE') ||
    blob.includes('CONWEST') ||
    CONWEST_TRACKING_RE.test(tn)
  ) {
    return 'conwest'
  }
  if (/^9\d{19,21}$/.test(tn)) {
    return 'usps'
  }
  return 'unknown'
}

export function normalizeTrackQueryLang(raw: string | null | undefined): TrackQueryLang {
  return (raw || '').trim().toLowerCase() === 'en' ? 'en' : 'zh'
}

export function isConwestTrackingNumber(raw: string | null | undefined): boolean {
  const tn = (raw || '').trim().toUpperCase().replace(/\s+/g, '')
  return Boolean(tn && CONWEST_TRACKING_RE.test(tn))
}

/** Conwest：末 5 位流水号，按件数递增（如 60001～60040） */
export function expandConwestTrackingNumbers(
  seed: string | null | undefined,
  count: number | null | undefined,
): string[] {
  const tn = normalizeLastMileTrackingNumber(seed).toUpperCase().replace(/\s+/g, '')
  if (!tn) return []
  if (!isConwestTrackingNumber(tn)) return [tn]
  const pieces = Math.max(1, Math.floor(Number(count) || 1))
  if (pieces === 1) return [tn]
  if (tn.length <= CONWEST_SUFFIX_LEN) return [tn]
  const prefix = tn.slice(0, -CONWEST_SUFFIX_LEN)
  const suffix = tn.slice(-CONWEST_SUFFIX_LEN)
  const start = Number.parseInt(suffix, 10)
  if (Number.isNaN(start)) return [tn]
  return Array.from({ length: pieces }, (_, i) => `${prefix}${String(start + i).padStart(5, '0')}`)
}

export function buildConwest17TrackUrl(numbers: string[]): string | null {
  const cleaned: string[] = []
  const seen = new Set<string>()
  for (const raw of numbers) {
    const n = normalizeLastMileTrackingNumber(raw)
    if (n && !seen.has(n)) {
      seen.add(n)
      cleaned.push(n)
    }
  }
  if (!cleaned.length) return null
  const batch = cleaned.slice(0, CONWEST_17TRACK_MAX)
  return `https://t.17track.net/en#nums=${batch.join(',')}&fc=${CONWEST_17TRACK_FC}`
}

export function formatConwestTrackingRange(numbers: string[]): string | null {
  if (numbers.length <= 1) return null
  const first = numbers[0]
  const last = numbers[numbers.length - 1]
  const suf = (n: string) => (n.length > CONWEST_SUFFIX_LEN ? n.slice(-CONWEST_SUFFIX_LEN) : n)
  return `${suf(first)}～${suf(last)}（共 ${numbers.length} 件）`
}

export function buildLastMileTrackUrl(
  trackingNumber: string,
  carrier: LastMileCarrier,
  lang: TrackQueryLang = 'zh',
): string | null {
  const n = trackingNumber.trim()
  if (!n) return null
  const enc = encodeURIComponent(n)
  const en = lang === 'en'
  switch (carrier) {
    case 'fedex':
      return en
        ? `https://www.fedex.com/wtrk/track/?action=track&tracknumbers=${enc}&locale=en_US&cntry_code=us`
        : `https://www.fedex.com/wtrk/track/?action=track&tracknumbers=${enc}&locale=zh_CN&cntry_code=us`
    case 'ups':
      return en
        ? `https://www.ups.com/track?tracknum=${enc}&loc=en_US`
        : `https://www.ups.com/track?tracknum=${enc}&loc=zh_CN`
    case 'usps':
      return `https://tools.usps.com/go/TrackConfirmAction?tLabels=${enc}`
    case 'dhl':
      return en
        ? `https://www.dhl.com/en/express/tracking.html?submit=1&tracking-id=${enc}`
        : `https://www.dhl.com/cn-zh/home/tracking/tracking-express.html?submit=1&tracking-id=${enc}`
    case 'conwest':
      return buildConwest17TrackUrl([n])
    case 'dpd':
      return buildDpdUkTrackUrl(n)
    default:
      return null
  }
}

export function resolveLastMileTracking(shipment: {
  trackingNumber?: string | null
  expressCode?: string | null
  carrierId?: string | null
  carrierCode?: string | null
  latestCarrierDesc?: string | null
  zipcode?: string | null
  ctns?: number | null
  trackingNumbers?: string[] | null
  customerLang?: string | null
  /** @deprecated 兼容旧字段 */
  customerTrackQueryLang?: string | null
}): LastMileTrackingInfo | null {
  const number = normalizeLastMileTrackingNumber(shipment.trackingNumber)
  if (!number) return null
  const lang = normalizeTrackQueryLang(
    shipment.customerLang ?? shipment.customerTrackQueryLang,
  )
  const carrier = detectLastMileCarrier(
    number,
    shipment.carrierCode,
    shipment.latestCarrierDesc,
    shipment.trackingNumber,
    shipment.expressCode,
  )
  let conwestNumbers: string[] | undefined
  let url =
    carrier === 'dpd'
      ? buildDpdUkTrackUrl(number)
      : buildLastMileTrackUrl(number, carrier, lang)
  if (carrier === 'conwest') {
    const fromDb = (shipment.trackingNumbers || []).filter(Boolean)
    const expanded =
      fromDb.length > 1
        ? fromDb
        : expandConwestTrackingNumbers(number, shipment.ctns)
    if (expanded.length > 1) {
      conwestNumbers = expanded.slice(0, CONWEST_17TRACK_MAX)
      url = buildConwest17TrackUrl(conwestNumbers)
    }
  }
  return {
    number,
    carrier,
    carrierLabel: CARRIER_LABELS[carrier],
    url,
    carrierId: (shipment.carrierId || '').trim() || null,
    trackLang: lang,
    conwestNumbers,
  }
}

export function formatLastMileTooltip(shipment: {
  trackingNumber?: string | null
  expressCode?: string | null
  carrierId?: string | null
  carrierCode?: string | null
  latestCarrierDesc?: string | null
  ctns?: number | null
  trackingNumbers?: string[] | null
}): string | null {
  const info = resolveLastMileTracking(shipment)
  if (!info) return null
  const code = (shipment.expressCode || '').trim()
  if (code) {
    return `${info.number} · 指定 ${code} → ${info.carrierLabel}`
  }
  return `${info.number} · ${info.carrierLabel}`
}
