/** 从航次摘要解析船名 / 航次（兼容仅填 vessel_voyage 的旧数据）。 */

export interface VesselVoyageLike {
  vesselName?: string | null
  voyageNo?: string | null
  vesselVoyage: string
}

export function resolveVesselName(v: VesselVoyageLike): string {
  const name = (v.vesselName || '').trim()
  if (name) return name
  const vv = (v.vesselVoyage || '').trim()
  const idx = vv.lastIndexOf('/')
  if (idx > 0) return vv.slice(0, idx).trim()
  return vv
}

export function resolveVoyageNo(v: VesselVoyageLike): string {
  const no = (v.voyageNo || '').trim()
  if (no) return no
  const vv = (v.vesselVoyage || '').trim()
  const idx = vv.lastIndexOf('/')
  if (idx > 0) return vv.slice(idx + 1).trim()
  return vv
}
